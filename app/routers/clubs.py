import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, Form, HTTPException, Request, UploadFile
from fastapi.responses import RedirectResponse, Response
from sqlalchemy.orm import Session

from app.core.config import BASE_DIR, CLUB_NAME_MAX_LEN, CLUB_NAME_MIN_LEN, FULL_NAME_MAX_LEN, FULL_NAME_MIN_LEN, MAX_CLUB_HEADS
from app.core.templates import templates
from app.db.models import (
    Club,
    ClubDirection,
    ClubHead,
    ClubStatus,
    DIRECTION_LABELS,
    Department,
    Faculty,
    POSITION_LABELS,
    PositionType,
    RegulationType,
)
from app.core.pdf_response import order_pdf_response, regulation_pdf_response
from app.db.session import get_db
from app.services.orders import render_create_order_docx
from app.services.pdf import docx_to_bytes
from app.services.regulation_docx import build_regulation_document

router = APIRouter()

REGULATIONS_DIR = BASE_DIR / "app" / "uploads" / "regulations"


def _form_context(db: Session) -> dict:
    faculties = db.query(Faculty).order_by(Faculty.name).all()
    return {
        "faculties": faculties,
        "directions": list(ClubDirection),
        "direction_labels": {d: DIRECTION_LABELS[d]["nomn"] for d in ClubDirection},
        "positions": [p for p in PositionType if p != PositionType.OTHER],
        "position_labels": POSITION_LABELS,
        "max_heads": MAX_CLUB_HEADS,
        "name_min": CLUB_NAME_MIN_LEN,
        "name_max": CLUB_NAME_MAX_LEN,
        "full_name_min": FULL_NAME_MIN_LEN,
        "full_name_max": FULL_NAME_MAX_LEN,
    }


@router.get("/clubs/new")
def new_club_form(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse(request, "pages/club_new.html", {"user": None, "errors": [], **_form_context(db)})


def _parse_head_blocks(form) -> list[dict]:
    heads = []
    for i in range(1, MAX_CLUB_HEADS + 1):
        full_name = (form.get(f"head_{i}_full_name") or "").strip()
        if not full_name:
            continue
        is_other = form.get(f"head_{i}_not_pedagogical") == "on"
        heads.append(
            {
                "full_name": full_name,
                "email": (form.get(f"head_{i}_email") or "").strip().lower(),
                "position_type": form.get(f"head_{i}_position_type"),
                "position_custom": (form.get(f"head_{i}_position_custom") or "").strip(),
                "is_other": is_other,
                "faculty_id": form.get(f"head_{i}_faculty_id"),
                "department_id": form.get(f"head_{i}_department_id"),
            }
        )
    return heads


@router.post("/clubs/new")
async def create_club(request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    errors: list[str] = []

    name = (form.get("name") or "").strip()
    direction_raw = form.get("direction")
    faculty_id = form.get("faculty_id")
    regulation_choice = form.get("regulation_type", "standard")
    regulation_file: UploadFile | None = form.get("regulation_file")

    if not (CLUB_NAME_MIN_LEN <= len(name) <= CLUB_NAME_MAX_LEN):
        errors.append(f"Назва гуртка має містити від {CLUB_NAME_MIN_LEN} до {CLUB_NAME_MAX_LEN} символів.")

    direction = None
    if direction_raw not in ClubDirection._value2member_map_:
        errors.append("Оберіть спрямування гуртка.")
    else:
        direction = ClubDirection(direction_raw)

    faculty = db.get(Faculty, int(faculty_id)) if faculty_id else None
    if faculty is None:
        errors.append("Оберіть підрозділ, за яким буде закріплено гурток.")

    heads_raw = _parse_head_blocks(form)
    if not heads_raw:
        errors.append("Потрібно вказати щонайменше одного керівника гуртка.")
    if len(heads_raw) > MAX_CLUB_HEADS:
        errors.append(f"Дозволено не більше {MAX_CLUB_HEADS} керівників гуртка.")

    parsed_heads = []
    for idx, h in enumerate(heads_raw, start=1):
        if not (FULL_NAME_MIN_LEN <= len(h["full_name"]) <= FULL_NAME_MAX_LEN):
            errors.append(f"ПІБ керівника {idx}: має містити від {FULL_NAME_MIN_LEN} до {FULL_NAME_MAX_LEN} символів.")
        if not h["email"]:
            errors.append(f"Керівник {idx}: вкажіть email.")

        position_type = None
        department = None
        if h["is_other"]:
            if not h["position_custom"]:
                errors.append(f"Керівник {idx}: вкажіть повну назву посади.")
            position_type = PositionType.OTHER
        else:
            if h["position_type"] not in PositionType._value2member_map_:
                errors.append(f"Керівник {idx}: оберіть посаду.")
            else:
                position_type = PositionType(h["position_type"])
            if h["department_id"]:
                department = db.get(Department, int(h["department_id"]))
            if department is None:
                errors.append(f"Керівник {idx}: оберіть кафедру.")

        parsed_heads.append(
            {
                "full_name": h["full_name"],
                "email": h["email"],
                "position_type": position_type,
                "position_custom": h["position_custom"] if h["is_other"] else None,
                "department": department,
            }
        )

    custom_regulation_bytes = None
    if regulation_choice == "custom":
        if regulation_file is None or not getattr(regulation_file, "filename", ""):
            errors.append("Прикріпіть PDF-файл проєкту Положення про гурток.")
        else:
            custom_regulation_bytes = await regulation_file.read()

    if errors:
        return templates.TemplateResponse(
            request, "pages/club_new.html", {"user": None, "errors": errors, **_form_context(db)}, status_code=400
        )

    club = Club(
        name=name,
        direction=direction,
        faculty_id=faculty.id,
        status=ClubStatus.DRAFT,
        regulation_type=RegulationType.CUSTOM if regulation_choice == "custom" else RegulationType.STANDARD,
    )
    db.add(club)
    db.flush()

    for h in parsed_heads:
        db.add(
            ClubHead(
                club_id=club.id,
                full_name=h["full_name"],
                email=h["email"],
                position_type=h["position_type"],
                position_custom=h["position_custom"],
                department_id=h["department"].id if h["department"] else None,
            )
        )

    if custom_regulation_bytes is not None:
        REGULATIONS_DIR.mkdir(parents=True, exist_ok=True)
        file_path = REGULATIONS_DIR / f"{uuid.uuid4().hex}.pdf"
        file_path.write_bytes(custom_regulation_bytes)
        club.regulation_file_path = str(file_path.relative_to(BASE_DIR))

    db.commit()
    return RedirectResponse(f"/clubs/{club.id}/review", status_code=303)


def _get_draft_club(db: Session, club_id: int) -> Club:
    club = db.get(Club, club_id)
    if club is None or club.status != ClubStatus.DRAFT:
        raise HTTPException(404, "Гурток не знайдено або вже подано на розгляд.")
    return club


@router.get("/clubs/{club_id}/review")
def review_club(club_id: int, request: Request, db: Session = Depends(get_db)):
    club = _get_draft_club(db, club_id)
    return templates.TemplateResponse(request, "pages/club_review.html", {"user": None, "club": club})


@router.post("/clubs/{club_id}/confirm")
def confirm_club(club_id: int, request: Request, db: Session = Depends(get_db)):
    club = _get_draft_club(db, club_id)
    club.status = ClubStatus.PENDING_VRSP_REVIEW
    db.commit()
    return RedirectResponse(f"/clubs/{club.id}/submitted", status_code=303)


@router.get("/clubs/{club_id}/submitted")
def submitted_page(club_id: int, request: Request, db: Session = Depends(get_db)):
    club = db.get(Club, club_id)
    if club is None:
        raise HTTPException(404)
    return templates.TemplateResponse(request, "pages/club_submitted.html", {"user": None, "club": club})


@router.get("/clubs/{club_id}/order.pdf")
def club_order_pdf(club_id: int, db: Session = Depends(get_db)):
    club = db.get(Club, club_id)
    if club is None:
        raise HTTPException(404)
    doc = render_create_order_docx(club, db)
    return order_pdf_response(doc)


@router.get("/clubs/{club_id}/order.docx")
def club_order_docx(club_id: int, db: Session = Depends(get_db)):
    club = db.get(Club, club_id)
    if club is None:
        raise HTTPException(404)
    doc = render_create_order_docx(club, db)
    data = docx_to_bytes(doc)
    return Response(
        data,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="order_{club.id}.docx"'},
    )


@router.get("/clubs/{club_id}/regulation.pdf")
def club_regulation_pdf(club_id: int, db: Session = Depends(get_db)):
    club = db.get(Club, club_id)
    if club is None:
        raise HTTPException(404)
    if club.regulation_type == RegulationType.CUSTOM and club.regulation_file_path:
        data = (BASE_DIR / club.regulation_file_path).read_bytes()
        return Response(data, media_type="application/pdf")
    doc = build_regulation_document(club)
    return regulation_pdf_response(doc)
