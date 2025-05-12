from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    ListItem,
    ListFlowable,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
import re
from reportlab.lib.pagesizes import letter


def export_to_pdf(text, output_path):
    """Convert markdown-formatted text to a PDF file.

    Supports:
    - Headers (# H1, ## H2, ### H3)
    - Bold (**text**)
    - Italic (*text*)
    - Lists (- item or * item)
    """
    doc = SimpleDocTemplate(output_path, pagesize=letter)
    styles = getSampleStyleSheet()

    if "Title" not in styles:
        styles.add(
            ParagraphStyle(name="Title", parent=styles["Heading1"], alignment=TA_CENTER)
        )
    if "Heading2" not in styles:
        styles.add(ParagraphStyle(name="Heading2", parent=styles["Heading2"]))
    if "Heading3" not in styles:
        styles.add(ParagraphStyle(name="Heading3", parent=styles["Heading3"]))

    normal_style = ParagraphStyle(
        name="CustomNormal", parent=styles["Normal"], alignment=TA_JUSTIFY
    )

    content = []
    bullets = []
    in_list = False

    for line in text.split("\n"):
        if not line.strip():
            if in_list and bullets:
                content.append(ListFlowable(bullets, bulletType="bullet"))
                bullets = []
                in_list = False
            content.append(Spacer(1, 6))
            continue

        if line.startswith("# "):
            if in_list and bullets:
                content.append(ListFlowable(bullets, bulletType="bullet"))
                bullets = []
                in_list = False
            content.append(Paragraph(line[2:], styles["Title"]))
        elif line.startswith("## "):
            if in_list and bullets:
                content.append(ListFlowable(bullets, bulletType="bullet"))
                bullets = []
                in_list = False
            content.append(Paragraph(line[3:], styles["Heading2"]))
        elif line.startswith("### "):
            if in_list and bullets:
                content.append(ListFlowable(bullets, bulletType="bullet"))
                bullets = []
                in_list = False
            content.append(Paragraph(line[4:], styles["Heading3"]))
        elif line.strip().startswith(("- ", "* ")):
            in_list = True
            text = line.strip()[2:]
            text = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", text)
            text = re.sub(r"\*(.*?)\*", r"<i>\1</i>", text)
            bullets.append(ListItem(Paragraph(text, normal_style)))
        else:
            if in_list and bullets:
                content.append(ListFlowable(bullets, bulletType="bullet"))
                bullets = []
                in_list = False

            text = line
            text = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", text)
            text = re.sub(r"\*(.*?)\*", r"<i>\1</i>", text)
            content.append(Paragraph(text, normal_style))

    if bullets:
        content.append(ListFlowable(bullets, bulletType="bullet"))

    doc.build(content)
    return output_path
