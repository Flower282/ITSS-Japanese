from __future__ import annotations

import json
import os
import re
import unicodedata
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from src.backend.endpoints.analysis_pdf import build_analysis_pdf
from src.backend.translateJp.analize_suggest import (
    HISTORY_FILE as SUGGEST_HISTORY_FILE,
    analyze_and_suggest_chat,
)
from src.backend.translateJp.api_clients import (
    translate_japanese_to_vietnamese,
    translate_vietnamese_to_japanese,
)
from src.db.session import engine
from src.repositories.message_repo import message_repo
from src.models.analysis_models import (
    AnalysisConversation,
    AnalysisLog,
    AnalysisMessage,
)


router = APIRouter(prefix="/analysis", tags=["analysis"])


ANALYSIS_TRANSLATION_CACHE: dict[tuple[int, str, int], AnalysisResponse] = {}


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
    understanding_score: int = 0
    overall_sentiment: str = ""
    ai_overall_feedback: str = ""


class AnalysisRunResponse(BaseModel):
    conversation_id: int
    inserted_logs: int
    analysis: AnalysisResponse


class ConversationListItem(BaseModel):
    id: int
    label: str
    subtitle: str | None = None


class TranslateMessageItem(BaseModel):
    id: int
    role: str
    text: str
    time: str
    translation: str | None = None
    note: str | None = None
    tags: list[str] = Field(default_factory=list)
    is_marked: int = 0


class MarkMessageResponse(BaseModel):
    id: int
    is_marked: int


class ReplySuggestionItem(BaseModel):
    id: str
    title: str
    description: str


class TranslateContextResponse(BaseModel):
    conversation_id: int
    conversation_name: str
    messages: list[TranslateMessageItem]
    intent_analysis: str
    nuance_analysis: str
    culture_explanation: str
    reply_suggestions: list[ReplySuggestionItem]
    partner_text: str
    translation_text: str


class MessageCreateRequest(BaseModel):
    text: str = Field(min_length=1)
    role: str = Field(default="you", pattern="^(listen|you)$")
    translation: str | None = None
    note: str | None = None
    tags: list[str] = Field(default_factory=list)


class ConversationUpdateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)


class DashboardInsightItem(BaseModel):
    icon: str
    title: str
    description: str
    link_label: str
    status_label: str
    status_classes: str


class DashboardOverviewResponse(BaseModel):
    total_conversations: int
    understanding_score: int
    suggestions_count: int
    interaction_time: str
    latest_analysis_id: int | None
    insights: list[DashboardInsightItem]


def parse_json_value(text: str | None) -> Any:
    if not text:
        return None

    try:
        return json.loads(text)
    except Exception:
        return None


def normalize_search_text(value: object) -> str:
    text = str(value or "").replace("\u0110", "D").replace("\u0111", "d").lower()
    text = unicodedata.normalize("NFD", text)
    text = "".join(
        char for char in text if unicodedata.category(char) != "Mn"
    )
    return text.replace("đ", "d")


def score_conversation_name_match(keyword: str, conversation_name: str) -> float:
    normalized_name = normalize_search_text(conversation_name)

    if not keyword or not normalized_name:
        return 0

    if normalized_name == keyword:
        return 100

    if normalized_name.startswith(keyword):
        return 90 + min(9, len(keyword) / max(len(normalized_name), 1) * 9)

    words = normalized_name.split()
    if any(word.startswith(keyword) for word in words):
        return 80 + min(9, len(keyword) / max(len(normalized_name), 1) * 9)

    if keyword in normalized_name:
        return 70 + min(9, len(keyword) / max(len(normalized_name), 1) * 9)

    return SequenceMatcher(None, keyword, normalized_name).ratio() * 60


def find_closest_conversation_names(
    keyword: str,
    conversations: list[AnalysisConversation],
    limit: int = 10,
) -> list[AnalysisConversation]:
    normalized_keyword = normalize_search_text(keyword.strip())

    if not normalized_keyword:
        return []

    ranked = [
        (
            score_conversation_name_match(
                normalized_keyword,
                conversation.conversation_name or "",
            ),
            conversation.created_at or datetime.min,
            conversation,
        )
        for conversation in conversations
        if conversation.conversation_id is not None
    ]

    ranked = [item for item in ranked if item[0] > 0]
    ranked.sort(key=lambda item: (item[0], item[1]), reverse=True)

    return [conversation for _, _, conversation in ranked[:limit]]


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


def get_latest_displayable_conversation(
    session: Session,
) -> AnalysisConversation | None:
    conversations = session.exec(
        select(AnalysisConversation)
        .order_by(AnalysisConversation.created_at.desc())
    ).all()

    fallback_conversation: AnalysisConversation | None = None

    for conversation in conversations:
        if conversation.conversation_id is None:
            continue

        if fallback_conversation is None:
            fallback_conversation = conversation

        if get_messages_by_conversation(session, conversation.conversation_id):
            return conversation

    return fallback_conversation


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
- Chỉ trả về JSON hợp lệ.
- Không dùng markdown.
- Không giải thích ngoài JSON.
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


def analysis_to_dict(analysis: AnalysisResponse) -> dict[str, Any]:
    if hasattr(analysis, "model_dump"):
        return analysis.model_dump()

    return analysis.dict()


def apply_analysis_translation(
    analysis: AnalysisResponse,
    translated: dict[str, Any],
) -> AnalysisResponse:
    data = analysis_to_dict(analysis)

    for key in [
        "meeting_title",
        "overall_sentiment",
        "ai_overall_feedback",
        "decisions",
        "action_items",
    ]:
        if key in translated:
            data[key] = translated[key]

    translated_metrics = translated.get("metrics")
    if isinstance(translated_metrics, list):
        metrics = data.get("metrics") or []
        for index, metric in enumerate(metrics):
            if index >= len(translated_metrics):
                break

            translated_metric = translated_metrics[index]
            if not isinstance(translated_metric, dict):
                continue

            for key in ["title", "value", "subtitle"]:
                if key in translated_metric:
                    metric[key] = translated_metric[key]

    translated_gaps = translated.get("perception_gaps")
    if isinstance(translated_gaps, list):
        gaps = data.get("perception_gaps") or []
        for index, gap in enumerate(gaps):
            if index >= len(translated_gaps):
                break

            translated_gap = translated_gaps[index]
            if not isinstance(translated_gap, dict):
                continue

            for key in [
                "title",
                "severity",
                "left_title",
                "left_text",
                "right_title",
                "right_text",
                "recommendation",
            ]:
                if key in translated_gap:
                    gap[key] = translated_gap[key]

    return AnalysisResponse(**data)


def normalize_vietnamese_display_text(value: Any) -> str:
    text = str(value or "").strip().replace("\u0110", "D").replace("\u0111", "d").lower()
    text = unicodedata.normalize("NFD", text)
    text = "".join(
        char for char in text if unicodedata.category(char) != "Mn"
    )
    text = re.sub(r"[^a-z0-9%:/-]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


VIETNAMESE_VISIBLE_PATTERNS = [
    "nguy co hieu lam",
    "phia viet nam",
    "phia nhat ban",
    "quan diem viet nam",
    "quan diem nhat ban",
    "pham vi sua doi",
    "pham vi cong viec",
    "deadline",
    "de tranh hieu lam",
    "xac nhan",
    "gui email",
    "hoi lai",
    "hieu rang",
    "tot",
    "trung lap",
    "cang thang",
]


def payload_contains_vietnamese_display_text(value: Any) -> bool:
    if isinstance(value, str):
        normalized = normalize_vietnamese_display_text(value)
        return any(pattern in normalized for pattern in VIETNAMESE_VISIBLE_PATTERNS)

    if isinstance(value, dict):
        return any(
            payload_contains_vietnamese_display_text(item)
            for item in value.values()
        )

    if isinstance(value, list):
        return any(payload_contains_vietnamese_display_text(item) for item in value)

    return False


def translation_shape_matches(source: Any, translated: Any) -> bool:
    if isinstance(source, dict):
        if not isinstance(translated, dict):
            return False
        if set(source.keys()) != set(translated.keys()):
            return False
        return all(
            translation_shape_matches(source[key], translated[key])
            for key in source
        )

    if isinstance(source, list):
        if not isinstance(translated, list):
            return False
        if len(source) != len(translated):
            return False
        return all(
            translation_shape_matches(source_item, translated_item)
            for source_item, translated_item in zip(source, translated)
        )

    return True


async def request_japanese_translation(
    *,
    api_key: str,
    payload: dict[str, Any],
    prompt: str,
    temperature: float,
) -> dict[str, Any]:
    model_name = os.getenv("GROQ_TRANSLATION_MODEL") or os.getenv(
        "GROQ_MODEL",
        "llama-3.3-70b-versatile",
    )

    async with httpx.AsyncClient(timeout=45) as client:
        response = await client.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json; charset=utf-8",
            },
            json={
                "model": model_name,
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "You are a precise Vietnamese-to-Japanese translator for business UI and PDF reports. "
                            "Translate complete thoughts naturally. "
                            "Never leave Vietnamese, romanized Vietnamese, or mixed Vietnamese-Japanese text in any visible field. "
                            "You only return valid JSON."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                "temperature": temperature,
            },
        )

    if response.status_code >= 400:
        raise HTTPException(
            status_code=500,
            detail=f"Groq translation API error: {response.text}",
        )

    content = response.json()["choices"][0]["message"]["content"]
    translated = extract_json_from_ai(content)

    if not translation_shape_matches(payload, translated):
        raise HTTPException(
            status_code=500,
            detail="Japanese translation returned an invalid payload shape",
        )

    return translated


async def translate_analysis_to_japanese(
    analysis: AnalysisResponse,
) -> AnalysisResponse:
    if analysis.id is None:
        return analysis

    cache_key = (analysis.id, "jp-ai-v4", analysis.ai_log_count)
    cached = ANALYSIS_TRANSLATION_CACHE.get(cache_key)

    if cached:
        return cached

    api_key = os.getenv("GROQ_API_KEY")

    if not api_key:
        raise HTTPException(
            status_code=500,
            detail="Missing GROQ_API_KEY for Japanese analysis translation",
        )

    payload = {
        "meeting_title": analysis.meeting_title,
        "overall_sentiment": analysis.overall_sentiment,
        "ai_overall_feedback": analysis.ai_overall_feedback,
        "metrics": [
            {
                "title": metric.get("title", ""),
                "value": metric.get("value", ""),
                "subtitle": metric.get("subtitle", ""),
            }
            for metric in analysis.metrics
        ],
        "perception_gaps": [
            {
                "title": gap.get("title", ""),
                "severity": gap.get("severity", ""),
                "left_title": gap.get("left_title", ""),
                "left_text": gap.get("left_text", ""),
                "right_title": gap.get("right_title", ""),
                "right_text": gap.get("right_text", ""),
                "recommendation": gap.get("recommendation", ""),
            }
            for gap in analysis.perception_gaps
        ],
        "decisions": analysis.decisions,
        "action_items": analysis.action_items,
    }

    prompt = f"""
Translate this Vietnamese conversation-analysis payload into natural, professional Japanese for a Japanese UI and PDF report.

Critical rules:
- Return valid JSON only. Do not use markdown.
- Keep exactly the same JSON keys and list lengths.
- Translate every user-facing text value completely into Japanese.
- Rewrite whole sentences naturally. Do not translate word-by-word.
- Do not leave Vietnamese, romanized Vietnamese, or mixed Vietnamese-Japanese text in any visible field.
- Preserve only numbers, dates, percentages, empty strings, and product/test codes that are names.
- Severity values must be exactly one of: "低", "中", "高".
- Sentiment values must be natural Japanese, for example "良好", "中立", or "緊張".

JSON payload:
{json.dumps(payload, ensure_ascii=False)}
"""

    try:
        translated = await request_japanese_translation(
            api_key=api_key,
            payload=payload,
            prompt=prompt,
            temperature=0.1,
        )

        if payload_contains_vietnamese_display_text(translated):
            retry_prompt = f"""
The previous JSON still contains Vietnamese, romanized Vietnamese, or mixed Vietnamese-Japanese text.
Rewrite the entire payload again in natural Japanese.
Return valid JSON only, with the exact same keys and list lengths.
Every visible value must be fully Japanese.

Invalid JSON to fix:
{json.dumps(translated, ensure_ascii=False)}
"""
            translated = await request_japanese_translation(
                api_key=api_key,
                payload=payload,
                prompt=retry_prompt,
                temperature=0.0,
            )

        if payload_contains_vietnamese_display_text(translated):
            raise HTTPException(
                status_code=500,
                detail="Japanese translation still contains Vietnamese text",
            )
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Cannot translate analysis to Japanese",
        )

    localized = apply_analysis_translation(analysis, translated)
    ANALYSIS_TRANSLATION_CACHE[cache_key] = localized
    return localized


async def localize_analysis_response(
    analysis: AnalysisResponse,
    lang: str,
) -> AnalysisResponse:
    if lang != "jp":
        return analysis
    return await translate_analysis_to_japanese(analysis)


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
async def ensure_latest_analysis(
    lang: str = Query(default="vn", pattern="^(vn|jp)$"),
) -> AnalysisResponse:
    with Session(engine) as session:
        conversation = get_latest_displayable_conversation(session)

        if not conversation or conversation.conversation_id is None:
            raise HTTPException(status_code=404, detail="No conversation found")

        conversation_id = conversation.conversation_id

    analysis = await ensure_analysis_exists(conversation_id)
    return await localize_analysis_response(analysis, lang)


@router.get("/latest", response_model=AnalysisResponse)
async def get_latest_analysis(
    lang: str = Query(default="vn", pattern="^(vn|jp)$"),
) -> AnalysisResponse:
    with Session(engine) as session:
        conversation = get_latest_displayable_conversation(session)

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

        analysis = build_analysis_from_db(
            conversation=conversation,
            messages=messages,
            logs=logs,
        )
        return await localize_analysis_response(analysis, lang)


@router.get("/search", response_model=list[AnalysisSearchItem])
def search_analyses(
    q: str = Query(..., min_length=1),
    limit: int = Query(default=10, ge=1, le=50),
) -> list[AnalysisSearchItem]:
    keyword = q.strip()

    if not keyword:
        return []

    with Session(engine) as session:
        statement = (
            select(AnalysisConversation)
            .order_by(AnalysisConversation.created_at.desc())
        )
        conversations = session.exec(statement).all()
        matched_conversations = find_closest_conversation_names(
            keyword,
            list(conversations),
            limit,
        )

        results: list[AnalysisSearchItem] = []

        for conversation in matched_conversations:
            if conversation.conversation_id is None:
                continue

            results.append(
                AnalysisSearchItem(
                    id=conversation.conversation_id,
                    meeting_title=conversation.conversation_name,
                    meeting_date=conversation.created_at.strftime("%d/%m/%Y")
                    if conversation.created_at
                    else None,
                )
            )

        return results


def pack_message_text(
    text: str,
    *,
    translation: str | None = None,
    note: str | None = None,
    tags: list[str] | None = None,
) -> str:
    """Persist translation only in DB (plain string). Note/tags use minimal JSON."""
    content = (translation or "").strip() or text.strip()
    note_clean = (note or "").strip()
    tag_list = [tag for tag in (tags or []) if tag]
    if note_clean or tag_list:
        payload: dict[str, Any] = {"content": content}
        if note_clean:
            payload["note"] = note_clean
        if tag_list:
            payload["tags"] = tag_list
        return json.dumps(payload, ensure_ascii=False)
    return content


def unpack_message_text(raw: str) -> dict[str, Any]:
    value = (raw or "").strip()
    if not value:
        return {"text": "", "translation": None, "note": None, "tags": []}

    if value.startswith("{"):
        try:
            data = json.loads(value)
            if isinstance(data, dict):
                note = data.get("note")
                tags = data.get("tags") or []
                legacy_translation = str(data.get("translation") or "").strip()
                legacy_text = str(data.get("text") or "").strip()
                if legacy_translation and legacy_text:
                    return {
                        "text": legacy_text,
                        "translation": legacy_translation,
                        "note": note,
                        "tags": tags,
                    }
                content = (
                    str(data.get("content") or "").strip()
                    or legacy_translation
                    or legacy_text
                )
                return {
                    "text": content,
                    "translation": None,
                    "note": note,
                    "tags": tags,
                }
        except json.JSONDecodeError:
            pass

    return {"text": value, "translation": None, "note": None, "tags": []}


_VIETNAMESE_CHARS = re.compile(
    r"[àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ]",
    re.IGNORECASE,
)


def _contains_vietnamese(text: str) -> bool:
    return bool(_VIETNAMESE_CHARS.search(text or ""))


def _contains_japanese(text: str) -> bool:
    for ch in text or "":
        if "\u3040" <= ch <= "\u30ff" or "\u4e00" <= ch <= "\u9fff":
            return True
    return False


def resolve_bilingual_pair(
    text: str,
    translation: str | None,
) -> tuple[str, str]:
    """Return (japanese, vietnamese) for translate history in VN UI."""
    primary = (text or "").strip()
    secondary = (translation or "").strip()

    if primary and secondary:
        if _contains_vietnamese(primary) and _contains_japanese(secondary):
            return secondary, primary
        if _contains_japanese(primary) and _contains_vietnamese(secondary):
            return primary, secondary
        if _contains_vietnamese(primary):
            return secondary, primary
        return primary, secondary

    if not primary:
        return "", ""

    if _contains_vietnamese(primary):
        japanese, _warning = translate_vietnamese_to_japanese(primary)
        return japanese.strip() or primary, primary

    vietnamese, _warning = translate_japanese_to_vietnamese(primary)
    return primary, vietnamese.strip()


def message_role(message: AnalysisMessage, index: int) -> str:
    if message.user_id:
        return "you"
    return "listen" if index % 2 == 0 else "you"


def format_message_time(created_at: datetime | None) -> str:
    if not created_at:
        return ""
    return created_at.strftime("%H:%M")


def build_reply_suggestions(logs: list[AnalysisLog]) -> list[ReplySuggestionItem]:
    output_text = get_latest_log_text(logs, "REPLY_SUGGESTION")
    parsed = parse_json_value(output_text)
    suggestions: list[ReplySuggestionItem] = []

    if isinstance(parsed, list):
        for index, item in enumerate(parsed):
            text = str(item)
            suggestions.append(
                ReplySuggestionItem(
                    id=f"s{index + 1}",
                    title=text[:80],
                    description=text,
                )
            )
    elif output_text:
        suggestions.append(
            ReplySuggestionItem(id="s1", title=output_text[:80], description=output_text)
        )

    return suggestions


def build_reply_suggestions_from_messages(
    messages: list[AnalysisMessage],
) -> list[ReplySuggestionItem]:
    transcript = "\n".join((message.text or "").strip() for message in messages if message.text)
    if not transcript.strip():
        return []
    try:
        history_path = Path(SUGGEST_HISTORY_FILE)
        history_path.parent.mkdir(parents=True, exist_ok=True)
        history_path.write_text(transcript, encoding="utf-8")
        analyzed = analyze_and_suggest_chat(history_path)
    except Exception:
        return []

    suggestions = analyzed.get("suggestions")
    if not isinstance(suggestions, list):
        return []

    items: list[ReplySuggestionItem] = []
    for index, item in enumerate(suggestions):
        if not isinstance(item, dict):
            continue
        jp = str(item.get("japanese") or "").strip()
        meaning = str(item.get("vietnamese_meaning") or "").strip()
        nuance = str(item.get("nuance") or "").strip()
        style = str(item.get("style") or "").strip()
        if not jp:
            continue
        desc_parts = [part for part in (meaning, style, nuance) if part]
        items.append(
            ReplySuggestionItem(
                id=f"s{index + 1}",
                title=jp[:80],
                description=" | ".join(desc_parts) if desc_parts else jp,
            )
        )
    return items


def build_dashboard_insights(
    perception_gaps: list[dict[str, Any]],
) -> list[DashboardInsightItem]:
    icon_map = {
        "CAO": ("report_problem", "bg-rose-50 text-rose-600"),
        "TRUNG BÌNH": ("warning_amber", "bg-amber-50 text-amber-600"),
        "THẤP": ("auto_fix_high", "bg-emerald-50 text-emerald-600"),
    }
    insights: list[DashboardInsightItem] = []

    for gap in perception_gaps[:3]:
        severity = str(gap.get("severity", "THẤP"))
        icon, status_classes = icon_map.get(severity, icon_map["THẤP"])
        insights.append(
            DashboardInsightItem(
                icon=icon,
                title=str(gap.get("title", "Phân tích AI")),
                description=str(
                    gap.get("recommendation")
                    or gap.get("left_text")
                    or gap.get("right_text")
                    or ""
                ),
                link_label="Xem chi tiết",
                status_label=severity,
                status_classes=status_classes,
            )
        )

    return insights


@router.get("/conversations", response_model=list[ConversationListItem])
def list_conversations(
    limit: int = Query(default=30, ge=1, le=100),
) -> list[ConversationListItem]:
    with Session(engine) as session:
        conversations = session.exec(
            select(AnalysisConversation)
            .order_by(AnalysisConversation.created_at.desc())
            .limit(limit)
        ).all()

        return [
            ConversationListItem(
                id=conversation.conversation_id,
                label=conversation.conversation_name,
                subtitle=conversation.created_at.strftime("%d/%m/%Y")
                if conversation.created_at
                else None,
            )
            for conversation in conversations
            if conversation.conversation_id is not None
        ]


@router.post("/conversations", response_model=ConversationListItem)
def create_conversation(
    name: str = Query(default="Hội thoại mới"),
) -> ConversationListItem:
    from src.models.models import User

    with Session(engine) as session:
        user_id = 4

        conversation = AnalysisConversation(
            user_id=user_id,
            conversation_name=name.strip() or "Hội thoại mới",
            created_at=datetime.utcnow(),
        )
        session.add(conversation)
        session.commit()
        session.refresh(conversation)

        if conversation.conversation_id is None:
            raise HTTPException(status_code=500, detail="Could not create conversation")

        return ConversationListItem(
            id=conversation.conversation_id,
            label=conversation.conversation_name,
            subtitle=conversation.created_at.strftime("%d/%m/%Y")
            if conversation.created_at
            else None,
        )


@router.patch("/conversations/{conversation_id}", response_model=ConversationListItem)
def update_conversation(
    conversation_id: int,
    body: ConversationUpdateRequest,
) -> ConversationListItem:
    with Session(engine) as session:
        conversation = get_conversation_or_404(session, conversation_id)
        conversation.conversation_name = body.name.strip()
        session.add(conversation)
        session.commit()
        session.refresh(conversation)

        return ConversationListItem(
            id=conversation.conversation_id,
            label=conversation.conversation_name,
            subtitle=conversation.created_at.strftime("%d/%m/%Y")
            if conversation.created_at
            else None,
        )


@router.get("/overview", response_model=DashboardOverviewResponse)
async def get_dashboard_overview(
    lang: str = Query(default="vn", pattern="^(vn|jp)$"),
) -> DashboardOverviewResponse:
    with Session(engine) as session:
        conversations = session.exec(select(AnalysisConversation)).all()
        total = len(conversations)

    try:
        analysis = await ensure_latest_analysis(lang)
    except HTTPException:
        return DashboardOverviewResponse(
            total_conversations=total,
            understanding_score=0,
            suggestions_count=0,
            interaction_time="0h",
            latest_analysis_id=None,
            insights=[],
        )

    duration = analysis.duration_minutes or 0
    hours = duration // 60
    minutes = duration % 60
    interaction_time = f"{hours}h" if hours else f"{minutes}m"

    return DashboardOverviewResponse(
        total_conversations=total,
        understanding_score=analysis.understanding_score,
        suggestions_count=len(analysis.action_items),
        interaction_time=interaction_time,
        latest_analysis_id=analysis.id,
        insights=build_dashboard_insights(analysis.perception_gaps),
    )


@router.get("/{conversation_id}/translate-context", response_model=TranslateContextResponse)
async def get_translate_context(
    conversation_id: int,
    lang: str = Query(default="vn", pattern="^(vn|jp)$"),
) -> TranslateContextResponse:
    with Session(engine) as session:
        conversation = get_conversation_or_404(session, conversation_id)
        messages = get_messages_by_conversation(session, conversation_id)
        logs = get_ai_logs_by_conversation(session, conversation_id)

    intent = get_latest_log_text(logs, "INTENT_ANALYSIS") or ""
    nuance = get_latest_log_text(logs, "NUANCE_ANALYSIS") or ""
    culture = get_latest_log_text(logs, "CULTURE_EXPLANATION") or ""

    if lang == "jp" and (intent or nuance or culture):
        analysis = await ensure_analysis_exists(conversation_id)
        localized = await localize_analysis_response(analysis, lang)
        gaps = localized.perception_gaps
        if gaps:
            culture = str(gaps[0].get("recommendation", culture)) if gaps else culture

    ui_messages = []
    for index, message in enumerate(messages):
        unpacked = unpack_message_text(message.text)
        display_text = unpacked["text"]
        display_translation = unpacked.get("translation")
        if lang == "vn":
            display_text, display_translation = resolve_bilingual_pair(
                display_text,
                display_translation,
            )
        ui_messages.append(
            TranslateMessageItem(
                id=message.message_id or index,
                role=message_role(message, index),
                text=display_text,
                translation=display_translation or None,
                note=unpacked.get("note"),
                tags=unpacked.get("tags") or [],
                time=format_message_time(message.created_at),
                is_marked=int(message.is_marked or 0),
            )
        )

    listen_items = [item for item in ui_messages if item.role == "listen"]
    last_listen = listen_items[-1] if listen_items else None
    partner_text = last_listen.text if last_listen else ""
    translation_text = ""
    for item in reversed(ui_messages):
        translated = (item.translation or "").strip()
        if translated:
            translation_text = translated
            break

    reply_suggestions = build_reply_suggestions(logs)
    if not reply_suggestions:
        reply_suggestions = build_reply_suggestions_from_messages(messages)

    return TranslateContextResponse(
        conversation_id=conversation_id,
        conversation_name=conversation.conversation_name,
        messages=ui_messages,
        intent_analysis=intent,
        nuance_analysis=nuance,
        culture_explanation=culture,
        reply_suggestions=reply_suggestions,
        partner_text=partner_text,
        translation_text=translation_text,
    )


@router.post("/{conversation_id}/messages", response_model=TranslateMessageItem)
def add_conversation_message(
    conversation_id: int,
    body: MessageCreateRequest,
) -> TranslateMessageItem:
    with Session(engine) as session:
        get_conversation_or_404(session, conversation_id)
        user_id = 4 if body.role == "you" else None

        stored_text = body.text.strip()
        message = AnalysisMessage(
            conversation_id=conversation_id,
            user_id=user_id,
            text=stored_text,
            created_at=datetime.utcnow(),
        )
        session.add(message)
        session.commit()
        session.refresh(message)

        if message.message_id is None:
            raise HTTPException(status_code=500, detail="Could not save message")

        return TranslateMessageItem(
            id=message.message_id,
            role=body.role,
            text=body.text.strip(),
            translation=body.translation,
            note=body.note,
            tags=body.tags,
            time=format_message_time(message.created_at),
            is_marked=int(message.is_marked or 0),
        )


@router.patch("/messages/{message_id}/mark", response_model=MarkMessageResponse)
def mark_conversation_message(message_id: int) -> MarkMessageResponse:
    """Marks a message as important (is_marked=1)."""
    with Session(engine) as session:
        message = message_repo.mark_message(session, message_id=message_id)
    if message.message_id is None:
        raise HTTPException(status_code=500, detail="Could not mark message")
    return MarkMessageResponse(
        id=message.message_id,
        is_marked=int(message.is_marked or 0),
    )


@router.get("/{conversation_id}/ensure", response_model=AnalysisResponse)
async def ensure_analysis_by_id(
    conversation_id: int,
    lang: str = Query(default="vn", pattern="^(vn|jp)$"),
) -> AnalysisResponse:
    analysis = await ensure_analysis_exists(conversation_id)
    return await localize_analysis_response(analysis, lang)


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


@router.get("/latest/export-pdf")
async def export_latest_analysis_pdf(
    lang: str = Query(default="vn", pattern="^(vn|jp)$"),
) -> FileResponse:
    with Session(engine) as session:
        conversation = get_latest_displayable_conversation(session)

        if not conversation or conversation.conversation_id is None:
            raise HTTPException(status_code=404, detail="No conversation found")

        conversation_id = conversation.conversation_id

    analysis = await ensure_analysis_exists(conversation_id)
    analysis = await localize_analysis_response(analysis, lang)
    file_path = build_analysis_pdf(analysis, lang)

    return FileResponse(
        path=str(file_path),
        media_type="application/pdf",
        filename=(
            f"analysis_report_{analysis.id}.pdf"
            if lang == "jp"
            else f"bao_cao_phan_tich_{analysis.id}.pdf"
        ),
    )


@router.get("/export-pdf")
async def export_current_analysis_pdf(
    lang: str = Query(default="vn", pattern="^(vn|jp)$"),
) -> FileResponse:
    return await export_latest_analysis_pdf(lang=lang)


@router.get("/{conversation_id}/export-pdf")
async def export_analysis_pdf(
    conversation_id: int,
    lang: str = Query(default="vn", pattern="^(vn|jp)$"),
) -> FileResponse:
    analysis = await ensure_analysis_exists(conversation_id)
    analysis = await localize_analysis_response(analysis, lang)
    file_path = build_analysis_pdf(analysis, lang)

    return FileResponse(
        path=str(file_path),
        media_type="application/pdf",
        filename=(
            f"analysis_report_{conversation_id}.pdf"
            if lang == "jp"
            else f"bao_cao_phan_tich_{conversation_id}.pdf"
        ),
    )


@router.get("/{conversation_id}", response_model=AnalysisResponse)
async def get_analysis_by_id(
    conversation_id: int,
    lang: str = Query(default="vn", pattern="^(vn|jp)$"),
) -> AnalysisResponse:
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

        analysis = build_analysis_from_db(
            conversation=conversation,
            messages=messages,
            logs=logs,
        )
        return await localize_analysis_response(analysis, lang)
