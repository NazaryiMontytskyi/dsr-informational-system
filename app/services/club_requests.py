"""Застосування та відкат наслідків заявок (BP-2, BP-3, BP-4) на гурток."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from app.db.models import (
    ClubHead,
    ClubNameHistory,
    ClubRequest,
    ClubRequestHeadAction,
    ClubStatus,
    RequestStatus,
    RequestType,
)


def apply_request(db: Session, request: ClubRequest) -> None:
    club = request.club

    if request.type == RequestType.RENAME:
        db.add(ClubNameHistory(club_id=club.id, old_name=club.name))
        club.name = request.new_name

    elif request.type == RequestType.CHANGE_HEAD:
        for entry in request.head_entries:
            if entry.action == ClubRequestHeadAction.REMOVE:
                head = entry.existing_head
                head.is_active = False
                head.removed_at = datetime.utcnow()
            else:
                db.add(
                    ClubHead(
                        club_id=club.id,
                        full_name=entry.full_name,
                        email=entry.email,
                        position_type=entry.position_type,
                        position_custom=entry.position_custom,
                        department_id=entry.department_id,
                    )
                )

    elif request.type == RequestType.CLOSE:
        club.status = ClubStatus.CLOSED
        club.closed_at = datetime.utcnow()

    request.status = RequestStatus.DONE
    request.resolved_at = datetime.utcnow()


def revert_request(db: Session, request: ClubRequest) -> None:
    """Скасовує заявку зі статусу 'Виконано' назад у 'Призначено' через людський фактор."""
    club = request.club

    if request.type == RequestType.RENAME:
        last_history = (
            db.query(ClubNameHistory)
            .filter(ClubNameHistory.club_id == club.id)
            .order_by(ClubNameHistory.changed_at.desc())
            .first()
        )
        if last_history is not None:
            club.name = last_history.old_name
            db.delete(last_history)

    elif request.type == RequestType.CHANGE_HEAD:
        for entry in request.head_entries:
            if entry.action == ClubRequestHeadAction.REMOVE:
                head = entry.existing_head
                head.is_active = True
                head.removed_at = None
            else:
                new_head = (
                    db.query(ClubHead)
                    .filter(
                        ClubHead.club_id == club.id,
                        ClubHead.full_name == entry.full_name,
                        ClubHead.email == entry.email,
                    )
                    .order_by(ClubHead.id.desc())
                    .first()
                )
                if new_head is not None:
                    db.delete(new_head)

    elif request.type == RequestType.CLOSE:
        club.status = ClubStatus.REGISTERED
        club.closed_at = None

    request.status = RequestStatus.ASSIGNED
    request.resolved_at = None
