from datetime import date

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.core.config import (
    REPORT_EVENT_NAME_MAX_LEN,
    REPORT_EVENT_TYPE_CUSTOM_MAX_LEN,
    REPORT_GROUP_CODE_MAX_LEN,
    REPORT_TEXT_MAX_LEN,
)
from app.core.deps import require_head, require_staff
from app.core.templates import templates
from app.db.models import (
    Club,
    ClubHead,
    ClubReport,
    EducationLevel,
    EventType,
    Faculty,
    ReportAchievement,
    ReportEvent,
    ReportParticipant,
    ReportSession,
    Semester,
    StudentCourse,
    User,
)
from app.db.session import get_db

router = APIRouter()


# ---------- ВРСП: сесії збору звітів ----------

@router.get("/vrsp/reports")
def vrsp_reports_list(request: Request, db: Session = Depends(get_db), user: User = Depends(require_staff)):
    sessions = db.query(ReportSession).order_by(ReportSession.start_date.desc()).all()
    return templates.TemplateResponse(request, "pages/vrsp_reports.html", {"user": user, "sessions": sessions})


@router.get("/vrsp/reports/new")
def vrsp_report_session_form(request: Request, db: Session = Depends(get_db), user: User = Depends(require_staff)):
    return templates.TemplateResponse(
        request, "pages/vrsp_report_session_new.html", {"user": user, "semesters": list(Semester)}
    )


@router.post("/vrsp/reports/new")
def vrsp_report_session_create(
    request: Request,
    year: int = Form(...),
    semester: str = Form(...),
    start_date: date = Form(...),
    end_date: date = Form(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_staff),
):
    if semester not in Semester._value2member_map_:
        raise HTTPException(400, "Оберіть семестр.")
    if end_date < start_date:
        raise HTTPException(400, "Дата завершення не може бути раніше дати початку.")
    session_obj = ReportSession(
        year=year, semester=Semester(semester), start_date=start_date, end_date=end_date, created_by_id=user.id
    )
    db.add(session_obj)
    db.commit()
    return RedirectResponse(f"/vrsp/reports/{session_obj.id}", status_code=303)


@router.get("/vrsp/reports/{session_id}")
def vrsp_report_session_detail(
    session_id: int, request: Request, db: Session = Depends(get_db), user: User = Depends(require_staff)
):
    session_obj = db.get(ReportSession, session_id)
    if session_obj is None:
        raise HTTPException(404)
    return templates.TemplateResponse(
        request, "pages/vrsp_report_session_detail.html", {"user": user, "session": session_obj}
    )


@router.get("/vrsp/reports/{session_id}/{report_id}")
def vrsp_report_detail(
    session_id: int, report_id: int, request: Request, db: Session = Depends(get_db), user: User = Depends(require_staff)
):
    report = db.get(ClubReport, report_id)
    if report is None or report.session_id != session_id:
        raise HTTPException(404)
    return templates.TemplateResponse(request, "pages/report_detail.html", {"user": user, "report": report, "back_url": f"/vrsp/reports/{session_id}"})


# ---------- Керівник гуртка: заповнення звіту ----------

def _owned_club_for_report(db: Session, user: User, club_id: int) -> Club:
    club = db.get(Club, club_id)
    if club is None or not any(h.user_id == user.id for h in club.active_heads):
        raise HTTPException(404, "Гурток не знайдено.")
    return club


@router.get("/my/reports")
def head_reports_list(request: Request, db: Session = Depends(get_db), user: User = Depends(require_head)):
    clubs = (
        db.query(Club)
        .join(ClubHead)
        .filter(ClubHead.user_id == user.id, ClubHead.is_active.is_(True))
        .distinct()
        .all()
    )
    sessions = db.query(ReportSession).order_by(ReportSession.start_date.desc()).all()
    submitted_ids = {
        (r.session_id, r.club_id)
        for r in db.query(ClubReport).filter(ClubReport.club_id.in_([c.id for c in clubs])).all()
    } if clubs else set()

    rows = []
    for session_obj in sessions:
        for club in clubs:
            rows.append({"session": session_obj, "club": club, "submitted": (session_obj.id, club.id) in submitted_ids})

    return templates.TemplateResponse(
        request, "pages/head_reports.html", {"user": user, "rows": rows, "has_clubs": bool(clubs)}
    )


@router.get("/my/reports/{session_id}/{club_id}/fill")
def head_report_fill_form(
    session_id: int, club_id: int, request: Request, db: Session = Depends(get_db), user: User = Depends(require_head)
):
    club = _owned_club_for_report(db, user, club_id)
    session_obj = db.get(ReportSession, session_id)
    if session_obj is None or not session_obj.is_active:
        raise HTTPException(400, "Сесія звітування неактивна.")
    existing = db.query(ClubReport).filter(ClubReport.session_id == session_id, ClubReport.club_id == club_id).first()
    if existing is not None:
        raise HTTPException(400, "Звіт для цього гуртка вже подано.")
    faculties = db.query(Faculty).order_by(Faculty.name).all()
    return templates.TemplateResponse(
        request,
        "pages/head_report_fill.html",
        {
            "user": user,
            "club": club,
            "session": session_obj,
            "faculties": faculties,
            "courses": list(StudentCourse),
            "education_levels": list(EducationLevel),
            "event_types": [t for t in EventType if t != EventType.OTHER],
            "text_max": REPORT_TEXT_MAX_LEN,
            "group_code_max": REPORT_GROUP_CODE_MAX_LEN,
            "event_name_max": REPORT_EVENT_NAME_MAX_LEN,
            "event_type_custom_max": REPORT_EVENT_TYPE_CUSTOM_MAX_LEN,
        },
    )


@router.post("/my/reports/{session_id}/{club_id}/fill")
async def head_report_fill_submit(
    session_id: int, club_id: int, request: Request, db: Session = Depends(get_db), user: User = Depends(require_head)
):
    club = _owned_club_for_report(db, user, club_id)
    session_obj = db.get(ReportSession, session_id)
    if session_obj is None or not session_obj.is_active:
        raise HTTPException(400, "Сесія звітування неактивна.")
    existing = db.query(ClubReport).filter(ClubReport.session_id == session_id, ClubReport.club_id == club_id).first()
    if existing is not None:
        raise HTTPException(400, "Звіт для цього гуртка вже подано.")

    form = await request.form()

    report = ClubReport(
        session_id=session_id,
        club_id=club_id,
        projects_activities=(form.get("projects_activities") or "").strip()[:REPORT_TEXT_MAX_LEN],
        difficulties=(form.get("difficulties") or "").strip()[:REPORT_TEXT_MAX_LEN],
        encouragement=(form.get("encouragement") or "").strip()[:REPORT_TEXT_MAX_LEN],
        plans=(form.get("plans") or "").strip()[:REPORT_TEXT_MAX_LEN],
        submitted_by_id=user.id,
    )
    db.add(report)
    db.flush()

    # 1. учасники гуртка
    i = 1
    participant_count = 0
    while form.get(f"participant_{i}_full_name") is not None:
        full_name = (form.get(f"participant_{i}_full_name") or "").strip()
        if full_name:
            course_raw = form.get(f"participant_{i}_course")
            level_raw = form.get(f"participant_{i}_education_level")
            faculty_id_raw = form.get(f"participant_{i}_faculty_id")
            if course_raw not in StudentCourse._value2member_map_:
                raise HTTPException(400, f"Оберіть курс для учасника {i}.")
            if level_raw not in EducationLevel._value2member_map_:
                raise HTTPException(400, f"Оберіть освітній рівень для учасника {i}.")
            if not faculty_id_raw:
                raise HTTPException(400, f"Оберіть підрозділ для учасника {i}.")
            db.add(
                ReportParticipant(
                    report_id=report.id,
                    full_name=full_name,
                    course=StudentCourse(course_raw),
                    group_code=(form.get(f"participant_{i}_group_code") or "").strip()[:REPORT_GROUP_CODE_MAX_LEN],
                    education_level=EducationLevel(level_raw),
                    faculty_id=int(faculty_id_raw),
                )
            )
            participant_count += 1
        i += 1

    if participant_count == 0:
        raise HTTPException(400, "Вкажіть щонайменше одного учасника гуртка.")

    # 3. заходи участі
    i = 1
    while form.get(f"event_{i}_name") is not None:
        name = (form.get(f"event_{i}_name") or "").strip()
        if name:
            type_raw = form.get(f"event_{i}_type")
            if type_raw not in EventType._value2member_map_:
                raise HTTPException(400, f"Оберіть тип заходу {i}.")
            event_type = EventType(type_raw)
            custom_name = (form.get(f"event_{i}_type_custom") or "").strip()[:REPORT_EVENT_TYPE_CUSTOM_MAX_LEN]
            db.add(
                ReportEvent(
                    report_id=report.id,
                    name=name[:REPORT_EVENT_NAME_MAX_LEN],
                    event_type=event_type,
                    event_type_custom=custom_name if event_type == EventType.OTHER else None,
                    achievements_description=(form.get(f"event_{i}_description") or "").strip()[:REPORT_TEXT_MAX_LEN],
                )
            )
        i += 1

    # 4. досягнення учасників
    i = 1
    while form.get(f"achievement_{i}_full_name") is not None:
        full_name = (form.get(f"achievement_{i}_full_name") or "").strip()
        description = (form.get(f"achievement_{i}_description") or "").strip()
        if full_name and description:
            db.add(
                ReportAchievement(
                    report_id=report.id,
                    participant_full_name=full_name,
                    description=description[:REPORT_TEXT_MAX_LEN],
                )
            )
        i += 1

    db.commit()
    return RedirectResponse(f"/my/reports/{session_id}/{club_id}", status_code=303)


@router.get("/my/reports/{session_id}/{club_id}")
def head_report_detail(
    session_id: int, club_id: int, request: Request, db: Session = Depends(get_db), user: User = Depends(require_head)
):
    _owned_club_for_report(db, user, club_id)
    report = db.query(ClubReport).filter(ClubReport.session_id == session_id, ClubReport.club_id == club_id).first()
    if report is None:
        raise HTTPException(404, "Звіт ще не подано.")
    return templates.TemplateResponse(request, "pages/report_detail.html", {"user": user, "report": report, "back_url": "/my/reports"})
