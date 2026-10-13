from datetime import UTC, datetime

import pytest
from fastapi import HTTPException
from sqlmodel import Session

from app.models import EventDeadline
from app.services.deadlines import ensure_open, update_deadline


def test_deadline_cutoff_is_inclusive_and_closes_after(client, engine):
    with Session(engine) as session:
        cutoff = datetime(2026, 10, 15, 17, 59, 59, tzinfo=UTC)
        session.add(
            EventDeadline(
                key="subcommittee",
                label="Subcommittee",
                deadline_at=cutoff,
                is_extended=False,
            )
        )
        session.commit()

        assert ensure_open(
            "subcommittee", session, now=lambda: datetime(2026, 10, 15, 17, 59, 58, tzinfo=UTC)
        ).key == "subcommittee"
        assert ensure_open("subcommittee", session, now=lambda: cutoff).key == "subcommittee"
        with pytest.raises(HTTPException) as error:
            ensure_open(
                "subcommittee", session, now=lambda: datetime(2026, 10, 15, 18, 0, tzinfo=UTC)
            )
        assert error.value.status_code == 403
        assert error.value.detail == "Submissions closed"


def test_ensure_open_unknown_key_is_not_found(engine):
    with Session(engine) as session, pytest.raises(HTTPException) as error:
        ensure_open("missing", session, now=lambda: datetime.now(UTC))
    assert error.value.status_code == 404


def test_public_deadlines_are_seeded(client, engine):
    # Test fixtures use metadata.create_all rather than Alembic, so add the
    # migration's seed rows explicitly for this endpoint contract test.
    with Session(engine) as session:
        session.add_all(
            [
                EventDeadline(
                    key=key,
                    label=label,
                    deadline_at=datetime(2026, month, day, 17, 59, 59, tzinfo=UTC),
                    is_extended=False,
                )
                for key, label, month, day in (
                    ("subcommittee", "Subcommittee submissions", 10, 15),
                    ("sponsor", "Sponsorship submissions", 9, 30),
                    ("openmic", "Open mic submissions", 11, 15),
                    ("stall", "Stall submissions", 12, 10),
                )
            ]
        )
        session.commit()

    response = client.get("/public/deadlines")
    assert response.status_code == 200
    deadlines = {item["key"]: item for item in response.json()}
    assert set(deadlines) == {"subcommittee", "sponsor", "openmic", "stall"}
    assert deadlines["subcommittee"]["deadline_at"].startswith("2026-10-15T17:59:59")
    assert deadlines["subcommittee"]["is_extended"] is False
    assert deadlines["subcommittee"]["is_open"] is True


def test_update_deadline_updates_deadline_and_extension(engine):
    with Session(engine) as session:
        session.add(
            EventDeadline(
                key="openmic",
                label="Open mic",
                deadline_at=datetime(2026, 11, 15, 17, 59, 59),
            )
        )
        session.commit()

        updated = update_deadline(
            "openmic",
            datetime.fromisoformat("2026-11-20T23:59:59+06:00"),
            True,
            session,
        )
        assert updated.deadline_at == datetime.fromisoformat("2026-11-20T23:59:59+06:00")
        assert updated.is_extended is True


def test_update_deadline_requires_timezone(engine):
    with Session(engine) as session, pytest.raises(ValueError, match="timezone"):
        update_deadline("openmic", datetime(2026, 11, 20), True, session)


def test_update_deadline_unknown_key_is_not_found(engine):
    with Session(engine) as session, pytest.raises(HTTPException) as error:
        update_deadline(
            "missing", datetime(2026, 11, 20, tzinfo=UTC), False, session
        )
    assert error.value.status_code == 404
