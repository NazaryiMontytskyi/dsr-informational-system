"""
Побудова наказів (BP-1..BP-4) шляхом заповнення зразків .docx із
app/order_templates реальними даними гуртка.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import docx.document
from sqlalchemy.orm import Session

from app.core.config import ORDER_TEMPLATES_DIR
from app.db.models import (
    Club,
    ClubRequest,
    ClubRequestHeadAction,
    DIRECTION_LABELS,
    DocumentSignatory,
    FacultyKind,
    PositionType,
    RequestType,
    SignatoryRole,
)
from app.services import dates_uk
from app.services.docx_fill import fill_order_template
from app.services.morphology import decline_all_words, decline_person_name, format_official_name

CONTROL_CLAUSE = "Контроль за виконанням цього наказу лишаю за собою."

PREAMBLE_CREATE = (
    "З метою підвищення інтелектуального та інноваційного рівня здобувачів вищої освіти "
    "КПІ ім. Ігоря Сікорського, мотивації до розвитку творчих здібностей, формування "
    "громадської свідомості, соціальної активності та підвищення іміджу "
    "КПІ ім. Ігоря Сікорського"
)
PREAMBLE_RENAME = "З метою забезпечення належної роботи гуртка, підтримки його організаційної діяльності"

SIGNATORY_ROLE_FOR_REQUEST_TYPE = {
    RequestType.RENAME: SignatoryRole.RENAME_ORDER,
    RequestType.CHANGE_HEAD: SignatoryRole.CHANGE_HEAD_ORDER,
    RequestType.CLOSE: SignatoryRole.CLOSE_ORDER,
}

TEMPLATE_FILES = {
    RequestType.RENAME: ORDER_TEMPLATES_DIR / "rename.docx",
    RequestType.CHANGE_HEAD: ORDER_TEMPLATES_DIR / "change_head.docx",
    RequestType.CLOSE: ORDER_TEMPLATES_DIR / "close.docx",
}
CREATE_TEMPLATE_FILE = ORDER_TEMPLATES_DIR / "create_1head.docx"


@dataclass
class OrderDocument:
    """Нейтральне (не прив'язане до .docx чи PDF) уявлення змісту наказу."""

    title: str
    preamble: str
    clauses: list[str] = field(default_factory=list)
    dean_label: str = "Декан"
    faculty_genitive: str = ""
    dean_name: str = ""
    executor_position: str = ""
    executor_name: str = ""
    vrsp_chief_name: str = ""
    hr_chief_name: str = ""


def _direction_gent(direction) -> str:
    return DIRECTION_LABELS[direction]["gent"]


def _dean_title(faculty) -> str:
    return faculty.head_title  # "декан" / "директор" (називний)


def get_signatory(db: Session, role: SignatoryRole) -> DocumentSignatory:
    signatory = db.query(DocumentSignatory).filter(DocumentSignatory.role == role).first()
    if signatory is None:
        signatory = DocumentSignatory(role=role, position_title="", full_name="")
    return signatory


def _head_position_and_department_accs(full_name: str, position_label: str, position_type, department) -> str:
    fullname_accs = format_official_name(decline_person_name(full_name, "accs"))
    position_accs = decline_all_words(position_label, "accs")
    if position_type == PositionType.OTHER:
        return f"{position_accs} {fullname_accs}"
    department_gent = department.genitive if department else ""
    return f"{position_accs} {department_gent} {fullname_accs}".strip()


def build_common_replacements(club: Club, db: Session, signatory_role: SignatoryRole) -> dict[str, str | list[str]]:
    dean_word = "Декан" if club.faculty.kind == FacultyKind.FACULTY else "Директор"
    signatory = get_signatory(db, signatory_role)
    vrsp_chief = get_signatory(db, SignatoryRole.VRSP_CHIEF)
    hr_chief = get_signatory(db, SignatoryRole.HR_CHIEF)
    return {
        "<назва гуртка>": club.name,
        "<спрямування>": _direction_gent(club.direction),
        "<Директор / декан>": dean_word,
        "<назва факультету або навчально-наукового інституту в родовому відмінку>": club.faculty.genitive,
        "<Ім’я ПРІЗВИЩЕ>": [
            format_official_name(signatory.full_name),
            format_official_name(club.faculty.dean_full_name or ""),
            format_official_name(vrsp_chief.full_name),
            format_official_name(hr_chief.full_name),
        ],
        "<назва посади>": signatory.position_title,
    }


def _create_clauses(club: Club) -> list[str]:
    direction_gent = _direction_gent(club.direction)
    heads = club.active_heads
    faculty = club.faculty

    appointment_parts = [
        f"«{club.name}» {direction_gent} спрямування "
        + _head_position_and_department_accs(head.full_name, head.position_label, head.position_type, head.department)
        for head in heads
    ]

    if len(heads) <= 1:
        appoint_clause = (
            f"Призначити керівником гуртка {appointment_parts[0]} без додаткової оплати (за згодою)."
            if appointment_parts
            else "Призначити керівника гуртка без додаткової оплати (за згодою)."
        )
    else:
        appoint_clause = (
            "Призначити керівниками гуртка " + ", ".join(appointment_parts) + " без додаткової оплати (за згодою)."
        )

    dean_datv = decline_all_words(_dean_title(faculty), "datv")
    dean_name_datv = format_official_name(decline_person_name(faculty.dean_full_name, "datv")) if faculty.dean_full_name else ""

    return [
        f"Створити гурток «{club.name}» {direction_gent} спрямування та закріпити його за {faculty.instrumental}.",
        f"Затвердити Положення про гурток «{club.name}» {direction_gent} спрямування (Додаток 1).",
        appoint_clause,
        (
            f"{dean_datv.capitalize()} {faculty.dative} {dean_name_datv} сприяти організації роботи гуртка "
            f"«{club.name}» {direction_gent} спрямування."
        ).replace("  ", " "),
        CONTROL_CLAUSE,
    ]


def _rename_clauses(request: ClubRequest) -> list[str]:
    club = request.club
    direction_gent = _direction_gent(club.direction)
    old_name = club.name
    new_name = request.new_name
    ref = dates_uk.format_order_reference(club.order_number, club.order_date)
    effective_date = request.resolved_at or request.created_at
    long_date = dates_uk.format_long_date(effective_date.date())

    return [
        f"Змінити назву гуртка «{old_name}» {direction_gent} спрямування на «{new_name}» з {long_date}.",
        f"Внести зміни до наказу {ref}, замінивши по тексту наказу та додатків до нього слова «{old_name}» на «{new_name}».",
        CONTROL_CLAUSE,
    ]


def _change_head_clauses(request: ClubRequest) -> list[str]:
    club = request.club
    direction_gent = _direction_gent(club.direction)

    remove_entries = [e for e in request.head_entries if e.action == ClubRequestHeadAction.REMOVE]
    add_entries = [e for e in request.head_entries if e.action == ClubRequestHeadAction.ADD]

    clauses: list[str] = []
    for entry in remove_entries:
        head = entry.existing_head
        piece = _head_position_and_department_accs(head.full_name, head.position_label, head.position_type, head.department)
        clauses.append(f"Зняти {piece} з посади керівника гуртка «{club.name}» {direction_gent} спрямування.")
    for entry in add_entries:
        piece = _head_position_and_department_accs(entry.full_name, entry.position_label, entry.position_type, entry.department)
        clauses.append(
            f"Призначити {piece} керівником гуртка «{club.name}» {direction_gent} спрямування без додаткової оплати (за згодою)."
        )
    clauses.append(CONTROL_CLAUSE)
    return clauses


def _close_clauses(request: ClubRequest) -> list[str]:
    club = request.club
    direction_gent = _direction_gent(club.direction)
    ref = dates_uk.format_order_reference(club.order_number, club.order_date)
    effective_date = request.resolved_at or request.created_at
    long_date = dates_uk.format_long_date(effective_date.date())

    return [
        f"Припинити діяльність гуртка «{club.name}» {direction_gent} спрямування з {long_date}.",
        f"Вважати таким, що втратив чинність наказ {ref}.",
        "Контроль за виконанням наказу лишаю за собою.",
    ]


def _clauses_for_request(request: ClubRequest) -> list[str]:
    if request.type == RequestType.RENAME:
        return _rename_clauses(request)
    if request.type == RequestType.CHANGE_HEAD:
        return _change_head_clauses(request)
    if request.type == RequestType.CLOSE:
        return _close_clauses(request)
    raise ValueError(f"Unsupported request type: {request.type}")


def render_create_order_docx(club: Club, db: Session) -> docx.document.Document:
    replacements = build_common_replacements(club, db, SignatoryRole.CREATE_ORDER)
    clauses = _create_clauses(club)
    return fill_order_template(CREATE_TEMPLATE_FILE, replacements, clauses)


def render_request_order_docx(request: ClubRequest, db: Session) -> docx.document.Document:
    club = request.club
    role = SIGNATORY_ROLE_FOR_REQUEST_TYPE[request.type]
    replacements = build_common_replacements(club, db, role)
    clauses = _clauses_for_request(request)
    template_path = TEMPLATE_FILES[request.type]
    return fill_order_template(template_path, replacements, clauses)


def _order_document(club: Club, title: str, preamble: str, clauses: list[str], db: Session, signatory_role: SignatoryRole) -> OrderDocument:
    dean_word = "Декан" if club.faculty.kind == FacultyKind.FACULTY else "Директор"
    signatory = get_signatory(db, signatory_role)
    vrsp_chief = get_signatory(db, SignatoryRole.VRSP_CHIEF)
    hr_chief = get_signatory(db, SignatoryRole.HR_CHIEF)
    return OrderDocument(
        title=title,
        preamble=preamble,
        clauses=clauses,
        dean_label=dean_word,
        faculty_genitive=club.faculty.genitive,
        dean_name=format_official_name(club.faculty.dean_full_name or ""),
        executor_position=signatory.position_title,
        executor_name=format_official_name(signatory.full_name),
        vrsp_chief_name=format_official_name(vrsp_chief.full_name),
        hr_chief_name=format_official_name(hr_chief.full_name),
    )


def build_create_order_document(club: Club, db: Session) -> OrderDocument:
    direction_gent = _direction_gent(club.direction)
    title = f"Про створення гуртка «{club.name}» {direction_gent} спрямування"
    return _order_document(club, title, PREAMBLE_CREATE, _create_clauses(club), db, SignatoryRole.CREATE_ORDER)


def build_request_order_document(request: ClubRequest, db: Session) -> OrderDocument:
    club = request.club
    direction_gent = _direction_gent(club.direction)
    clauses = _clauses_for_request(request)
    role = SIGNATORY_ROLE_FOR_REQUEST_TYPE[request.type]

    if request.type == RequestType.RENAME:
        title = f"Про зміну назви гуртка «{club.name}» {direction_gent} спрямування"
        preamble = PREAMBLE_RENAME
    elif request.type == RequestType.CHANGE_HEAD:
        title = f"Про зміну керівника гуртка «{club.name}» {direction_gent} спрямування"
        preamble = f"У зв’язку із оновленням у особовому складі керівництва гуртка «{club.name}» {direction_gent} спрямування,"
    elif request.type == RequestType.CLOSE:
        title = f"Про припинення діяльності гуртка «{club.name}» {direction_gent} спрямування"
        preamble = f"У зв’язку із припиненням діяльності гуртка «{club.name}» {direction_gent} спрямування"
    else:
        raise ValueError(f"Unsupported request type: {request.type}")

    return _order_document(club, title, preamble, clauses, db, role)
