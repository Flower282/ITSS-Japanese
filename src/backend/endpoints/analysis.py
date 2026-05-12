from __future__ import annotations

import json
import os
import re
import tempfile
import unicodedata
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape

import httpx
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from sqlmodel import Session, select

from src.db.session import engine
from src.models.analysis_models import (
    AnalysisConversation,
    AnalysisLog,
    AnalysisMessage,
)


router = APIRouter(prefix="/analysis", tags=["analysis"])


AI_ANALYSIS_TASK_TYPES = [
    "INTENT_ANALYSIS",
    "NUANCE_ANALYSIS",
    "MISUNDERSTANDING_DETECTION",
    "CULTURE_EXPLANATION",
    "REPLY_SUGGESTION",
    "CONVERSATION_SUMMARY",
]


class AnalysisResponse(BaseModel):
    id: int
    meeting_title: str
    meeting_date: str | None = None
    duration_minutes: int | None = None
    understanding_score: int
    overall_sentiment: str
    ai_overall_feedback: str
    metrics: list[dict[str, Any]]
    perception_gaps: list[dict[str, Any]]
    decisions: list[str]
    action_items: list[str]
    ai_log_count: int = 0


class AnalysisSearchItem(BaseModel):
    id: int
    meeting_title: str
    meeting_date: str | None = None
    duration_minutes: int | None = None
    understanding_score: int
    overall_sentiment: str
    ai_overall_feedback: str


class AnalysisRunResponse(BaseModel):
    conversation_id: int
    inserted_logs: int
    analysis: AnalysisResponse


def parse_json_value(text: str | None) -> Any:
    if not text:
        return None

    try:
        return json.loads(text)
    except Exception:
        return None


def normalize_search_text(value: object) -> str:
    text = str(value or "").lower()
    text = unicodedata.normalize("NFD", text)
    text = "".join(
        char for char in text if unicodedata.category(char) != "Mn"
    )
    return text.replace("đ", "d")


def extract_json_from_ai(text: str) -> dict[str, Any]:
    text = text.strip()

    if text.startswith("```"):
        text = re.sub(r"^```json", "", text, flags=re.IGNORECASE).strip()
        text = re.sub(r"^```", "", text).strip()
        text = re.sub(r"```$", "", text).strip()

    match = re.search(r"\{.*\}", text, re.DOTALL)

    if not match:
        raise ValueError("AI response does not contain JSON")

    return json.loads(match.group(0))


def calculate_duration_minutes(
    started_at: datetime | None,
    ended_at: datetime | None,
) -> int | None:
    if not started_at or not ended_at:
        return None

    return int((ended_at - started_at).total_seconds() // 60)


def get_severity_classes(severity: str) -> str:
    severity = severity.upper()

    if severity == "CAO":
        return "bg-rose-500 text-white"

    if severity == "TRUNG BÌNH":
        return "bg-amber-500 text-white"

    return "bg-emerald-500 text-white"


def get_gap_card_classes(severity: str) -> str:
    severity = severity.upper()

    if severity == "CAO":
        return "w-full rounded-2xl border border-rose-100 bg-rose-50/60 p-4"

    if severity == "TRUNG BÌNH":
        return "w-full rounded-2xl border border-amber-100 bg-amber-50/60 p-4"

    return "w-full rounded-2xl border border-emerald-100 bg-emerald-50/60 p-4"


def normalize_gap_severity(value: Any) -> str:
    severity = str(value or "").strip()

    if not severity:
        return "THẤP"

    normalized = normalize_search_text(severity)

    if "cao" in normalized or "high" in normalized:
        return "CAO"

    if "trung binh" in normalized or "medium" in normalized:
        return "TRUNG BÌNH"

    return "THẤP"


def get_conversation_or_404(
    session: Session,
    conversation_id: int,
) -> AnalysisConversation:
    conversation = session.get(AnalysisConversation, conversation_id)

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    return conversation


def get_messages_by_conversation(
    session: Session,
    conversation_id: int,
) -> list[AnalysisMessage]:
    statement = (
        select(AnalysisMessage)
        .where(AnalysisMessage.conversation_id == conversation_id)
        .where(AnalysisMessage.is_deleted == False)
        .order_by(AnalysisMessage.created_at.asc())
    )

    return list(session.exec(statement).all())


def get_ai_logs_by_conversation(
    session: Session,
    conversation_id: int,
) -> list[AnalysisLog]:
    statement = (
        select(AnalysisLog)
        .where(AnalysisLog.conversation_id == conversation_id)
        .order_by(AnalysisLog.created_at.asc())
    )

    return list(session.exec(statement).all())


def get_latest_log_text(
    logs: list[AnalysisLog],
    task_type: str,
) -> str | None:
    matched_logs = [
        log.output_text
        for log in logs
        if log.ai_task_type == task_type
    ]

    return matched_logs[-1] if matched_logs else None


def has_full_analysis(logs: list[AnalysisLog]) -> bool:
    existing_types = {log.ai_task_type for log in logs}

    return all(
        task_type in existing_types
        for task_type in AI_ANALYSIS_TASK_TYPES
    )


async def analyze_conversation_with_ai(
    conversation: AnalysisConversation,
    messages: list[AnalysisMessage],
) -> dict[str, Any]:
    api_key = os.getenv("GROQ_API_KEY")

    if not api_key:
        raise HTTPException(
            status_code=500,
            detail="Missing GROQ_API_KEY in .env",
        )

    transcript = "\n".join(f"- {message.text}" for message in messages)

    prompt = f"""
Bạn là AI phân tích hội thoại trong môi trường làm việc Việt Nam - Nhật Bản.

Nhiệm vụ:
Phân tích hội thoại dưới đây để xác định:
- Ý định chính của cuộc hội thoại.
- Sắc thái giao tiếp và hàm ý.
- Nguy cơ hiểu lầm nếu thật sự có căn cứ trong transcript.
- Yếu tố văn hóa Việt - Nhật liên quan trực tiếp.
- Gợi ý phản hồi hoặc hành động tiếp theo.
- Tóm tắt tình trạng hội thoại, quyết định chính và mức độ hiểu nhau.

Yêu cầu bắt buộc:
- Trả lời bằng tiếng Việt có dấu đầy đủ.
- Không thay thế ký tự tiếng Việt bằng dấu hỏi (?).
- Chỉ trả về JSON hợp lệ.
- Không dùng markdown.
- Không giải thích ngoài JSON.
- Giá trị trong JSON phải là chuỗi Unicode UTF-8 hợp lệ.
- Chấm "understanding_score" theo đúng tiêu chí bên dưới, trả về số nguyên từ 0 đến 100.
- Không copy số điểm mẫu; điểm phải thay đổi theo nội dung transcript thực tế.
- Trường "overall_sentiment" chỉ được nhận một trong ba giá trị: "Tốt", "Trung lập", "Căng thẳng".
- Trường "severity" trong "misunderstanding_detection" chỉ được nhận một trong ba giá trị: "THẤP", "TRUNG BÌNH", "CAO".
- Nếu không có nguy cơ hiểu lầm có căn cứ rõ ràng, "misunderstanding_detection" phải là mảng rỗng [].
- Không được tạo nguy cơ hiểu lầm chỉ vì transcript có nhắc đến deadline, phạm vi, trách nhiệm hoặc khách hàng.
- Chỉ tạo nguy cơ hiểu lầm khi transcript thể hiện hai bên hiểu khác nhau, thiếu xác nhận, nói mơ hồ, nói gián tiếp hoặc có dấu hiệu bất đồng.
- Không được đưa khuyến nghị, lời khuyên hoặc action items vào "decisions".

Tiêu chí chấm understanding_score:
- 95-100:
  Hai bên đã xác nhận rõ đầy đủ 5 yếu tố: mục tiêu, phạm vi, deadline, trách nhiệm, bước tiếp theo.
  Không có nguy cơ hiểu lầm đáng kể.
  "misunderstanding_detection" phải là [] hoặc chỉ có nguy cơ mức "THẤP".
  Không có dấu hiệu ảnh hưởng xấu tới khách hàng, demo hoặc deadline.

- 85-94:
  Hai bên hiểu rõ phần lớn nội dung chính.
  Có thể còn 1 điểm nhỏ cần xác nhận, nhưng điểm đó không ảnh hưởng deadline, trách nhiệm, phạm vi chính, khách hàng hoặc kết quả công việc.
  Nếu có misunderstanding_detection thì chỉ nên là "THẤP".

- 70-84:
  Nhìn chung hai bên hiểu đúng.
  Còn một vài điểm cần xác nhận lại.
  Các điểm chưa rõ không gây rủi ro nghiêm trọng cho khách hàng, deadline, demo hoặc kết quả công việc.
  Có thể có misunderstanding_detection mức "THẤP" hoặc tối đa 1 mục "TRUNG BÌNH".

- 50-69:
  Có nhiều điểm mơ hồ về yêu cầu, phạm vi, trách nhiệm hoặc bước tiếp theo.
  Tuy nhiên chưa có dấu hiệu hiểu sai nghiêm trọng về deadline, khách hàng, demo hoặc người phụ trách.
  Không được dùng mức này nếu transcript có hiểu sai deadline quan trọng hoặc có nguy cơ ảnh hưởng khách hàng/demo.

- 25-49:
  Có ít nhất một hiểu lầm nghiêm trọng về deadline, phạm vi, trách nhiệm, kỳ vọng khách hàng hoặc điều kiện demo.
  Hai bên chưa thống nhất rõ cách xử lý.
  Có ít nhất một misunderstanding_detection mức "CAO".
  Dùng mức này khi có nguy cơ ảnh hưởng tiến độ, khách hàng, demo hoặc chất lượng bàn giao.

- 0-24:
  Hội thoại có nguy cơ thất bại cao.
  Có nhiều hiểu lầm nghiêm trọng cùng lúc, ví dụ: sai deadline, chưa rõ người phụ trách, không cam kết xử lý, khách hàng phàn nàn, demo có thể bị hủy.
  Có từ hai misunderstanding_detection mức "CAO" trở lên.
  Dùng mức này khi hội thoại thể hiện rủi ro rất lớn và chưa có hướng xử lý rõ.

Quy tắc giới hạn điểm bắt buộc:
- Nếu có hiểu sai deadline quan trọng, understanding_score không được vượt quá 49.
- Nếu có hiểu sai deadline và chưa rõ người phụ trách, understanding_score không được vượt quá 40.
- Nếu có nguy cơ ảnh hưởng khách hàng hoặc demo, understanding_score không được vượt quá 45.
- Nếu có từ 2 misunderstanding_detection mức "CAO" trở lên, understanding_score không được vượt quá 35.
- Nếu phía Việt Nam không thể cam kết xử lý trong khi deadline gần, understanding_score không được vượt quá 45.
- Nếu "misunderstanding_detection" là [] và hai bên đã xác nhận rõ mục tiêu, phạm vi, deadline, trách nhiệm, bước tiếp theo, understanding_score phải từ 95 đến 100.
- Nếu overall_sentiment là "Tốt", decisions có đầy đủ phạm vi, deadline, trách nhiệm và không có risk "TRUNG BÌNH" hoặc "CAO", understanding_score không được thấp hơn 90.

Tiêu chí overall_sentiment:
- "Tốt":
  Hội thoại hợp tác, lịch sự, có hướng giải quyết rõ.
  Hai bên xác nhận được phần lớn hoặc toàn bộ mục tiêu, phạm vi, deadline, trách nhiệm và bước tiếp theo.
- "Trung lập":
  Hội thoại bình thường, chưa rõ tích cực hay tiêu cực.
  Có trao đổi thông tin nhưng chưa chốt đủ nội dung quan trọng.
  Không có áp lực lớn, bất đồng rõ hoặc phàn nàn nghiêm trọng.
- "Căng thẳng":
  Có dấu hiệu áp lực, bất đồng, phàn nàn, thiếu thống nhất hoặc nguy cơ ảnh hưởng khách hàng/demo.
  Nếu transcript có khách hàng phàn nàn, demo có thể bị hủy, không cam kết deadline, hoặc hiểu sai deadline quan trọng thì overall_sentiment phải là "Căng thẳng".

Tiêu chí intent_analysis:
- Nêu mục tiêu chính của cuộc hội thoại.
- Chỉ ra yêu cầu, quyết định hoặc vấn đề đang được trao đổi nếu có.
- Không suy diễn ngoài transcript.
- Nếu mục tiêu chưa rõ thì nói rõ: "Mục tiêu chưa được xác nhận rõ".

Tiêu chí nuance_analysis:
- Nhận diện cách nói gián tiếp, né tránh, do dự, lịch sự quá mức hoặc hàm ý văn hóa.
- Phân biệt điều được nói trực tiếp và điều có thể đang được ngầm hiểu.
- Nêu tác động của sắc thái đó tới cách hai bên hiểu nhau.
- Nếu transcript chủ yếu là xác nhận rõ ràng, hãy nói rằng sắc thái giao tiếp rõ ràng, ít hàm ý và ít nguy cơ hiểu lầm.

Tiêu chí misunderstanding_detection:
- Chỉ liệt kê các nguy cơ hiểu lầm có căn cứ rõ ràng trong transcript.
- Không được tự suy diễn nguy cơ nếu hai bên đã xác nhận rõ mục tiêu, phạm vi, deadline, trách nhiệm và bước tiếp theo.
- Nếu không có nguy cơ hiểu lầm rõ ràng, trả về [].
- Không tạo risk chỉ vì có từ khóa như deadline, phạm vi, trách nhiệm, khách hàng.
- Chỉ tạo risk nếu có dấu hiệu:
  + Hai bên hiểu khác nhau về cùng một nội dung.
  + Một bên nói chưa rõ, chưa chắc, cần hỏi lại, chưa cam kết.
  + Có deadline/phạm vi/trách nhiệm bị hiểu sai.
  + Có câu nói gián tiếp hoặc hàm ý có thể bị hiểu sai.
- "CAO":
  Có thể làm sai deadline, trách nhiệm, phạm vi công việc, quyết định, kỳ vọng quan trọng, ảnh hưởng khách hàng hoặc demo.
- "TRUNG BÌNH":
  Có thể gây nhầm về cách thực hiện, mức độ ưu tiên, vai trò hoặc bước tiếp theo nhưng còn có thể xác nhận lại dễ dàng.
- "THẤP":
  Chỉ là khác biệt sắc thái, cách diễn đạt hoặc chi tiết nhỏ, ít ảnh hưởng tới kết quả công việc.
- Với mỗi nguy cơ, phải nêu rõ:
  + Cách phía Việt Nam có thể hiểu.
  + Cách phía Nhật Bản có thể hiểu.
  + Khuyến nghị xác nhận cụ thể.

Tiêu chí culture_explanation:
- Chỉ giải thích yếu tố văn hóa/giao tiếp Việt - Nhật liên quan trực tiếp tới transcript.
- Ưu tiên các điểm như nói gián tiếp, giữ thể diện, tránh từ chối thẳng, tôn trọng cấp bậc, xác nhận bằng văn bản.
- Không dùng khuôn mẫu văn hóa chung chung nếu transcript không có dấu hiệu liên quan.
- Nếu transcript đã rõ ràng và ít yếu tố văn hóa, hãy nói rằng hội thoại chủ yếu mang tính xác nhận công việc, ít rủi ro từ khác biệt văn hóa.

Tiêu chí reply_suggestion:
- Mỗi gợi ý phải là hành động hoặc câu phản hồi cụ thể, lịch sự và có thể dùng ngay sau hội thoại.
- Ưu tiên xác nhận deadline, trách nhiệm, phạm vi, người phụ trách và bước tiếp theo.
- Nếu có rủi ro hiểu lầm cao, gợi ý phải hướng tới xác nhận lại bằng văn bản hoặc câu hỏi rõ ràng.
- Nếu hội thoại đã rõ ràng, gợi ý nên tập trung vào việc gửi email tóm tắt, thực hiện đúng deadline và cập nhật tiến độ; không cần gợi ý hỏi lại những nội dung đã được xác nhận rõ.

Tiêu chí conversation_summary:
- "overall_feedback":
  Tóm tắt ngắn tình trạng hội thoại, điểm tốt và rủi ro chính.
  Nếu hội thoại đã rõ, nói rõ rằng hai bên đã thống nhất tốt về mục tiêu, phạm vi, deadline, trách nhiệm và bước tiếp theo.
  Nếu hội thoại rủi ro, nói rõ rủi ro chính là gì.
- "decisions":
  Chỉ liệt kê quyết định đã được nói rõ trong transcript.
  Quyết định phải là việc đã được thống nhất hoặc được một bên xác nhận rõ.
  Không đưa khuyến nghị, lời khuyên, hành động nên làm, dự định hỏi lại hoặc nội dung chưa chắc chắn vào decisions.
  Nếu câu chỉ mang tính "cần hỏi lại", "sẽ xem thêm", "chưa chắc", "cần xác nhận", "không dám cam kết", thì không được đưa vào decisions.
  Nếu chưa có quyết định rõ, trả về [].
- Không biến reply_suggestion hoặc recommendation thành decisions.

Tên hội thoại:
{conversation.conversation_name}

Transcript:
{transcript}

JSON bắt buộc có cấu trúc:
{{
  "intent_analysis": "Phân tích ý định chính của cuộc hội thoại",
  "nuance_analysis": "Phân tích sắc thái, cách nói gián tiếp, hàm ý, mức độ lịch sự",
  "misunderstanding_detection": [
    {{
      "title": "Tên nguy cơ hiểu lầm",
      "severity": "CAO",
      "left_title": "Quan điểm Việt Nam",
      "left_text": "Cách phía Việt Nam có thể đang hiểu vấn đề",
      "right_title": "Quan điểm Nhật Bản",
      "right_text": "Cách phía Nhật có thể đang hiểu vấn đề",
      "recommendation": "Khuyến nghị cụ thể để giảm hiểu lầm"
    }}
  ],
  "culture_explanation": "Giải thích yếu tố văn hóa/giao tiếp Việt - Nhật liên quan",
  "reply_suggestion": [
    "Gợi ý phản hồi/hành động 1",
    "Gợi ý phản hồi/hành động 2"
  ],
  "conversation_summary": {{
    "overall_feedback": "Nhận xét tổng quan từ AI",
    "decisions": [
      "Quyết định chính 1",
      "Quyết định chính 2"
    ],
    "understanding_score": 0,
    "overall_sentiment": "Tốt hoặc Trung lập hoặc Căng thẳng"
  }}
}}

Lưu ý: Giá trị 0 trong cấu trúc trên chỉ là placeholder schema. Khi trả kết quả thật,
"understanding_score" phải là số nguyên được tự chấm theo rubric, không được copy placeholder.
"""

    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json; charset=utf-8",
            },
            json={
                "model": os.getenv("GROQ_MODEL", "llama-3.1-8b-instant"),
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "Bạn là AI chuyên phân tích ý nghĩa và sắc thái giao tiếp Việt Nam - Nhật Bản. "
                            "Luôn trả lời JSON hợp lệ bằng tiếng Việt có dấu đầy đủ, UTF-8."
                        ),
                    },
                    {
                        "role": "user",
                        "content": prompt,
                    },
                ],
                "temperature": 0.2,
            },
        )

    if response.status_code >= 400:
        raise HTTPException(
            status_code=500,
            detail=f"Groq API error: {response.text}",
        )

    content = response.json()["choices"][0]["message"]["content"]
    return extract_json_from_ai(content)


def create_analysis_logs_from_ai_data(
    conversation_id: int,
    ai_data: dict[str, Any],
) -> list[AnalysisLog]:
    mapping = [
        ("INTENT_ANALYSIS", "intent_analysis"),
        ("NUANCE_ANALYSIS", "nuance_analysis"),
        ("MISUNDERSTANDING_DETECTION", "misunderstanding_detection"),
        ("CULTURE_EXPLANATION", "culture_explanation"),
        ("REPLY_SUGGESTION", "reply_suggestion"),
        ("CONVERSATION_SUMMARY", "conversation_summary"),
    ]

    logs: list[AnalysisLog] = []

    for task_type, key in mapping:
        value = ai_data.get(key)

        if value is None:
            continue

        if isinstance(value, str):
            output_text = value
        else:
            output_text = json.dumps(value, ensure_ascii=False)

        logs.append(
            AnalysisLog(
                message_id=None,
                conversation_id=conversation_id,
                ai_task_type=task_type,
                output_text=output_text,
                created_at=datetime.utcnow(),
            )
        )

    return logs


def build_metrics(
    duration_minutes: int | None,
    understanding_score: int,
    overall_sentiment: str,
) -> list[dict[str, Any]]:
    sentiment_subtitle = {
        "Tốt": "Hợp tác rõ ràng",
        "Trung lập": "Cần theo dõi",
        "Căng thẳng": "Cần thống nhất",
    }.get(overall_sentiment, "Chưa có dữ liệu")

    return [
        {
            "title": "THỜI LƯỢNG",
            "value": str(duration_minutes or 0),
            "subtitle": "Phút tương tác",
            "accent_classes": "border-blue-100 bg-blue-50",
            "value_classes": "text-blue-600",
        },
        {
            "title": "ĐỘ HIỂU",
            "value": f"{understanding_score}%",
            "subtitle": "Truyền đạt chính xác"
            if understanding_score
            else "Chưa có dữ liệu",
            "accent_classes": "border-emerald-100 bg-emerald-50",
            "value_classes": "text-emerald-600",
        },
        {
            "title": "CẢM XÚC CHUNG",
            "value": overall_sentiment,
            "subtitle": sentiment_subtitle,
            "accent_classes": "border-purple-100 bg-purple-50",
            "value_classes": "text-purple-600",
        },
    ]


def build_perception_gaps(
    logs: list[AnalysisLog],
    transcript: str,
) -> list[dict[str, Any]]:
    output_text = get_latest_log_text(
        logs,
        "MISUNDERSTANDING_DETECTION",
    )
    parsed = parse_json_value(output_text)

    gaps: list[dict[str, Any]] = []

    if isinstance(parsed, dict):
        parsed = [parsed]

    if isinstance(parsed, list):
        for item in parsed:
            if not isinstance(item, dict):
                continue

            severity = normalize_gap_severity(item.get("severity", "TRUNG BÌNH"))

            gaps.append(
                {
                    "title": str(item.get("title", "Nguy cơ hiểu lầm")),
                    "severity": severity,
                    "severity_classes": get_severity_classes(severity),
                    "card_classes": get_gap_card_classes(severity),
                    "left_title": str(item.get("left_title", "Quan điểm Việt Nam")),
                    "left_text": str(item.get("left_text", "")),
                    "right_title": str(item.get("right_title", "Quan điểm Nhật Bản")),
                    "right_text": str(item.get("right_text", "")),
                    "recommendation": str(item.get("recommendation", "")),
                }
            )

    elif output_text:
        severity = "TRUNG BÌNH"

        gaps.append(
            {
                "title": "Nguy cơ hiểu lầm",
                "severity": severity,
                "severity_classes": get_severity_classes(severity),
                "card_classes": get_gap_card_classes(severity),
                "left_title": "Nội dung hội thoại",
                "left_text": transcript,
                "right_title": "AI phân tích",
                "right_text": output_text,
                "recommendation": "Nên xác nhận lại nội dung quan trọng bằng văn bản.",
            }
        )

    return gaps


def build_action_items(logs: list[AnalysisLog]) -> list[str]:
    output_text = get_latest_log_text(logs, "REPLY_SUGGESTION")
    parsed = parse_json_value(output_text)

    if isinstance(parsed, list):
        return [str(item) for item in parsed]

    if output_text:
        return [output_text]

    return []


def build_summary_data(logs: list[AnalysisLog]) -> dict[str, Any]:
    output_text = get_latest_log_text(logs, "CONVERSATION_SUMMARY")
    parsed = parse_json_value(output_text)

    if isinstance(parsed, dict):
        return parsed

    if output_text:
        return {
            "overall_feedback": output_text,
            "decisions": [],
            "understanding_score": 80,
            "overall_sentiment": "Tốt",
        }

    return {
        "overall_feedback": "Chưa có dữ liệu phân tích trong database.",
        "decisions": [],
        "understanding_score": 0,
        "overall_sentiment": "N/A",
    }


def normalize_understanding_score(value: Any) -> int:
    try:
        score = int(float(value))
    except (TypeError, ValueError):
        return 0

    return max(0, min(100, score))


def normalize_overall_sentiment(value: Any) -> str:
    sentiment = str(value or "").strip()

    if not sentiment or sentiment.upper() == "N/A":
        return "N/A"

    normalized = normalize_search_text(sentiment)

    if "cang" in normalized or "ap luc" in normalized or "bat dong" in normalized:
        return "Căng thẳng"

    if "trung lap" in normalized or "neutral" in normalized:
        return "Trung lập"

    if "tot" in normalized or "tich cuc" in normalized or "positive" in normalized:
        return "Tốt"

    return "Trung lập"


def build_analysis_from_db(
    conversation: AnalysisConversation,
    messages: list[AnalysisMessage],
    logs: list[AnalysisLog],
) -> AnalysisResponse:
    if conversation.conversation_id is None:
        raise HTTPException(status_code=500, detail="Conversation has no id")

    transcript = "\n".join(message.text for message in messages)

    duration_minutes = calculate_duration_minutes(
        conversation.started_at,
        conversation.ended_at,
    )

    summary_data = build_summary_data(logs)

    understanding_score = normalize_understanding_score(
        summary_data.get("understanding_score")
    )
    overall_sentiment = normalize_overall_sentiment(
        summary_data.get("overall_sentiment")
    )
    ai_overall_feedback = str(
        summary_data.get("overall_feedback")
        or "Chưa có dữ liệu phân tích trong database."
    )

    decisions = [
        str(item)
        for item in summary_data.get("decisions", [])
    ]

    action_items = build_action_items(logs)
    perception_gaps = build_perception_gaps(logs, transcript)

    generated_log_count = len(
        [
            log
            for log in logs
            if log.ai_task_type in AI_ANALYSIS_TASK_TYPES
        ]
    )

    return AnalysisResponse(
        id=conversation.conversation_id,
        meeting_title=conversation.conversation_name,
        meeting_date=conversation.created_at.strftime("%d/%m/%Y")
        if conversation.created_at
        else None,
        duration_minutes=duration_minutes,
        understanding_score=understanding_score,
        overall_sentiment=overall_sentiment,
        ai_overall_feedback=ai_overall_feedback,
        metrics=build_metrics(
            duration_minutes,
            understanding_score,
            overall_sentiment,
        ),
        perception_gaps=perception_gaps,
        decisions=decisions,
        action_items=action_items,
        ai_log_count=generated_log_count,
    )


async def ensure_analysis_exists(conversation_id: int) -> AnalysisResponse:
    with Session(engine) as session:
        conversation = get_conversation_or_404(session, conversation_id)

        if conversation.conversation_id is None:
            raise HTTPException(status_code=500, detail="Conversation has no id")

        messages = get_messages_by_conversation(
            session,
            conversation.conversation_id,
        )
        logs = get_ai_logs_by_conversation(
            session,
            conversation.conversation_id,
        )

        if has_full_analysis(logs):
            return build_analysis_from_db(
                conversation=conversation,
                messages=messages,
                logs=logs,
            )

    result = await run_conversation_analysis(
        conversation_id=conversation_id,
        replace_existing=True,
    )

    return result.analysis


@router.get("/latest/ensure", response_model=AnalysisResponse)
async def ensure_latest_analysis() -> AnalysisResponse:
    with Session(engine) as session:
        statement = (
            select(AnalysisConversation)
            .order_by(AnalysisConversation.created_at.desc())
            .limit(1)
        )
        conversation = session.exec(statement).first()

        if not conversation or conversation.conversation_id is None:
            raise HTTPException(status_code=404, detail="No conversation found")

        conversation_id = conversation.conversation_id

    return await ensure_analysis_exists(conversation_id)


@router.get("/latest", response_model=AnalysisResponse)
def get_latest_analysis() -> AnalysisResponse:
    with Session(engine) as session:
        statement = (
            select(AnalysisConversation)
            .order_by(AnalysisConversation.created_at.desc())
            .limit(1)
        )
        conversation = session.exec(statement).first()

        if not conversation or conversation.conversation_id is None:
            raise HTTPException(status_code=404, detail="No conversation found")

        messages = get_messages_by_conversation(
            session,
            conversation.conversation_id,
        )
        logs = get_ai_logs_by_conversation(
            session,
            conversation.conversation_id,
        )

        return build_analysis_from_db(
            conversation=conversation,
            messages=messages,
            logs=logs,
        )


@router.get("/search", response_model=list[AnalysisSearchItem])
def search_analyses(
    q: str = Query(..., min_length=1),
    limit: int = Query(default=10, ge=1, le=50),
) -> list[AnalysisSearchItem]:
    keyword = normalize_search_text(q.strip())

    if not keyword:
        return []

    with Session(engine) as session:
        statement = (
            select(AnalysisConversation)
            .order_by(AnalysisConversation.created_at.desc())
            .limit(200)
        )
        conversations = session.exec(statement).all()

        results: list[AnalysisSearchItem] = []

        for conversation in conversations:
            if conversation.conversation_id is None:
                continue

            messages = get_messages_by_conversation(
                session,
                conversation.conversation_id,
            )
            logs = get_ai_logs_by_conversation(
                session,
                conversation.conversation_id,
            )

            searchable_text = normalize_search_text(
                " ".join(
                    [
                        conversation.conversation_name or "",
                        *[message.text for message in messages],
                        *[log.output_text for log in logs],
                        *[log.ai_task_type for log in logs],
                    ]
                )
            )

            if keyword not in searchable_text:
                continue

            analysis = build_analysis_from_db(
                conversation=conversation,
                messages=messages,
                logs=logs,
            )

            results.append(
                AnalysisSearchItem(
                    id=analysis.id,
                    meeting_title=analysis.meeting_title,
                    meeting_date=analysis.meeting_date,
                    duration_minutes=analysis.duration_minutes,
                    understanding_score=analysis.understanding_score,
                    overall_sentiment=analysis.overall_sentiment,
                    ai_overall_feedback=analysis.ai_overall_feedback,
                )
            )

            if len(results) >= limit:
                break

        return results


@router.get("/{conversation_id}/ensure", response_model=AnalysisResponse)
async def ensure_analysis_by_id(conversation_id: int) -> AnalysisResponse:
    return await ensure_analysis_exists(conversation_id)


@router.post("/{conversation_id}/run", response_model=AnalysisRunResponse)
async def run_conversation_analysis(
    conversation_id: int,
    replace_existing: bool = True,
) -> AnalysisRunResponse:
    with Session(engine) as session:
        conversation = get_conversation_or_404(session, conversation_id)

        if conversation.conversation_id is None:
            raise HTTPException(status_code=500, detail="Conversation has no id")

        messages = get_messages_by_conversation(
            session,
            conversation.conversation_id,
        )

        if not messages:
            raise HTTPException(
                status_code=400,
                detail="Conversation has no messages to analyze",
            )

    ai_data = await analyze_conversation_with_ai(
        conversation=conversation,
        messages=messages,
    )

    new_logs = create_analysis_logs_from_ai_data(
        conversation_id=conversation_id,
        ai_data=ai_data,
    )

    if not new_logs:
        raise HTTPException(
            status_code=500,
            detail="AI returned no analysis logs",
        )

    with Session(engine) as session:
        conversation = get_conversation_or_404(session, conversation_id)

        if conversation.conversation_id is None:
            raise HTTPException(status_code=500, detail="Conversation has no id")

        messages = get_messages_by_conversation(
            session,
            conversation.conversation_id,
        )

        if replace_existing:
            old_logs = session.exec(
                select(AnalysisLog)
                .where(AnalysisLog.conversation_id == conversation_id)
                .where(AnalysisLog.ai_task_type.in_(AI_ANALYSIS_TASK_TYPES))
            ).all()

            for old_log in old_logs:
                session.delete(old_log)

        for log in new_logs:
            session.add(log)

        session.commit()

        logs = get_ai_logs_by_conversation(
            session,
            conversation.conversation_id,
        )

        analysis = build_analysis_from_db(
            conversation=conversation,
            messages=messages,
            logs=logs,
        )

        return AnalysisRunResponse(
            conversation_id=conversation.conversation_id,
            inserted_logs=len(new_logs),
            analysis=analysis,
        )


def register_pdf_font() -> str:
    font_name = "TrueTalkFont"

    try:
        pdfmetrics.getFont(font_name)
        return font_name
    except Exception:
        pass

    candidates = [
        "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/calibri.ttf",
        "C:/Windows/Fonts/tahoma.ttf",
        "C:/Windows/Fonts/verdana.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]

    for font_path in candidates:
        if Path(font_path).exists():
            try:
                pdfmetrics.registerFont(TTFont(font_name, font_path))
                return font_name
            except Exception:
                continue

    return "Helvetica"


def pdf_paragraph(text: object, style: ParagraphStyle) -> Paragraph:
    safe_text = escape(str(text or "")).replace("\n", "<br/>")
    return Paragraph(safe_text, style)


def build_analysis_pdf(analysis: AnalysisResponse) -> Path:
    font_name = register_pdf_font()

    reports_dir = Path(tempfile.gettempdir()) / "truetalk_reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    file_path = (
        reports_dir
        / f"analysis_report_{analysis.id}_{uuid.uuid4().hex[:8]}.pdf"
    )

    doc = SimpleDocTemplate(
        str(file_path),
        pagesize=A4,
        rightMargin=1.7 * cm,
        leftMargin=1.7 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm,
    )

    base_styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "TrueTalkTitle",
        parent=base_styles["Title"],
        fontName=font_name,
        fontSize=20,
        leading=26,
        spaceAfter=14,
    )

    heading_style = ParagraphStyle(
        "TrueTalkHeading",
        parent=base_styles["Heading2"],
        fontName=font_name,
        fontSize=13,
        leading=18,
        spaceBefore=12,
        spaceAfter=8,
    )

    normal_style = ParagraphStyle(
        "TrueTalkNormal",
        parent=base_styles["Normal"],
        fontName=font_name,
        fontSize=10,
        leading=15,
    )

    small_style = ParagraphStyle(
        "TrueTalkSmall",
        parent=base_styles["Normal"],
        fontName=font_name,
        fontSize=9,
        leading=13,
        textColor=colors.HexColor("#475569"),
    )

    story = []

    story.append(pdf_paragraph("Báo cáo phân tích hội thoại", title_style))
    story.append(pdf_paragraph(analysis.meeting_title, heading_style))

    info_data = [
        [
            pdf_paragraph("Ngày họp", small_style),
            pdf_paragraph(analysis.meeting_date or "Không có dữ liệu", normal_style),
        ],
        [
            pdf_paragraph("Thời lượng", small_style),
            pdf_paragraph(f"{analysis.duration_minutes or 0} phút", normal_style),
        ],
        [
            pdf_paragraph("Độ hiểu", small_style),
            pdf_paragraph(f"{analysis.understanding_score}%", normal_style),
        ],
        [
            pdf_paragraph("Cảm xúc chung", small_style),
            pdf_paragraph(analysis.overall_sentiment, normal_style),
        ],
    ]

    info_table = Table(info_data, colWidths=[4 * cm, 12 * cm])
    info_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#F1F5F9")),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )

    story.append(info_table)
    story.append(Spacer(1, 10))

    story.append(pdf_paragraph("Nhận xét tổng quan từ AI", heading_style))
    story.append(pdf_paragraph(analysis.ai_overall_feedback, normal_style))

    story.append(pdf_paragraph("Chỉ số phân tích", heading_style))

    metrics_data = [
        [
            pdf_paragraph("Chỉ số", small_style),
            pdf_paragraph("Giá trị", small_style),
            pdf_paragraph("Mô tả", small_style),
        ]
    ]

    for metric in analysis.metrics:
        metrics_data.append(
            [
                pdf_paragraph(metric.get("title", ""), normal_style),
                pdf_paragraph(metric.get("value", ""), normal_style),
                pdf_paragraph(metric.get("subtitle", ""), normal_style),
            ]
        )

    metrics_table = Table(metrics_data, colWidths=[5 * cm, 4 * cm, 7 * cm])
    metrics_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#DBEAFE")),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )

    story.append(metrics_table)
    story.append(Spacer(1, 10))

    story.append(pdf_paragraph("Điểm lệch nhận thức", heading_style))

    if not analysis.perception_gaps:
        story.append(
            pdf_paragraph(
                "Chưa phát hiện điểm lệch nhận thức nào.",
                normal_style,
            )
        )

    for index, gap in enumerate(analysis.perception_gaps, start=1):
        story.append(
            pdf_paragraph(
                f"{index}. {gap.get('title', 'Vấn đề chưa đặt tên')} - {gap.get('severity', '')}",
                normal_style,
            )
        )

        gap_table = Table(
            [
                [
                    pdf_paragraph(gap.get("left_title", "Quan điểm Việt Nam"), small_style),
                    pdf_paragraph(gap.get("left_text", ""), normal_style),
                ],
                [
                    pdf_paragraph(gap.get("right_title", "Quan điểm Nhật Bản"), small_style),
                    pdf_paragraph(gap.get("right_text", ""), normal_style),
                ],
                [
                    pdf_paragraph("Khuyến nghị AI", small_style),
                    pdf_paragraph(gap.get("recommendation", ""), normal_style),
                ],
            ],
            colWidths=[4 * cm, 12 * cm],
        )

        gap_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#FEF3C7")),
                    ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                    ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                    ("TOPPADDING", (0, 0), (-1, -1), 7),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                ]
            )
        )

        story.append(gap_table)
        story.append(Spacer(1, 8))

    story.append(pdf_paragraph("Tóm tắt nội dung / Quyết định chính", heading_style))

    for index, decision in enumerate(analysis.decisions, start=1):
        story.append(pdf_paragraph(f"{index}. {decision}", normal_style))

    story.append(pdf_paragraph("Action items", heading_style))

    for index, item in enumerate(analysis.action_items, start=1):
        story.append(pdf_paragraph(f"{index}. {item}", normal_style))

    doc.build(story)

    return file_path


@router.get("/latest/export-pdf")
def export_latest_analysis_pdf() -> FileResponse:
    analysis = get_latest_analysis()
    file_path = build_analysis_pdf(analysis)

    return FileResponse(
        path=str(file_path),
        media_type="application/pdf",
        filename=f"bao_cao_phan_tich_{analysis.id}.pdf",
    )


@router.get("/{conversation_id}/export-pdf")
def export_analysis_pdf(conversation_id: int) -> FileResponse:
    analysis = get_analysis_by_id(conversation_id)
    file_path = build_analysis_pdf(analysis)

    return FileResponse(
        path=str(file_path),
        media_type="application/pdf",
        filename=f"bao_cao_phan_tich_{conversation_id}.pdf",
    )


@router.get("/{conversation_id}", response_model=AnalysisResponse)
def get_analysis_by_id(conversation_id: int) -> AnalysisResponse:
    with Session(engine) as session:
        conversation = get_conversation_or_404(session, conversation_id)

        if conversation.conversation_id is None:
            raise HTTPException(status_code=500, detail="Conversation has no id")

        messages = get_messages_by_conversation(
            session,
            conversation.conversation_id,
        )
        logs = get_ai_logs_by_conversation(
            session,
            conversation.conversation_id,
        )

        return build_analysis_from_db(
            conversation=conversation,
            messages=messages,
            logs=logs,
        )
