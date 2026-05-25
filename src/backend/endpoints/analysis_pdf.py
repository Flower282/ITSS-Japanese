from __future__ import annotations

import tempfile
import uuid
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


PDF_LABELS = {
    "vn": {
        "report_title": "Báo cáo phân tích hội thoại",
        "meeting_date": "Ngày họp",
        "no_data": "Không có dữ liệu",
        "duration": "Thời lượng",
        "minutes": "phút",
        "understanding": "Độ hiểu",
        "sentiment": "Cảm xúc chung",
        "feedback": "Nhận xét tổng quan từ AI",
        "metrics": "Chỉ số phân tích",
        "metric_name": "Chỉ số",
        "metric_value": "Giá trị",
        "metric_desc": "Mô tả",
        "gaps": "Điểm lệch nhận thức",
        "no_gaps": "Chưa phát hiện điểm lệch nhận thức nào.",
        "untitled_gap": "Vấn đề chưa đặt tên",
        "recommendation": "Khuyến nghị AI",
        "summary": "Tóm tắt nội dung / Quyết định chính",
        "action_items": "Action items",
    },
    "jp": {
        "report_title": "会話分析レポート",
        "meeting_date": "会議日",
        "no_data": "データなし",
        "duration": "時間",
        "minutes": "分",
        "understanding": "理解度",
        "sentiment": "全体の感情",
        "feedback": "AIからの総合フィードバック",
        "metrics": "分析指標",
        "metric_name": "指標",
        "metric_value": "値",
        "metric_desc": "説明",
        "gaps": "認識のギャップ",
        "no_gaps": "認識のギャップは検出されませんでした。",
        "untitled_gap": "未設定の課題",
        "recommendation": "AIの推奨",
        "summary": "内容のまとめ / 主な決定事項",
        "action_items": "アクションアイテム",
    },
}


def register_pdf_font(lang: str = "vn") -> str:
    if lang == "jp":
        font_name = "HeiseiKakuGo-W5"

        try:
            pdfmetrics.getFont(font_name)
            return font_name
        except Exception:
            try:
                pdfmetrics.registerFont(UnicodeCIDFont(font_name))
                return font_name
            except Exception:
                pass

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


def build_analysis_pdf(analysis, lang: str = "vn") -> Path:
    font_name = register_pdf_font(lang)
    labels = PDF_LABELS.get(lang, PDF_LABELS["vn"])

    reports_dir = Path(tempfile.gettempdir()) / "truetalk_reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    file_path = reports_dir / f"analysis_report_{analysis.id}_{uuid.uuid4().hex[:8]}.pdf"

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

    story = [
        pdf_paragraph(labels["report_title"], title_style),
        pdf_paragraph(analysis.meeting_title, heading_style),
    ]

    info_data = [
        [pdf_paragraph(labels["meeting_date"], small_style), pdf_paragraph(analysis.meeting_date or labels["no_data"], normal_style)],
        [pdf_paragraph(labels["duration"], small_style), pdf_paragraph(f"{analysis.duration_minutes or 0} {labels['minutes']}", normal_style)],
        [pdf_paragraph(labels["understanding"], small_style), pdf_paragraph(f"{analysis.understanding_score}%", normal_style)],
        [pdf_paragraph(labels["sentiment"], small_style), pdf_paragraph(analysis.overall_sentiment, normal_style)],
    ]

    info_table = Table(info_data, colWidths=[4 * cm, 12 * cm])
    info_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#F1F5F9")),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))
    story.extend([info_table, Spacer(1, 10)])

    story.extend([
        pdf_paragraph(labels["feedback"], heading_style),
        pdf_paragraph(analysis.ai_overall_feedback, normal_style),
        pdf_paragraph(labels["metrics"], heading_style),
    ])

    metrics_data = [[
        pdf_paragraph(labels["metric_name"], small_style),
        pdf_paragraph(labels["metric_value"], small_style),
        pdf_paragraph(labels["metric_desc"], small_style),
    ]]
    for metric in analysis.metrics:
        metrics_data.append([
            pdf_paragraph(metric.get("title", ""), normal_style),
            pdf_paragraph(metric.get("value", ""), normal_style),
            pdf_paragraph(metric.get("subtitle", ""), normal_style),
        ])

    metrics_table = Table(metrics_data, colWidths=[5 * cm, 4 * cm, 7 * cm])
    metrics_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#DBEAFE")),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))
    story.extend([metrics_table, Spacer(1, 10)])

    story.append(pdf_paragraph(labels["gaps"], heading_style))
    if not analysis.perception_gaps:
        story.append(pdf_paragraph(labels["no_gaps"], normal_style))

    for index, gap in enumerate(analysis.perception_gaps, start=1):
        story.append(
            pdf_paragraph(
                f"{index}. {gap.get('title', labels['untitled_gap'])} - {gap.get('severity', '')}",
                normal_style,
            )
        )
        gap_table = Table([
            [pdf_paragraph(gap.get("left_title", ""), small_style), pdf_paragraph(gap.get("left_text", ""), normal_style)],
            [pdf_paragraph(gap.get("right_title", ""), small_style), pdf_paragraph(gap.get("right_text", ""), normal_style)],
            [pdf_paragraph(labels["recommendation"], small_style), pdf_paragraph(gap.get("recommendation", ""), normal_style)],
        ], colWidths=[4 * cm, 12 * cm])
        gap_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#FEF3C7")),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 7),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ]))
        story.extend([gap_table, Spacer(1, 8)])

    story.append(pdf_paragraph(labels["summary"], heading_style))
    for index, decision in enumerate(analysis.decisions, start=1):
        story.append(pdf_paragraph(f"{index}. {decision}", normal_style))

    story.append(pdf_paragraph(labels["action_items"], heading_style))
    for index, item in enumerate(analysis.action_items, start=1):
        story.append(pdf_paragraph(f"{index}. {item}", normal_style))

    doc.build(story)
    return file_path
