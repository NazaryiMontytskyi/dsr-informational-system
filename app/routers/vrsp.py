from datetime import date, datetime

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.core.config import STUDENT_EMAIL_DOMAIN
from app.core.deps import require_staff
from app.core.security import generate_temp_password, hash_password
from app.core.templates import templates
from app.db.models import Club, ClubStatus, User, UserRole
from app.db.session import get_db

router = APIRouter()

STATUS_TABS = [
    (ClubStatus.PENDING_VRSP_REVIEW, "На верифікації"),
    (ClubStatus.PENDING_SIGNATURE, "Перебуває в узгодженні"),
    (ClubStatus.REGISTERED, "Зареєстровані"),
    (ClubStatus.REJECTED, "Відмовлено"),
    (ClubStatus.CLOSED, "Закриті"),
]


@router.get("/vrsp/clubs")
def clubs_dashboard(request: Request, status: str = "pending_vrsp_review", db: Session = Depends(get_db), user: User = Depends(require_staff)):
    try:
        current_status = ClubStatus(status)
    except ValueError:
        current_status = ClubStatus.PENDING_VRSP_REVIEW
    clubs = db.query(Club).filter(Club.status == current_status).order_by(Club.created_at.desc()).all()
    return templates.TemplateResponse(
        request,
        "pages/vrsp_clubs.html",
        {"user": user, "clubs": clubs, "tabs": STATUS_TABS, "current_status": current_status},
    )


@router.get("/vrsp/clubs/{club_id}")
def club_detail(club_id: int, request: Request, db: Session = Depends(get_db), user: User = Depends(require_staff)):
    club = db.get(Club, club_id)
    if club is None:
        raise HTTPException(404)
    return templates.TemplateResponse(request, "pages/vrsp_club_detail.html", {"user": user, "club": club})


@router.post("/vrsp/clubs/{club_id}/approve")
def approve_club(club_id: int, db: Session = Depends(get_db), user: User = Depends(require_staff)):
    club = db.get(Club, club_id)
    if club is None or club.status != ClubStatus.PENDING_VRSP_REVIEW:
        raise HTTPException(400, "Гурток не очікує на верифікацію.")
    club.status = ClubStatus.PENDING_SIGNATURE
    db.commit()
    return RedirectResponse(f"/vrsp/clubs/{club.id}", status_code=303)


@router.post("/vrsp/clubs/{club_id}/reject")
def reject_club(club_id: int, reason: str = Form(...), db: Session = Depends(get_db), user: User = Depends(require_staff)):
    club = db.get(Club, club_id)
    if club is None or club.status not in (ClubStatus.PENDING_VRSP_REVIEW, ClubStatus.PENDING_SIGNATURE):
        raise HTTPException(400, "Дію недоступно для поточного стану гуртка.")
    club.status = ClubStatus.REJECTED
    club.rejection_reason = reason
    db.commit()
    return RedirectResponse(f"/vrsp/clubs/{club.id}", status_code=303)


@router.post("/vrsp/clubs/{club_id}/mark-signed")
def mark_signed(
    club_id: int,
    order_number: str = Form(...),
    order_date: date = Form(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_staff),
):
    club = db.get(Club, club_id)
    if club is None or club.status != ClubStatus.PENDING_SIGNATURE:
        raise HTTPException(400, "Гурток не перебуває в узгодженні.")
    club.status = ClubStatus.REGISTERED
    club.order_number = order_number
    club.order_date = order_date
    club.registered_at = datetime.utcnow()
    db.commit()
    return RedirectResponse(f"/vrsp/clubs/{club.id}", status_code=303)


@router.post("/vrsp/clubs/{club_id}/revert-to-signature")
def revert_to_signature(club_id: int, db: Session = Depends(get_db), user: User = Depends(require_staff)):
    club = db.get(Club, club_id)
    if club is None or club.status != ClubStatus.REGISTERED:
        raise HTTPException(400, "Гурток не зареєстровано.")
    club.status = ClubStatus.PENDING_SIGNATURE
    club.order_number = None
    club.order_date = None
    club.registered_at = None
    db.commit()
    return RedirectResponse(f"/vrsp/clubs/{club.id}", status_code=303)


@router.post("/vrsp/clubs/{club_id}/create-accounts")
def create_head_accounts(club_id: int, request: Request, db: Session = Depends(get_db), user: User = Depends(require_staff)):
    club = db.get(Club, club_id)
    if club is None or club.status != ClubStatus.REGISTERED:
        raise HTTPException(400, "Акаунти можна створювати лише для зареєстрованих гуртків.")

    created = []
    errors = []
    for head in club.active_heads:
        if head.user_id is not None:
            continue
        if not head.email.endswith(STUDENT_EMAIL_DOMAIN):
            errors.append(f"{head.full_name}: email має бути на домені {STUDENT_EMAIL_DOMAIN} ({head.email}).")
            continue
        existing = db.query(User).filter(User.email == head.email).first()
        if existing is not None:
            head.user_id = existing.id
            continue
        temp_password = generate_temp_password()
        new_user = User(
            email=head.email,
            full_name=head.full_name,
            password_hash=hash_password(temp_password),
            role=UserRole.HEAD,
        )
        db.add(new_user)
        db.flush()
        head.user_id = new_user.id
        created.append({"email": new_user.email, "password": temp_password, "full_name": new_user.full_name})

    db.commit()
    return templates.TemplateResponse(
        request,
        "pages/vrsp_accounts_created.html",
        {"user": user, "club": club, "created": created, "errors": errors},
    )
