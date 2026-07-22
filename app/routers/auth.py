from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.core.deps import get_current_user_optional
from app.core.security import verify_password
from app.core.templates import templates
from app.db.models import User, UserRole
from app.db.session import get_db

router = APIRouter()


def _home_url_for(user: User) -> str:
    if user.role == UserRole.STAFF:
        return "/vrsp/clubs"
    return "/my/clubs"


@router.get("/login")
def login_form(request: Request, db: Session = Depends(get_db)):
    user = get_current_user_optional(request, db)
    if user is not None:
        return RedirectResponse(_home_url_for(user), status_code=303)
    return templates.TemplateResponse(request, "pages/login.html", {"error": None})


@router.post("/login")
def login_submit(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.email == email.strip().lower()).first()
    if user is None or not user.is_active or not verify_password(password, user.password_hash):
        return templates.TemplateResponse(
            request, "pages/login.html", {"error": "Невірний email або пароль."}, status_code=401
        )
    request.session["user_id"] = user.id
    return RedirectResponse(_home_url_for(user), status_code=303)


@router.post("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login", status_code=303)
