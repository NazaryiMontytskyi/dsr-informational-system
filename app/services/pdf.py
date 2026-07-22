"""
Генерація PDF-подання наказів і Положення про гурток.

Побудовано напряму через reportlab (чистий Python, без зовнішніх програм
на кшталт LibreOffice/MS Word) -- це робить генерацію документів
незалежною від софта, встановленого на сервері розгортання.

Шрифт -- Liberation Serif: метрично сумісний вільний аналог Times New
Roman (той самий шрифт, яким оформлені офіційні зразки наказів), тому
вигляд документа зберігається однаковим незалежно від того, чи є на
сервері власне Times New Roman.
"""

from __future__ import annotations

from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.core.config import BASE_DIR
from app.services.orders import OrderDocument

FONTS_DIR = BASE_DIR / "app" / "static" / "fonts"
FONT_NAME = "LiberationSerif"

_fonts_registered = False


def _register_fonts() -> None:
    global _fonts_registered
    if _fonts_registered:
        return
    pdfmetrics.registerFont(TTFont(FONT_NAME, str(FONTS_DIR / "LiberationSerif-Regular.ttf")))
    pdfmetrics.registerFont(TTFont(f"{FONT_NAME}-Bold", str(FONTS_DIR / "LiberationSerif-Bold.ttf")))
    pdfmetrics.registerFont(TTFont(f"{FONT_NAME}-Italic", str(FONTS_DIR / "LiberationSerif-Italic.ttf")))
    pdfmetrics.registerFont(TTFont(f"{FONT_NAME}-BoldItalic", str(FONTS_DIR / "LiberationSerif-BoldItalic.ttf")))
    pdfmetrics.registerFontFamily(
        FONT_NAME,
        normal=FONT_NAME,
        bold=f"{FONT_NAME}-Bold",
        italic=f"{FONT_NAME}-Italic",
        boldItalic=f"{FONT_NAME}-BoldItalic",
    )
    _fonts_registered = True


def _styles() -> dict[str, ParagraphStyle]:
    _register_fonts()
    base = dict(fontSize=13, leading=17)
    return {
        "header": ParagraphStyle("header", **base, alignment=TA_CENTER, fontName=f"{FONT_NAME}-Bold"),
        "naked_title": ParagraphStyle(
            "naked_title", **base, alignment=TA_CENTER, fontName=f"{FONT_NAME}-Bold", spaceBefore=6, spaceAfter=6
        ),
        "plain": ParagraphStyle("plain", **base, fontName=FONT_NAME, alignment=TA_JUSTIFY),
        "bold_center": ParagraphStyle("bold_center", **base, alignment=TA_CENTER, fontName=f"{FONT_NAME}-Bold"),
        "bold": ParagraphStyle("bold", **base, fontName=f"{FONT_NAME}-Bold"),
        "clause": ParagraphStyle(
            "clause", **base, fontName=FONT_NAME, alignment=TA_JUSTIFY,
            leftIndent=1.0 * cm, firstLineIndent=-1.0 * cm, spaceAfter=2,
        ),
        "small": ParagraphStyle("small", fontName=FONT_NAME, fontSize=11, leading=14),
    }


def _borderless_table(
    rows: list[list[str]], col_widths: list[float], styles: dict, right_align_last: bool = False, bold: bool = False
) -> Table:
    cell_style = styles["bold"] if bold else styles["plain"]
    data = [[Paragraph(cell, cell_style) for cell in row] for row in rows]
    table = Table(data, colWidths=col_widths, hAlign="LEFT")
    style_cmds = [
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]
    if right_align_last:
        style_cmds.append(("ALIGN", (-1, 0), (-1, -1), "RIGHT"))
    table.setStyle(TableStyle(style_cmds))
    return table


def render_order_pdf(order: OrderDocument) -> bytes:
    styles = _styles()
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
        leftMargin=3 * cm,
        rightMargin=1.5 * cm,
    )

    story = [
        Paragraph("УКРАЇНА", styles["header"]),
        Paragraph("МІНІСТЕРСТВО ОСВІТИ І НАУКИ УКРАЇНИ", styles["header"]),
        Paragraph("НАЦІОНАЛЬНИЙ ТЕХНІЧНИЙ УНІВЕРСИТЕТ УКРАЇНИ", styles["header"]),
        Paragraph("«КИЇВСЬКИЙ ПОЛІТЕХНІЧНИЙ ІНСТИТУТ імені ІГОРЯ СІКОРСЬКОГО»", styles["header"]),
        Paragraph("(КПІ ім. Ігоря Сікорського)", styles["header"]),
        Spacer(1, 10),
        Paragraph("НАКАЗ", styles["naked_title"]),
        Spacer(1, 6),
        _borderless_table(
            [["м. Київ", "«____» ___________ 20__ р."]],
            [9 * cm, 9 * cm],
            styles,
            right_align_last=True,
        ),
        Spacer(1, 10),
        Paragraph(order.title, styles["bold_center"]),
        Spacer(1, 10),
        Paragraph(order.preamble, styles["plain"]),
        Spacer(1, 10),
        Paragraph("НАКАЗУЮ:", styles["bold_center"]),
        Spacer(1, 6),
    ]

    for i, clause in enumerate(order.clauses, start=1):
        story.append(Paragraph(f"{i}. {clause}", styles["clause"]))

    story.append(Spacer(1, 14))
    story.append(
        _borderless_table(
            [[order.executor_position, order.executor_name]],
            [12 * cm, 6 * cm],
            styles,
            right_align_last=True,
            bold=True,
        )
    )
    story.append(Spacer(1, 20))
    story.append(Paragraph("Проєкт наказу вносить:", styles["plain"]))
    story.append(Paragraph(f"{order.dean_label} {order.faculty_genitive}", styles["plain"]))
    story.append(Spacer(1, 24))
    story.append(Paragraph(f"___________________ {order.dean_name}", styles["plain"]))
    story.append(Spacer(1, 16))
    story.append(Paragraph("ПОГОДЖЕНО:", styles["bold"]))
    story.append(Spacer(1, 6))
    story.append(
        _borderless_table(
            [
                ["Начальник ВРСП", order.vrsp_chief_name],
                ["Начальник відділу кадрів", order.hr_chief_name],
            ],
            [12 * cm, 6 * cm],
            styles,
            right_align_last=True,
        )
    )
    story.append(Spacer(1, 20))
    story.append(Paragraph("Розрахунок електронної розсилки:", styles["small"]))
    story.append(Paragraph("Факультети, навчально-наукові інститути;", styles["small"]))
    story.append(Paragraph("ДСР;", styles["small"]))
    story.append(Paragraph("Відділ кадрів.", styles["small"]))

    doc.build(story)
    return buffer.getvalue()


def render_regulation_pdf(club) -> bytes:
    from app.db.models import DIRECTION_LABELS
    from app.services import dates_uk

    styles = _styles()
    direction_nomn = DIRECTION_LABELS[club.direction]["nomn"]
    direction_plur_gent = DIRECTION_LABELS[club.direction]["plur_gent"]
    faculty_genitive = club.faculty.genitive
    order_reference = dates_uk.format_order_reference(club.order_number, club.order_date)

    heading_style = ParagraphStyle(
        "heading", fontName=f"{FONT_NAME}-Bold", fontSize=13, leading=17, spaceBefore=12, spaceAfter=6
    )
    item_style = ParagraphStyle(
        "item", fontName=FONT_NAME, fontSize=13, leading=17, alignment=TA_JUSTIFY,
        leftIndent=1 * cm, firstLineIndent=-1 * cm, spaceAfter=6,
    )
    right_style = ParagraphStyle("right", fontName=FONT_NAME, fontSize=13, leading=16, alignment=TA_RIGHT)
    title_style = ParagraphStyle(
        "title", fontName=f"{FONT_NAME}-Bold", fontSize=15, leading=19, alignment=TA_CENTER, spaceAfter=4
    )

    def numbered(items: list[str]) -> list[Paragraph]:
        return [Paragraph(f"{i}. {text}", item_style) for i, text in enumerate(items, start=1)]

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4, topMargin=2 * cm, bottomMargin=2 * cm, leftMargin=3 * cm, rightMargin=1.5 * cm
    )

    story = [
        Paragraph("ЗАТВЕРДЖЕНО", right_style),
        Paragraph("наказом КПІ ім. Ігоря Сікорського", right_style),
        Paragraph(order_reference, right_style),
        Spacer(1, 16),
        Paragraph("ПОЛОЖЕННЯ", title_style),
        Paragraph(f"про гурток «{club.name}» {direction_nomn} спрямування", title_style),
        Spacer(1, 12),
        Paragraph("1. Загальні положення", heading_style),
        *numbered(
            [
                (
                    f"Гурток «{club.name}» {direction_nomn} спрямування (далі — Гурток) є добровільним "
                    f"об’єднанням здобувачів вищої освіти КПІ ім. Ігоря Сікорського, створеним з метою "
                    f"розвитку {direction_plur_gent} здібностей його учасників."
                ),
                (
                    f"Гурток діє на базі {faculty_genitive} КПІ ім. Ігоря Сікорського за організаційної "
                    f"підтримки Департаменту студентського розвитку (відділу розвитку студентського потенціалу)."
                ),
                (
                    "У своїй діяльності Гурток керується законодавством України, Статутом "
                    "КПІ ім. Ігоря Сікорського, наказами і розпорядженнями університету та цим Положенням."
                ),
            ]
        ),
        Paragraph("2. Мета та завдання", heading_style),
        *numbered(
            [
                (
                    "Метою діяльності Гуртка є створення умов для розвитку творчого, інтелектуального та "
                    "практичного потенціалу здобувачів вищої освіти за обраним спрямуванням."
                ),
                (
                    "Основними завданнями Гуртка є: залучення здобувачів вищої освіти до систематичної "
                    "позанавчальної діяльності за спрямуванням Гуртка; підвищення рівня практичних навичок "
                    "учасників; організація та участь у заходах, конкурсах, змаганнях, конференціях "
                    "відповідного спрямування; популяризація напряму діяльності Гуртка серед студентської "
                    "спільноти університету."
                ),
            ]
        ),
        Paragraph("3. Керівництво Гуртком", heading_style),
        *numbered(
            [
                "Загальне керівництво діяльністю Гуртка здійснює керівник (керівники) Гуртка, призначений(-і) відповідним наказом ректора.",
                (
                    "Керівник Гуртка організовує поточну діяльність Гуртка, забезпечує ведення звітності, "
                    "взаємодіє з відділом розвитку студентського потенціалу ДСР із питань організаційного та "
                    "методичного супроводу Гуртка."
                ),
                "Керівник Гуртка здійснює свої повноваження на громадських засадах, без додаткової оплати праці.",
            ]
        ),
        Paragraph("4. Члени Гуртка, їхні права та обов’язки", heading_style),
        *numbered(
            [
                "Членом Гуртка може бути будь-який здобувач вищої освіти КПІ ім. Ігоря Сікорського, який виявив бажання брати участь у діяльності Гуртка.",
                (
                    "Члени Гуртка мають право: брати участь у заходах, що проводить Гурток; використовувати "
                    "матеріально-технічну базу, надану Гуртку для здійснення його діяльності; вносити "
                    "пропозиції щодо напрямів і форм роботи Гуртка."
                ),
                "Члени Гуртка зобов’язані: дотримуватися цього Положення; брати активну участь у діяльності Гуртка; дбайливо ставитися до наданого Гуртку майна.",
            ]
        ),
        Paragraph("5. Організація діяльності", heading_style),
        *numbered(
            [
                "Гурток провадить свою діяльність відповідно до плану роботи, що складається керівником Гуртка на навчальний рік.",
                "Керівник Гуртка щорічно звітує про діяльність Гуртка перед відділом розвитку студентського потенціалу ДСР у порядку, визначеному ДСР.",
                "Засідання (заняття) Гуртка проводяться регулярно, за розкладом, погодженим керівником Гуртка з учасниками.",
            ]
        ),
        Paragraph("6. Припинення діяльності", heading_style),
        *numbered(
            [
                "Діяльність Гуртка припиняється на підставі відповідного наказу КПІ ім. Ігоря Сікорського за поданням ВРСП.",
                "Підставою для припинення діяльності Гуртка може бути звернення керівника Гуртка, тривала відсутність активної діяльності Гуртка або інші обґрунтовані причини.",
            ]
        ),
    ]

    doc.build(story)
    return buffer.getvalue()


def docx_to_bytes(doc) -> bytes:
    buffer = BytesIO()
    doc.save(buffer)
    return buffer.getvalue()
