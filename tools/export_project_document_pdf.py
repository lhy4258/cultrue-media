from __future__ import annotations

import html
import re
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "docs" / "project-document.md"
OUTPUT = ROOT / "docs" / "project-document.pdf"

BODY_FONT = "NotoSansSC-Thin"
HEADING_FONT = "MicrosoftYaHei-Bold-0"
BODY_FONT_FILE = Path(r"C:\Windows\Fonts\NotoSansSC-VF.ttf")
HEADING_FONT_FILE = Path(r"C:\Windows\Fonts\msyhbd.ttc")


def register_fonts() -> None:
    pdfmetrics.registerFont(TTFont(BODY_FONT, str(BODY_FONT_FILE)))
    pdfmetrics.registerFont(TTFont(HEADING_FONT, str(HEADING_FONT_FILE), subfontIndex=0))


def clean_inline(text: str) -> str:
    escaped = html.escape(text)
    escaped = re.sub(r"`([^`]+)`", r"<font name='%s'>\1</font>" % BODY_FONT, escaped)
    return escaped


def make_styles() -> dict[str, ParagraphStyle]:
    return {
        "h1": ParagraphStyle(
            "Heading1",
            fontName=HEADING_FONT,
            fontSize=18,
            leading=25,
            spaceBefore=0,
            spaceAfter=12,
            alignment=TA_LEFT,
            wordWrap="CJK",
        ),
        "h2": ParagraphStyle(
            "Heading2",
            fontName=HEADING_FONT,
            fontSize=14,
            leading=21,
            spaceBefore=12,
            spaceAfter=7,
            wordWrap="CJK",
        ),
        "h3": ParagraphStyle(
            "Heading3",
            fontName=HEADING_FONT,
            fontSize=16,
            leading=23,
            spaceBefore=10,
            spaceAfter=6,
            wordWrap="CJK",
        ),
        "body": ParagraphStyle(
            "Body",
            fontName=BODY_FONT,
            fontSize=10.5,
            leading=17,
            spaceBefore=0,
            spaceAfter=5,
            wordWrap="CJK",
        ),
        "bullet": ParagraphStyle(
            "Bullet",
            fontName=BODY_FONT,
            fontSize=10.5,
            leading=17,
            leftIndent=14,
            firstLineIndent=-10,
            spaceAfter=3,
            wordWrap="CJK",
        ),
        "code": ParagraphStyle(
            "Code",
            fontName=BODY_FONT,
            fontSize=9.2,
            leading=13,
            leftIndent=6,
            rightIndent=6,
            spaceBefore=3,
            spaceAfter=6,
            wordWrap="CJK",
            backColor=colors.HexColor("#F5F7FA"),
            borderColor=colors.HexColor("#D9E1EC"),
            borderWidth=0.4,
            borderPadding=5,
        ),
        "table": ParagraphStyle(
            "TableText",
            fontName=BODY_FONT,
            fontSize=8.7,
            leading=12,
            wordWrap="CJK",
        ),
    }


def code_paragraph(lines: list[str], styles: dict[str, ParagraphStyle]) -> Paragraph:
    text = "<br/>".join(html.escape(line) if line else "&nbsp;" for line in lines)
    return Paragraph(text, styles["code"])


def markdown_table(lines: list[str], styles: dict[str, ParagraphStyle]) -> Table:
    rows: list[list[Paragraph]] = []
    for line in lines:
        stripped = line.strip()
        if not stripped or re.fullmatch(r"\|?[\s:\-\|]+\|?", stripped):
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        rows.append([Paragraph(clean_inline(cell), styles["table"]) for cell in cells])

    if not rows:
        return Table([[""]])

    available_width = A4[0] - 36 * mm
    col_count = max(len(row) for row in rows)
    col_widths = [available_width / col_count] * col_count
    table = Table(rows, colWidths=col_widths, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, -1), BODY_FONT),
                ("FONTSIZE", (0, 0), (-1, -1), 8.7),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EAF1FA")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#1F2937")),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#CAD5E1")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    return table


def parse_markdown(markdown: str, styles: dict[str, ParagraphStyle]) -> list:
    flowables: list = []
    lines = markdown.splitlines()
    i = 0

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        if not stripped:
            flowables.append(Spacer(1, 7))
            i += 1
            continue

        if stripped.startswith("```"):
            i += 1
            block: list[str] = []
            while i < len(lines) and not lines[i].strip().startswith("```"):
                block.append(lines[i])
                i += 1
            flowables.append(code_paragraph(block, styles))
            i += 1
            continue

        if stripped.startswith("|") and "|" in stripped[1:]:
            table_lines = [line]
            i += 1
            while i < len(lines) and lines[i].strip().startswith("|"):
                table_lines.append(lines[i])
                i += 1
            flowables.append(markdown_table(table_lines, styles))
            flowables.append(Spacer(1, 6))
            continue

        if stripped.startswith("# "):
            flowables.append(Paragraph(clean_inline(stripped[2:].strip()), styles["h1"]))
            i += 1
            continue

        if stripped.startswith("## "):
            title = Paragraph(clean_inline(stripped[3:].strip()), styles["h2"])
            flowables.append(KeepTogether([title]))
            i += 1
            continue

        if stripped.startswith("### "):
            flowables.append(Paragraph(clean_inline(stripped[4:].strip()), styles["h3"]))
            i += 1
            continue

        bullet_match = re.match(r"^[-*]\s+(.*)$", stripped)
        if bullet_match:
            flowables.append(
                Paragraph("- " + clean_inline(bullet_match.group(1)), styles["bullet"])
            )
            i += 1
            continue

        ordered_match = re.match(r"^(\d+)\.\s+(.*)$", stripped)
        if ordered_match:
            flowables.append(
                Paragraph(
                    f"{ordered_match.group(1)}. {clean_inline(ordered_match.group(2))}",
                    styles["bullet"],
                )
            )
            i += 1
            continue

        if stripped == "---":
            flowables.append(PageBreak())
            i += 1
            continue

        flowables.append(Paragraph(clean_inline(stripped), styles["body"]))
        i += 1

    return flowables


def footer(canvas, doc) -> None:
    canvas.saveState()
    canvas.setFont(BODY_FONT, 8.5)
    canvas.setFillColor(colors.HexColor("#6B7280"))
    canvas.drawString(18 * mm, 11 * mm, "AI 评价生成 Demo 最终交付文档")
    canvas.drawRightString(A4[0] - 18 * mm, 11 * mm, f"第 {doc.page} 页")
    canvas.restoreState()


def main() -> None:
    register_fonts()
    markdown = SOURCE.read_text(encoding="utf-8")
    styles = make_styles()
    flowables = parse_markdown(markdown, styles)

    document = SimpleDocTemplate(
        str(OUTPUT),
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
        title="AI 评价生成 Demo 最终交付文档",
        author="Codex",
    )
    document.build(flowables, onFirstPage=footer, onLaterPages=footer)
    print(OUTPUT)


if __name__ == "__main__":
    main()
