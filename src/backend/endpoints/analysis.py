from __future__ import annotations

import json
import os
import re
import tempfile
import uuid
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape

import httpx
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlmodel import Session, select

from src.db.session import engine
from src.models.analysis_models import ConversationAnalysis


router = APIRouter(prefix="/analysis", tags=["analysis"])


class AnalysisCreateRequest(BaseModel):
    meeting_title: str = Field(default="Cuộc họp chưa đặt tên")
    meeting_date: str | None = None
    duration_minutes: int | None = None
    transcript: str


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


class AnalysisSearchItem(BaseModel):
    id: int
    meeting_title: str
    meeting_date: str | None = None
    duration_minutes: int | None = None
    understanding_score: int
    overall_sentiment: str
    ai_overall_feedback: str


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


def normalize_sentiment(sentiment: str | None) -> str:
    if not sentiment:
        return "Trung bình"

    sentiment = sentiment.strip()

    if sentiment not in {"Tốt", "Trung bình", "Căng thẳng"}:
        return "Trung bình"

    return sentiment


def build_metrics(
    duration: int | None,
    understanding_score: int,
    sentiment: str,
) -> list[dict[str, Any]]:
    return [
        {
            "title": "THỜI LƯỢNG",
            "value": str(duration or 0),
            "subtitle": "Phút tương tác",
            "accent_classes": "border-blue-100 bg-blue-50",
            "value_classes": "text-blue-600",
        },
        {
            "title": "ĐỘ HIỂU",
            "value": f"{understanding_score}%",
            "subtitle": "Truyền đạt chính xác",
            "accent_classes": "border-emerald-100 bg-emerald-50",
            "value_classes": "text-emerald-600",
        },
        {
            "title": "CẢM XÚC CHUNG",
            "value": sentiment,
            "subtitle": "Tích cực & Xây dựng"
            if sentiment == "Tốt"
            else "Cần theo dõi thêm",
            "accent_classes": "border-purple-100 bg-purple-50",
            "value_classes": "text-purple-600",
        },
    ]


def build_ui_payload(
    ai_data: dict[str, Any],
    payload: AnalysisCreateRequest,
) -> dict[str, Any]:
    duration = ai_data.get("duration_minutes") or payload.duration_minutes or 0

    understanding_score = int(ai_data.get("understanding_score") or 0)
    understanding_score = max(0, min(100, understanding_score))

    sentiment = normalize_sentiment(ai_data.get("overall_sentiment"))

    raw_gaps = ai_data.get("perception_gaps") or []
    perception_gaps: list[dict[str, Any]] = []

    for gap in raw_gaps:
        severity = str(gap.get("severity", "THẤP")).upper()

        if severity not in {"THẤP", "TRUNG BÌNH", "CAO"}:
            severity = "THẤP"

        perception_gaps.append(
            {
                "title": gap.get("title", "Vấn đề chưa đặt tên"),
                "severity": severity,
                "severity_classes": get_severity_classes(severity),
                "card_classes": get_gap_card_classes(severity),
                "left_title": "VN QUAN ĐIỂM VIỆT NAM",
                "left_text": gap.get("vn_view", ""),
                "right_title": "JP QUAN ĐIỂM NHẬT BẢN",
                "right_text": gap.get("jp_view", ""),
                "recommendation": gap.get("recommendation", ""),
            }
        )

    return {
        "meeting_title": ai_data.get("meeting_title") or payload.meeting_title,
        "meeting_date": ai_data.get("meeting_date") or payload.meeting_date,
        "duration_minutes": duration,
        "understanding_score": understanding_score,
        "overall_sentiment": sentiment,
        "ai_overall_feedback": ai_data.get("ai_overall_feedback", ""),
        "metrics": build_metrics(duration, understanding_score, sentiment),
        "perception_gaps": perception_gaps,
        "decisions": ai_data.get("decisions") or [],
        "action_items": ai_data.get("action_items") or [],
    }


async def analyze_with_groq(payload: AnalysisCreateRequest) -> dict[str, Any]:
    api_key = os.getenv("GROQ_API_KEY")

    if not api_key:
        raise HTTPException(status_code=500, detail="Missing GROQ_API_KEY in .env")

    prompt = f"""
Bạn là AI phân tích hội thoại trong môi trường làm việc Việt Nam - Nhật Bản.

Hãy phân tích transcript dưới đây và trả về DUY NHẤT JSON hợp lệ.
Không dùng markdown. Không giải thích ngoài JSON.

Thông tin cuộc họp:
- Tên cuộc họp: {payload.meeting_title}
- Ngày họp: {payload.meeting_date}
- Thời lượng phút: {payload.duration_minutes}

Transcript:
{payload.transcript}

JSON bắt buộc có cấu trúc:
{{
  "meeting_title": "string",
  "meeting_date": "string hoặc null",
  "duration_minutes": number,
  "understanding_score": number từ 0 đến 100,
  "overall_sentiment": "Tốt hoặc Trung bình hoặc Căng thẳng",
  "ai_overall_feedback": "Nhận xét tổng quan bằng tiếng Việt",
  "perception_gaps": [
    {{
      "title": "Tên vấn đề",
      "severity": "THẤP hoặc TRUNG BÌNH hoặc CAO",
      "vn_view": "Cách hiểu của phía Việt Nam",
      "jp_view": "Cách hiểu của phía Nhật Bản",
      "recommendation": "Khuyến nghị xử lý"
    }}
  ],
  "decisions": ["Quyết định chính 1"],
  "action_items": ["Người phụ trách: việc cần làm"]
}}
"""

    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": os.getenv("GROQ_MODEL", "llama-3.1-8b-instant"),
                "messages": [
                    {
                        "role": "system",
                        "content": "Bạn là AI chuyên phân tích khác biệt giao tiếp Việt Nam - Nhật Bản.",
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


def to_response(row: ConversationAnalysis) -> AnalysisResponse:
    if row.id is None:
        raise HTTPException(status_code=500, detail="Analysis row has no id")

    return AnalysisResponse(
        id=row.id,
        meeting_title=row.meeting_title,
        meeting_date=row.meeting_date,
        duration_minutes=row.duration_minutes,
        understanding_score=row.understanding_score,
        overall_sentiment=row.overall_sentiment,
        ai_overall_feedback=row.ai_overall_feedback,
        metrics=row.metrics
        or build_metrics(
            row.duration_minutes,
            row.understanding_score,
            row.overall_sentiment,
        ),
        perception_gaps=row.perception_gaps or [],
        decisions=row.decisions or [],
        action_items=row.action_items or [],
    )


def to_search_item(row: ConversationAnalysis) -> AnalysisSearchItem:
    if row.id is None:
        raise HTTPException(status_code=500, detail="Analysis row has no id")

    return AnalysisSearchItem(
        id=row.id,
        meeting_title=row.meeting_title,
        meeting_date=row.meeting_date,
        duration_minutes=row.duration_minutes,
        understanding_score=row.understanding_score,
        overall_sentiment=row.overall_sentiment,
        ai_overall_feedback=row.ai_overall_feedback,
    )


def analysis_to_search_text(row: ConversationAnalysis) -> str:
    payload = {
        "meeting_title": row.meeting_title,
        "meeting_date": row.meeting_date,
        "duration_minutes": row.duration_minutes,
        "transcript": row.transcript,
        "understanding_score": row.understanding_score,
        "overall_sentiment": row.overall_sentiment,
        "ai_overall_feedback": row.ai_overall_feedback,
        "metrics": row.metrics,
        "perception_gaps": row.perception_gaps,
        "decisions": row.decisions,
        "action_items": row.action_items,
    }

    return json.dumps(payload, ensure_ascii=False).lower()


def get_analysis_row_or_404(
    session: Session,
    analysis_id: int,
) -> ConversationAnalysis:
    row = session.get(ConversationAnalysis, analysis_id)

    if not row:
        raise HTTPException(status_code=404, detail="Analysis result not found")

    return row


@router.post("/run", response_model=AnalysisResponse)
async def run_analysis(payload: AnalysisCreateRequest) -> AnalysisResponse:
    if not payload.transcript.strip():
        raise HTTPException(status_code=400, detail="Transcript is required")

    ai_data = await analyze_with_groq(payload)
    ui_payload = build_ui_payload(ai_data, payload)

    row = ConversationAnalysis(
        meeting_title=ui_payload["meeting_title"],
        meeting_date=ui_payload["meeting_date"],
        duration_minutes=ui_payload["duration_minutes"],
        transcript=payload.transcript,
        understanding_score=ui_payload["understanding_score"],
        overall_sentiment=ui_payload["overall_sentiment"],
        ai_overall_feedback=ui_payload["ai_overall_feedback"],
        metrics=ui_payload["metrics"],
        perception_gaps=ui_payload["perception_gaps"],
        decisions=ui_payload["decisions"],
        action_items=ui_payload["action_items"],
    )

    with Session(engine) as session:
        session.add(row)
        session.commit()
        session.refresh(row)

    return to_response(row)


@router.get("/latest", response_model=AnalysisResponse)
def get_latest_analysis() -> AnalysisResponse:
    with Session(engine) as session:
        statement = (
            select(ConversationAnalysis)
            .order_by(ConversationAnalysis.created_at.desc())
            .limit(1)
        )
        row = session.exec(statement).first()

        if not row:
            raise HTTPException(status_code=404, detail="No analysis result found")

        return to_response(row)


@router.get("/search", response_model=list[AnalysisSearchItem])
def search_analyses(
    q: str = Query(..., min_length=1),
    limit: int = Query(default=10, ge=1, le=50),
) -> list[AnalysisSearchItem]:
    keyword = q.strip().lower()

    if not keyword:
        return []

    with Session(engine) as session:
        statement = (
            select(ConversationAnalysis)
            .order_by(ConversationAnalysis.created_at.desc())
            .limit(200)
        )
        rows = session.exec(statement).all()

        matched_rows = [
            row for row in rows if keyword in analysis_to_search_text(row)
        ]

        return [to_search_item(row) for row in matched_rows[:limit]]


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


def build_analysis_pdf(row: ConversationAnalysis) -> Path:
    font_name = register_pdf_font()

    reports_dir = Path(tempfile.gettempdir()) / "truetalk_reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    file_path = reports_dir / f"analysis_report_{row.id}_{uuid.uuid4().hex[:8]}.pdf"

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
    story.append(pdf_paragraph(row.meeting_title, heading_style))

    info_data = [
        [
            pdf_paragraph("Ngày họp", small_style),
            pdf_paragraph(row.meeting_date or "Không có dữ liệu", normal_style),
        ],
        [
            pdf_paragraph("Thời lượng", small_style),
            pdf_paragraph(f"{row.duration_minutes or 0} phút", normal_style),
        ],
        [
            pdf_paragraph("Độ hiểu", small_style),
            pdf_paragraph(f"{row.understanding_score}%", normal_style),
        ],
        [
            pdf_paragraph("Cảm xúc chung", small_style),
            pdf_paragraph(row.overall_sentiment, normal_style),
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
    story.append(pdf_paragraph(row.ai_overall_feedback, normal_style))

    story.append(pdf_paragraph("Chỉ số phân tích", heading_style))

    metric_rows = [
        [
            pdf_paragraph("Chỉ số", small_style),
            pdf_paragraph("Giá trị", small_style),
            pdf_paragraph("Mô tả", small_style),
        ]
    ]

    for metric in row.metrics or []:
        metric_rows.append(
            [
                pdf_paragraph(metric.get("title", ""), normal_style),
                pdf_paragraph(metric.get("value", ""), normal_style),
                pdf_paragraph(metric.get("subtitle", ""), normal_style),
            ]
        )

    metrics_table = Table(metric_rows, colWidths=[5 * cm, 4 * cm, 7 * cm])
    metrics_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#DBEAFE")),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 7),
                ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )

    story.append(metrics_table)

    story.append(pdf_paragraph("Điểm lệch nhận thức", heading_style))

    if not row.perception_gaps:
        story.append(
            pdf_paragraph("Chưa phát hiện điểm lệch nhận thức nào.", normal_style)
        )

    for index, gap in enumerate(row.perception_gaps or [], start=1):
        story.append(
            pdf_paragraph(
                f"{index}. {gap.get('title', 'Vấn đề chưa đặt tên')} - {gap.get('severity', '')}",
                normal_style,
            )
        )

        gap_table = Table(
            [
                [
                    pdf_paragraph("Quan điểm Việt Nam", small_style),
                    pdf_paragraph(
                        gap.get("left_text") or gap.get("vn_view") or "",
                        normal_style,
                    ),
                ],
                [
                    pdf_paragraph("Quan điểm Nhật Bản", small_style),
                    pdf_paragraph(
                        gap.get("right_text") or gap.get("jp_view") or "",
                        normal_style,
                    ),
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
                    ("LEFTPADDING", (0, 0), (-1, -1), 7),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                    ("TOPPADDING", (0, 0), (-1, -1), 7),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                ]
            )
        )

        story.append(gap_table)
        story.append(Spacer(1, 8))

    story.append(pdf_paragraph("Tóm tắt nội dung / Quyết định chính", heading_style))

    if row.decisions:
        for index, decision in enumerate(row.decisions, start=1):
            story.append(pdf_paragraph(f"{index}. {decision}", normal_style))
    else:
        story.append(pdf_paragraph("Chưa phát hiện quyết định chính nào.", normal_style))

    story.append(pdf_paragraph("Action items", heading_style))

    if row.action_items:
        for index, item in enumerate(row.action_items, start=1):
            story.append(pdf_paragraph(f"{index}. {item}", normal_style))
    else:
        story.append(pdf_paragraph("Chưa có action items.", normal_style))

    doc.build(story)
    return file_path


@router.get("/latest/export-pdf")
def export_latest_analysis_pdf() -> FileResponse:
    with Session(engine) as session:
        statement = (
            select(ConversationAnalysis)
            .order_by(ConversationAnalysis.created_at.desc())
            .limit(1)
        )
        row = session.exec(statement).first()

        if not row:
            raise HTTPException(status_code=404, detail="No analysis result found")

        file_path = build_analysis_pdf(row)

        return FileResponse(
            path=str(file_path),
            media_type="application/pdf",
            filename=f"bao_cao_phan_tich_{row.id}.pdf",
        )


@router.get("/{analysis_id}/export-pdf")
def export_analysis_pdf(analysis_id: int) -> FileResponse:
    with Session(engine) as session:
        row = get_analysis_row_or_404(session, analysis_id)
        file_path = build_analysis_pdf(row)

        return FileResponse(
            path=str(file_path),
            media_type="application/pdf",
            filename=f"bao_cao_phan_tich_{analysis_id}.pdf",
        )


@router.get("/{analysis_id}", response_model=AnalysisResponse)
def get_analysis_by_id(analysis_id: int) -> AnalysisResponse:
    with Session(engine) as session:
        row = get_analysis_row_or_404(session, analysis_id)
        return to_response(row)
