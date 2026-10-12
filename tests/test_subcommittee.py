from datetime import UTC, datetime, timedelta

import pytest
from sqlmodel import Session, select

from app.constants import SUBCOMMITTEE_NAMES
from app.models import EventDeadline, SubcommitteeApplication


@pytest.fixture
def open_subcommittee_deadline(engine):
    with Session(engine) as session:
        session.add(
            EventDeadline(
                key="subcommittee",
                label="Subcommittee submissions",
                deadline_at=datetime.now(UTC) + timedelta(days=1),
                is_extended=False,
            )
        )
        session.commit()


@pytest.fixture
def application_payload():
    return {
        "first_choice": "Registration",
        "second_choice": "Logistics",
        "motivation": "I want to help make the jubilee organized and welcoming.",
        "availability_notes": "Evenings and weekends",
    }


@pytest.fixture
def other_alumna(client, admin_headers, registration_payload):
    payload = {**registration_payload, "email": "other@example.com"}
    body = client.post("/auth/register", json=payload).json()
    client.patch(
        f"/admin/alumnae/{body['uuid']}/status",
        params={"new_status": "confirmed"},
        headers=admin_headers,
    )
    return payload


def test_options_are_public(client):
    response = client.get("/involve/subcommittee/options")
    assert response.status_code == 200
    assert response.json() == SUBCOMMITTEE_NAMES


def test_create_application(client, client_login, open_subcommittee_deadline, application_payload):
    response = client.post("/involve/subcommittee", json=application_payload)
    assert response.status_code == 201
    body = response.json()
    assert body["first_choice"] == "Registration"
    assert body["status"] == "submitted"
    assert body["admin_note"] is None
    assert "alumna_uuid" not in body


def test_create_duplicate_returns_conflict(
    client, client_login, open_subcommittee_deadline, application_payload
):
    assert client.post("/involve/subcommittee", json=application_payload).status_code == 201
    response = client.post("/involve/subcommittee", json=application_payload)
    assert response.status_code == 409


def test_create_requires_authentication(client, open_subcommittee_deadline, application_payload):
    assert client.post("/involve/subcommittee", json=application_payload).status_code == 401


@pytest.mark.parametrize(
    "changes",
    [
        {"first_choice": "Made up"},
        {"second_choice": "Registration"},
        {"motivation": "too short"},
        {"motivation": "x" * 1001},
        {"availability_notes": "x" * 501},
    ],
)
def test_invalid_application_returns_validation_error(
    client, client_login, open_subcommittee_deadline, application_payload, changes
):
    response = client.post(
        "/involve/subcommittee", json={**application_payload, **changes}
    )
    assert response.status_code == 422


def test_read_missing_application_returns_not_found(client, client_login):
    response = client.get("/involve/subcommittee/me")
    assert response.status_code == 404


def test_read_requires_authentication(client):
    assert client.get("/involve/subcommittee/me").status_code == 401


def test_edit_while_submitted_updates_fields(
    client, client_login, open_subcommittee_deadline, application_payload
):
    client.post("/involve/subcommittee", json=application_payload)
    updated = {
        **application_payload,
        "first_choice": "Finance",
        "second_choice": None,
        "motivation": "I have relevant experience and can contribute reliably.",
    }
    response = client.put("/involve/subcommittee/me", json=updated)
    assert response.status_code == 200
    assert response.json()["first_choice"] == "Finance"
    assert response.json()["second_choice"] is None


def test_edit_after_status_change_returns_conflict(
    client, client_login, engine, open_subcommittee_deadline, application_payload
):
    client.post("/involve/subcommittee", json=application_payload)
    with Session(engine) as session:
        application = session.exec(select(SubcommitteeApplication)).first()
        application.status = "under_review"
        session.add(application)
        session.commit()

    response = client.put("/involve/subcommittee/me", json=application_payload)
    assert response.status_code == 409


def test_edit_requires_authentication(client, application_payload):
    assert client.put("/involve/subcommittee/me", json=application_payload).status_code == 401


def test_closed_deadline_blocks_create_and_edit(
    client, client_login, engine, monkeypatch, application_payload
):
    from app.routes import involve

    with Session(engine) as session:
        session.add(
            EventDeadline(
                key="subcommittee",
                label="Subcommittee submissions",
                deadline_at=datetime(2026, 1, 1, tzinfo=UTC),
            )
        )
        session.commit()
    monkeypatch.setattr(involve, "now", lambda: datetime(2026, 1, 2, tzinfo=UTC))

    created = client.post("/involve/subcommittee", json=application_payload)
    assert created.status_code == 403
    assert created.json()["detail"] == "Submissions closed"
    assert client.put("/involve/subcommittee/me", json=application_payload).status_code == 403


def test_user_cannot_read_or_edit_another_users_application(
    client,
    client_login,
    other_alumna,
    open_subcommittee_deadline,
    application_payload,
):
    client.post(
        "/auth/login",
        json={"email": other_alumna["email"], "password": other_alumna["password"]},
    )
    created = client.post("/involve/subcommittee", json=application_payload)
    assert created.status_code == 201
    client.post(
        "/auth/login",
        json={"email": "ayesha@example.com", "password": "secret123"},
    )
    response = client.get("/involve/subcommittee/me")
    assert response.status_code == 404
    assert client.put("/involve/subcommittee/me", json=application_payload).status_code == 404

