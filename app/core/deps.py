from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.db.models import User, UserRole
from app.db.session import get_db


class NotAuthenticated(Exception):
    pass


class Forbidden(Exception):
    pass


def get_current_user_optional(request: Request, db: Session = Depends(get_db)) -> User | None:
    user_id = request.session.get("user_id")
    if not user_id:
        return None
    return db.get(User, user_id)


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    user = get_current_user_optional(request, db)
    if user is None or not user.is_active:
        raise NotAuthenticated()
    return user


def require_staff(user: User = Depends(get_current_user)) -> User:
    if user.role != UserRole.STAFF:
        raise Forbidden()
    return user


def require_head(user: User = Depends(get_current_user)) -> User:
    if user.role != UserRole.HEAD:
        raise Forbidden()
    return user
