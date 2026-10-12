from collections.abc import Callable
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlmodel import Session

from app.helper import now as current_time
from app.models import EventDeadline


def ensure_open(
    key: str,
    database_session: Session,
    now: Callable[[], datetime] = current_time,
) -> EventDeadline:
    deadline = database_session.get(EventDeadline, key)
    if deadline is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deadline not found")

    current = now()
    if current.tzinfo is None:
        current = current.replace(tzinfo=UTC)
    cutoff = deadline.deadline_at
    if cutoff.tzinfo is None:
        cutoff = cutoff.replace(tzinfo=UTC)
    if current > cutoff:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Submissions closed",
        )
    return deadline


def deadline_is_open(deadline: EventDeadline, now: datetime | None = None) -> bool:
    current = now or current_time()
    cutoff = deadline.deadline_at
    if current.tzinfo is None:
        current = current.replace(tzinfo=UTC)
    if cutoff.tzinfo is None:
        cutoff = cutoff.replace(tzinfo=UTC)
    return current <= cutoff


def update_deadline(
    key: str,
    deadline_at: datetime,
    is_extended: bool | None,
    session: Session,
) -> EventDeadline:
    if deadline_at.tzinfo is None or deadline_at.utcoffset() is None:
        raise ValueError("deadline_at must include a timezone")

    deadline = session.get(EventDeadline, key)
    if deadline is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deadline not found")

    deadline.deadline_at = deadline_at
    if is_extended is not None:
        deadline.is_extended = is_extended
    session.add(deadline)
    session.commit()
    session.refresh(deadline)
    return deadline
