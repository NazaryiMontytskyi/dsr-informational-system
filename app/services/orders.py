"""
Побудова наказів (BP-1..BP-4) шляхом заповнення зразків .docx із
app/order_templates реальними даними гуртка.
"""

from __future__ import annotations

import docx.document
from sqlalchemy.orm import Session

from app.core.config import ORDER_TEMPLATES_DIR
from app.db.models import (
    Club,
    ClubRequest,
    ClubRequestHeadAction,
    DIRECTION_LABELS,
    DocumentSignatory,
    Faculty,
    FacultyKind,
    HeadChangeMode,
    PositionType,
    RequestType,
    SignatoryRole,
)
from app.services import dates_uk
from app.services.docx_fill import fill_order_template
from app.services.morphology import decline_all_words, decline_first_word_only, decline_person_name, format_official_name

CONTROL_CLAUSE = "Контроль за виконанням цього наказу лишаю за собою."

TEMPLATE_FILES = {
    RequestType.RENAME: ORDER_TEMPLATES_DIR / "rename.docx",
    RequestType.CHANGE_HEAD: ORDER_TEMPLATES_DIR / "change_head.docx",
    RequestType.CLOSE: ORDER_TEMPLATES_DIR / "close.docx",
}
CREATE_TEMPLATE_FILE = ORDER_TEMPLATES_DIR / "create_1head.docx"
CHANGE_HEAD_COHEAD_TEMPLATE_FILE = ORDER_TEMPLATES_DIR / "change_head_cohead.docx"


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
    if position_type == PositionType.OTHER:
        # Довільний текст посади вводить сама людина і вже містить власний
        # "хвіст" у родовому відмінку (напр. "начальник відділу розвитку
        # студентського потенціалу департаменту студентського розвитку") --
        # відмінюємо лише перше ("головне") слово, решту лишаємо як є.
        position_accs = decline_first_word_only(position_label, "accs")
        return f"{position_accs} {fullname_accs}"
    position_accs = decline_all_words(position_label, "accs")
    department_gent = department.genitive if department else ""
    return f"{position_accs} {department_gent} {fullname_accs}".strip()


def _submitter_block(club: Club, db: Session, *, override_faculty: Faculty | None = None, use_vrsp_chief: bool = False) -> tuple[str, str, str]:
    """
    Повертає (роль, абревіатура підрозділу, ПІБ) для розділу "Проєкт наказу
    вносить". Типово це декан/директор власного факультету гуртка -- але
    для заявок на додавання/вилучення співкерівника вносить наказ
    декан/директор ТОГО підрозділу, звідки походить співкерівник, а якщо
    такого підрозділу декілька -- Начальник ВРСП.
    """
    if use_vrsp_chief:
        vrsp_chief = get_signatory(db, SignatoryRole.VRSP_CHIEF)
        return ("Начальник ВРСП", "", vrsp_chief.full_name)
    faculty = override_faculty or club.faculty
    dean_word = "Декан" if faculty.kind == FacultyKind.FACULTY else "Директор"
    return (dean_word, faculty.abbreviation, faculty.dean_full_name or "")


def build_common_replacements(
    club: Club, db: Session, *, submitter: tuple[str, str, str] | None = None
) -> dict[str, str | list[str]]:
    submitter_role, submitter_department, submitter_name = submitter or _submitter_block(club, db)
    signatory = get_signatory(db, SignatoryRole.ORDER)
    vrsp_chief = get_signatory(db, SignatoryRole.VRSP_CHIEF)
    hr_chief = get_signatory(db, SignatoryRole.HR_CHIEF)
    return {
        "<назва гуртка>": club.name,
        "<спрямування>": _direction_gent(club.direction),
        "<Директор / декан>": submitter_role,
        "<назва факультету або навчально-наукового інституту в родовому відмінку>": submitter_department,
        "<Ім’я ПРІЗВИЩЕ>": [
            format_official_name(signatory.full_name),
            format_official_name(submitter_name),
            format_official_name(vrsp_chief.full_name),
            format_official_name(hr_chief.full_name),
        ],
        "<назва посади>": signatory.position_title,
    }


def _create_clauses(club: Club) -> list[str]:
    direction_gent = _direction_gent(club.direction)
    heads = club.active_heads
    faculty = club.faculty

    club_ref = f"«{club.name}» {direction_gent} спрямування"
    appointment_parts = [
        _head_position_and_department_accs(head.full_name, head.position_label, head.position_type, head.department)
        for head in heads
    ]

    if len(heads) <= 1:
        appoint_clause = (
            f"Призначити керівником гуртка {club_ref} {appointment_parts[0]} без додаткової оплати (за згодою)."
            if appointment_parts
            else f"Призначити керівника гуртка {club_ref} без додаткової оплати (за згодою)."
        )
    else:
        appoint_clause = (
            f"Призначити керівниками гуртка {club_ref} "
            + ", ".join(appointment_parts)
            + " без додаткової оплати (за згодою)."
        )

    dean_datv = decline_all_words(_dean_title(faculty), "datv")
    dean_name_datv = format_official_name(decline_person_name(faculty.dean_full_name, "datv")) if faculty.dean_full_name else ""

    return [
        f"Створити гурток «{club.name}» {direction_gent} спрямування та закріпити його за {faculty.instrumental}.",
        f"Затвердити Положення про гурток «{club.name}» {direction_gent} спрямування (Додаток 1).",
        appoint_clause,
        (
            f"{dean_datv.capitalize()} {faculty.abbreviation} {dean_name_datv} сприяти організації роботи гуртка "
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
    club_ref = f"«{club.name}» {direction_gent} спрямування"
    is_mutual = request.head_change_mode == HeadChangeMode.MUTUAL

    remove_entries = [e for e in request.head_entries if e.action == ClubRequestHeadAction.REMOVE]
    add_entries = [e for e in request.head_entries if e.action == ClubRequestHeadAction.ADD]

    clauses: list[str] = []
    for entry in remove_entries:
        head = entry.existing_head
        piece = _head_position_and_department_accs(head.full_name, head.position_label, head.position_type, head.department)
        if is_mutual:
            clauses.append(f"Зняти {piece} з посади керівника гуртка {club_ref}.")
        else:
            clauses.append(f"Звільнити {piece} від обов’язків керівника гуртка {club_ref}.")
    for entry in add_entries:
        piece = _head_position_and_department_accs(entry.full_name, entry.position_label, entry.position_type, entry.department)
        role_word = "керівником" if is_mutual else "співкерівником"
        clauses.append(f"Призначити {piece} {role_word} гуртка {club_ref} без додаткової оплати (за згодою).")
    clauses.append(CONTROL_CLAUSE)
    return clauses


def _change_head_submitter(request: ClubRequest, db: Session) -> tuple[str, str, str] | None:
    """
    Для mutual-заміни вносить наказ декан/директор власного факультету
    гуртка (типова поведінка, submitter=None). Для додавання/вилучення
    співкерівника -- декан/директор факультету, звідки походить
    співкерівник; якщо співкерівників декілька -- Начальник ВРСП.
    """
    if request.head_change_mode == HeadChangeMode.MUTUAL:
        return None

    action = ClubRequestHeadAction.ADD if request.head_change_mode == HeadChangeMode.ADD else ClubRequestHeadAction.REMOVE
    entries = [e for e in request.head_entries if e.action == action]
    departments = [
        (e.department if action == ClubRequestHeadAction.ADD else e.existing_head.department) for e in entries
    ]

    if len(departments) == 1 and departments[0] is not None:
        return _submitter_block(request.club, db, override_faculty=departments[0].faculty)
    return _submitter_block(request.club, db, use_vrsp_chief=True)


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
    replacements = build_common_replacements(club, db)
    clauses = _create_clauses(club)
    return fill_order_template(CREATE_TEMPLATE_FILE, replacements, clauses)


def render_request_order_docx(request: ClubRequest, db: Session) -> docx.document.Document:
    club = request.club
    submitter = None
    template_path = TEMPLATE_FILES[request.type]
    if request.type == RequestType.CHANGE_HEAD:
        submitter = _change_head_submitter(request, db)
        if request.head_change_mode != HeadChangeMode.MUTUAL:
            template_path = CHANGE_HEAD_COHEAD_TEMPLATE_FILE
    replacements = build_common_replacements(club, db, submitter=submitter)
    clauses = _clauses_for_request(request)
    return fill_order_template(template_path, replacements, clauses)
