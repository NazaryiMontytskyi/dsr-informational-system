from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.core.deps import require_staff
from app.core.templates import templates
from app.db.models import DocumentSignatory, Faculty, SIGNATORY_ROLE_LABELS, SignatoryRole, User
from app.db.session import get_db

router = APIRouter()


@router.get("/vrsp/settings")
def settings_page(request: Request, db: Session = Depends(get_db), user: User = Depends(require_staff)):
    signatories = db.query(DocumentSignatory).all()
    signatories_by_role = {s.role: s for s in signatories}
    ordered = [
        (role, label, signatories_by_role.get(role))
        for role, label in SIGNATORY_ROLE_LABELS.items()
    ]
    faculties = db.query(Faculty).order_by(Faculty.name).all()
    return templates.TemplateResponse(
        request, "pages/vrsp_settings.html", {"user": user, "signatories": ordered, "faculties": faculties}
    )


@router.post("/vrsp/settings/signatories")
async def update_signatories(request: Request, db: Session = Depends(get_db), user: User = Depends(require_staff)):
    form = await request.form()
    for role in SignatoryRole:
        position_title = (form.get(f"{role.value}_position_title") or "").strip()
        full_name = (form.get(f"{role.value}_full_name") or "").strip()
        signatory = db.query(DocumentSignatory).filter(DocumentSignatory.role == role).first()
        if signatory is None:
            signatory = DocumentSignatory(role=role)
            db.add(signatory)
        signatory.position_title = position_title
        signatory.full_name = full_name
    db.commit()
    return RedirectResponse("/vrsp/settings", status_code=303)


@router.post("/vrsp/settings/faculties/{faculty_id}")
def update_faculty_dean(
    faculty_id: int,
    dean_full_name: str = Form(""),
    db: Session = Depends(get_db),
    user: User = Depends(require_staff),
):
    faculty = db.get(Faculty, faculty_id)
    if faculty is not None:
        faculty.dean_full_name = dean_full_name.strip()
        db.commit()
    return RedirectResponse("/vrsp/settings", status_code=303)
