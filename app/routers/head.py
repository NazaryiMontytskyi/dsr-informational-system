from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse, Response
from sqlalchemy.orm import Session

from app.core.config import CLUB_NAME_MAX_LEN, CLUB_NAME_MIN_LEN, FULL_NAME_MAX_LEN, FULL_NAME_MIN_LEN, MAX_CLUB_HEADS
from app.core.deps import require_head
from app.core.templates import templates
from app.db.models import (
    Club,
    ClubHead,
    ClubRequest,
    ClubRequestHead,
    ClubRequestHeadAction,
    ClubStatus,
    Department,
    Faculty,
    HeadChangeMode,
    POSITION_LABELS,
    PositionType,
    RequestStatus,
    RequestType,
    User,
)
from app.db.session import get_db
from app.services.orders import build_request_order_document
from app.services.pdf import render_order_pdf

router = APIRouter()


def _owned_club(db: Session, user: User, club_id: int) -> Club:
    club = db.get(Club, club_id)
    if club is None or not any(h.user_id == user.id for h in club.active_heads):
        raise HTTPException(404, "Гурток не знайдено.")
    return club


def _owned_request(db: Session, user: User, request_id: int) -> ClubRequest:
    item = db.get(ClubRequest, request_id)
    if item is None or item.created_by_id != user.id:
        raise HTTPException(404, "Заявку не знайдено.")
    return item


@router.get("/my/clubs")
def my_clubs(request: Request, db: Session = Depends(get_db), user: User = Depends(require_head)):
    clubs = (
        db.query(Club)
        .join(ClubHead)
        .filter(ClubHead.user_id == user.id, ClubHead.is_active.is_(True))
        .distinct()
        .all()
    )
    return templates.TemplateResponse(request, "pages/head_clubs.html", {"user": user, "clubs": clubs})


@router.get("/my/clubs/{club_id}")
def my_club_detail(club_id: int, request: Request, db: Session = Depends(get_db), user: User = Depends(require_head)):
    club = _owned_club(db, user, club_id)
    return templates.TemplateResponse(request, "pages/head_club_detail.html", {"user": user, "club": club})


# ---------- Перейменування (BP-2) ----------

@router.get("/my/clubs/{club_id}/rename")
def rename_form(club_id: int, request: Request, db: Session = Depends(get_db), user: User = Depends(require_head)):
    club = _owned_club(db, user, club_id)
    return templates.TemplateResponse(
        request, "pages/head_rename.html", {"user": user, "club": club, "name_min": CLUB_NAME_MIN_LEN, "name_max": CLUB_NAME_MAX_LEN}
    )


@router.post("/my/clubs/{club_id}/rename")
def rename_submit(club_id: int, new_name: str = Form(...), db: Session = Depends(get_db), user: User = Depends(require_head)):
    club = _owned_club(db, user, club_id)
    new_name = new_name.strip()
    if not (CLUB_NAME_MIN_LEN <= len(new_name) <= CLUB_NAME_MAX_LEN):
        raise HTTPException(400, f"Назва має містити від {CLUB_NAME_MIN_LEN} до {CLUB_NAME_MAX_LEN} символів.")
    item = ClubRequest(
        club_id=club.id, type=RequestType.RENAME, status=RequestStatus.DRAFT, new_name=new_name, created_by_id=user.id
    )
    db.add(item)
    db.commit()
    return RedirectResponse(f"/my/requests/{item.id}/review", status_code=303)


# ---------- Зміна керівника (BP-3) ----------

@router.get("/my/clubs/{club_id}/change-head")
def change_head_form(club_id: int, request: Request, db: Session = Depends(get_db), user: User = Depends(require_head)):
    club = _owned_club(db, user, club_id)
    faculties = db.query(Faculty).order_by(Faculty.name).all()
    return templates.TemplateResponse(
        request,
        "pages/head_change_head.html",
        {
            "user": user,
            "club": club,
            "faculties": faculties,
            "positions": [p for p in PositionType if p != PositionType.OTHER],
            "position_labels": POSITION_LABELS,
            "max_new_heads": MAX_CLUB_HEADS,
            "full_name_min": FULL_NAME_MIN_LEN,
            "full_name_max": FULL_NAME_MAX_LEN,
        },
    )


@router.post("/my/clubs/{club_id}/change-head")
async def change_head_submit(club_id: int, request: Request, db: Session = Depends(get_db), user: User = Depends(require_head)):
    club = _owned_club(db, user, club_id)
    form = await request.form()
    mode_raw = form.get("mode")
    if mode_raw not in HeadChangeMode._value2member_map_:
        raise HTTPException(400, "Оберіть форму зміни керівника гуртка.")
    mode = HeadChangeMode(mode_raw)

    item = ClubRequest(
        club_id=club.id, type=RequestType.CHANGE_HEAD, status=RequestStatus.DRAFT,
        head_change_mode=mode, created_by_id=user.id,
    )
    db.add(item)
    db.flush()

    if mode == HeadChangeMode.REMOVE:
        remove_ids = form.getlist("remove_head_id")
        if not remove_ids:
            raise HTTPException(400, "Оберіть щонайменше одного співкерівника для вилучення.")
        remaining = len(club.active_heads) - len(remove_ids)
        if remaining < 1:
            raise HTTPException(400, "У гуртка має лишитися щонайменше один керівник.")
        for head_id in remove_ids:
            head = db.get(ClubHead, int(head_id))
            if head is None or head.club_id != club.id:
                continue
            db.add(ClubRequestHead(request_id=item.id, action=ClubRequestHeadAction.REMOVE, existing_head_id=head.id))
    else:
        if mode == HeadChangeMode.MUTUAL:
            for head in club.active_heads:
                db.add(ClubRequestHead(request_id=item.id, action=ClubRequestHeadAction.REMOVE, existing_head_id=head.id))
            capacity = MAX_CLUB_HEADS
        else:
            capacity = MAX_CLUB_HEADS - len(club.active_heads)

        added = 0
        for i in range(1, MAX_CLUB_HEADS + 1):
            full_name = (form.get(f"head_{i}_full_name") or "").strip()
            if not full_name:
                continue
            if added >= capacity:
                raise HTTPException(400, f"Дозволено не більше {MAX_CLUB_HEADS} керівників гуртка загалом.")
            is_other = form.get(f"head_{i}_not_pedagogical") == "on"
            position_custom = (form.get(f"head_{i}_position_custom") or "").strip()
            position_type_raw = form.get(f"head_{i}_position_type")
            department_id = form.get(f"head_{i}_department_id")

            if is_other:
                position_type = PositionType.OTHER
                department = None
            else:
                if position_type_raw not in PositionType._value2member_map_:
                    raise HTTPException(400, f"Оберіть посаду для нового керівника {i}.")
                position_type = PositionType(position_type_raw)
                department = db.get(Department, int(department_id)) if department_id else None
                if department is None:
                    raise HTTPException(400, f"Оберіть кафедру для нового керівника {i}.")

            db.add(
                ClubRequestHead(
                    request_id=item.id,
                    action=ClubRequestHeadAction.ADD,
                    full_name=full_name,
                    email=(form.get(f"head_{i}_email") or "").strip().lower(),
                    position_type=position_type,
                    position_custom=position_custom if is_other else None,
                    department_id=department.id if department else None,
                )
            )
            added += 1

        if added == 0:
            raise HTTPException(400, "Вкажіть дані щонайменше одного нового керівника.")

    db.commit()
    return RedirectResponse(f"/my/requests/{item.id}/review", status_code=303)


# ---------- Закриття гуртка (BP-4) ----------

@router.get("/my/clubs/{club_id}/close")
def close_form(club_id: int, request: Request, db: Session = Depends(get_db), user: User = Depends(require_head)):
    club = _owned_club(db, user, club_id)
    return templates.TemplateResponse(request, "pages/head_close.html", {"user": user, "club": club})


@router.post("/my/clubs/{club_id}/close")
def close_submit(club_id: int, db: Session = Depends(get_db), user: User = Depends(require_head)):
    club = _owned_club(db, user, club_id)
    item = ClubRequest(club_id=club.id, type=RequestType.CLOSE, status=RequestStatus.DRAFT, created_by_id=user.id)
    db.add(item)
    db.commit()
    return RedirectResponse(f"/my/requests/{item.id}/review", status_code=303)


# ---------- Спільний перегляд/підтвердження заявки ----------

@router.get("/my/requests/{request_id}/review")
def request_review(request_id: int, request: Request, db: Session = Depends(get_db), user: User = Depends(require_head)):
    item = _owned_request(db, user, request_id)
    if item.status != RequestStatus.DRAFT:
        raise HTTPException(404)
    return templates.TemplateResponse(request, "pages/head_request_review.html", {"user": user, "item": item})


@router.post("/my/requests/{request_id}/confirm")
def request_confirm(request_id: int, db: Session = Depends(get_db), user: User = Depends(require_head)):
    item = _owned_request(db, user, request_id)
    if item.status != RequestStatus.DRAFT:
        raise HTTPException(404)
    item.status = RequestStatus.ASSIGNED
    db.commit()
    return RedirectResponse(f"/my/clubs/{item.club_id}", status_code=303)


@router.get("/my/requests/{request_id}/order.pdf")
def request_order_pdf_head(request_id: int, db: Session = Depends(get_db), user: User = Depends(require_head)):
    item = _owned_request(db, user, request_id)
    order = build_request_order_document(item, db)
    pdf_bytes = render_order_pdf(order)
    return Response(pdf_bytes, media_type="application/pdf")
