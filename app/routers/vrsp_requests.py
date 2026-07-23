from datetime import date

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse, Response
from sqlalchemy.orm import Session

from app.core.deps import require_staff
from app.core.pdf_response import order_pdf_response
from app.core.templates import templates
from app.db.models import ClubRequest, RequestStatus, User
from app.db.session import get_db
from app.services.club_requests import apply_request, revert_request
from app.services.orders import render_request_order_docx
from app.services.pdf import docx_to_bytes

router = APIRouter()

STATUS_TABS = [
    (RequestStatus.ASSIGNED, "Призначено"),
    (RequestStatus.DONE, "Виконано"),
    (RequestStatus.REJECTED, "Відмовлено"),
]


@router.get("/vrsp/requests")
def requests_dashboard(request: Request, status: str = "assigned", db: Session = Depends(get_db), user: User = Depends(require_staff)):
    try:
        current_status = RequestStatus(status)
    except ValueError:
        current_status = RequestStatus.ASSIGNED
    items = (
        db.query(ClubRequest)
        .filter(ClubRequest.status == current_status)
        .order_by(ClubRequest.created_at.desc())
        .all()
    )
    return templates.TemplateResponse(
        request,
        "pages/vrsp_requests.html",
        {"user": user, "items": items, "tabs": STATUS_TABS, "current_status": current_status},
    )


@router.get("/vrsp/requests/{request_id}")
def request_detail(request_id: int, request: Request, db: Session = Depends(get_db), user: User = Depends(require_staff)):
    item = db.get(ClubRequest, request_id)
    if item is None:
        raise HTTPException(404)
    return templates.TemplateResponse(request, "pages/vrsp_request_detail.html", {"user": user, "item": item})


@router.get("/vrsp/requests/{request_id}/order.pdf")
def request_order_pdf(request_id: int, db: Session = Depends(get_db), user: User = Depends(require_staff)):
    item = db.get(ClubRequest, request_id)
    if item is None:
        raise HTTPException(404)
    doc = render_request_order_docx(item, db)
    return order_pdf_response(doc)


@router.get("/vrsp/requests/{request_id}/order.docx")
def request_order_docx(request_id: int, db: Session = Depends(get_db), user: User = Depends(require_staff)):
    item = db.get(ClubRequest, request_id)
    if item is None:
        raise HTTPException(404)
    doc = render_request_order_docx(item, db)
    data = docx_to_bytes(doc)
    return Response(
        data,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="order_request_{item.id}.docx"'},
    )


@router.post("/vrsp/requests/{request_id}/approve")
def approve_request(
    request_id: int,
    order_number: str = Form(...),
    order_date: date = Form(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_staff),
):
    item = db.get(ClubRequest, request_id)
    if item is None or item.status != RequestStatus.ASSIGNED:
        raise HTTPException(400, "Заявка не в статусі 'Призначено'.")
    item.order_number = order_number
    item.order_date = order_date
    apply_request(db, item)
    db.commit()
    return RedirectResponse(f"/vrsp/requests/{item.id}", status_code=303)


@router.post("/vrsp/requests/{request_id}/reject")
def reject_request(request_id: int, reason: str = Form(...), db: Session = Depends(get_db), user: User = Depends(require_staff)):
    item = db.get(ClubRequest, request_id)
    if item is None or item.status != RequestStatus.ASSIGNED:
        raise HTTPException(400, "Заявка не в статусі 'Призначено'.")
    item.status = RequestStatus.REJECTED
    item.rejection_reason = reason
    db.commit()
    return RedirectResponse(f"/vrsp/requests/{item.id}", status_code=303)


@router.post("/vrsp/requests/{request_id}/undo")
def undo_request(request_id: int, db: Session = Depends(get_db), user: User = Depends(require_staff)):
    item = db.get(ClubRequest, request_id)
    if item is None or item.status != RequestStatus.DONE:
        raise HTTPException(400, "Заявка не в статусі 'Виконано'.")
    revert_request(db, item)
    db.commit()
    return RedirectResponse(f"/vrsp/requests/{item.id}", status_code=303)
