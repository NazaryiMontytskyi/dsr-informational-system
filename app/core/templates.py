from fastapi.templating import Jinja2Templates

from app.core.config import BASE_DIR
from app.db.models import (
    ClubStatus,
    DIRECTION_LABELS,
    EDUCATION_LEVEL_LABELS,
    EVENT_TYPE_LABELS,
    HeadChangeMode,
    RequestStatus,
    RequestType,
    SEMESTER_LABELS,
    STUDENT_COURSE_LABELS,
)

templates = Jinja2Templates(directory=str(BASE_DIR / "app" / "templates"))

CLUB_STATUS_LABELS = {
    ClubStatus.DRAFT: "Чернетка",
    ClubStatus.PENDING_VRSP_REVIEW: "На верифікації ВРСП",
    ClubStatus.PENDING_SIGNATURE: "Перебуває в узгодженні",
    ClubStatus.REGISTERED: "Зареєстрований",
    ClubStatus.REJECTED: "Відмовлено",
    ClubStatus.CLOSED: "Закритий",
}

REQUEST_STATUS_LABELS = {
    RequestStatus.DRAFT: "Чернетка",
    RequestStatus.ASSIGNED: "Призначено",
    RequestStatus.REJECTED: "Відмовлено",
    RequestStatus.DONE: "Виконано",
}

REQUEST_TYPE_LABELS = {
    RequestType.RENAME: "Зміна назви гуртка",
    RequestType.CHANGE_HEAD: "Зміна керівника гуртка",
    RequestType.CLOSE: "Закриття гуртка",
}

HEAD_CHANGE_MODE_LABELS = {
    HeadChangeMode.MUTUAL: "За згодою сторін",
    HeadChangeMode.ADD: "Додавання співкерівника",
    HeadChangeMode.REMOVE: "Вилучення співкерівника",
}


def status_badge(status: ClubStatus) -> str:
    return CLUB_STATUS_LABELS.get(status, status.value)


def request_status_badge(status: RequestStatus) -> str:
    return REQUEST_STATUS_LABELS.get(status, status.value)


def request_type_label(type_: RequestType) -> str:
    return REQUEST_TYPE_LABELS.get(type_, type_.value)


def head_change_mode_label(mode: HeadChangeMode) -> str:
    return HEAD_CHANGE_MODE_LABELS.get(mode, mode.value)


def direction_label(direction) -> str:
    return DIRECTION_LABELS[direction]["nomn"]


def semester_label(semester) -> str:
    return SEMESTER_LABELS.get(semester, semester.value)


def course_label(course) -> str:
    return STUDENT_COURSE_LABELS.get(course, course.value)


def education_level_label(level) -> str:
    return EDUCATION_LEVEL_LABELS.get(level, level.value)


def event_type_label(event_type) -> str:
    return EVENT_TYPE_LABELS.get(event_type, event_type.value)


templates.env.filters["status_badge"] = status_badge
templates.env.filters["request_status_badge"] = request_status_badge
templates.env.filters["request_type_label"] = request_type_label
templates.env.filters["head_change_mode_label"] = head_change_mode_label
templates.env.filters["direction_label"] = direction_label
templates.env.filters["semester_label"] = semester_label
templates.env.filters["course_label"] = course_label
templates.env.filters["education_level_label"] = education_level_label
templates.env.filters["event_type_label"] = event_type_label
