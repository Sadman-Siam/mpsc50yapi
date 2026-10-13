from datetime import UTC, datetime, timedelta

import pytest
from sqlmodel import Session, select

from app.models import EventDeadline, StallApplication


@pytest.fixture
def open_stall_deadline(engine):
    with Session(engine) as session:
        session.add(
            EventDeadline(
                key="stall",
                label="Stall submissions",
                deadline_at=datetime.now(UTC) + timedelta(days=1),
            )
        )
        session.commit()


@pytest.fixture
def stall_payload():
    return {
        "stall_name": "Ayesha's Kitchen",
        "category": "food",
        "description": "Homemade snacks and traditional treats.",
        "products": ["samosa", "pitha"],
        "space_needs": "One 3m table",
        "power_needs": "One standard outlet",
        "number_of_helpers": 2,
        "contact_phone": "01712345678",
        "website_or_social_link": "https://example.com/ayesha",
    }


def test_create_stall_application(client, client_login, open_stall_deadline, stall_payload):
    response = client.post("/involve/stall", json=stall_payload)
    assert response.status_code == 201
    body = response.json()
    assert body["stall_name"] == "Ayesha's Kitchen"
    assert body["products"] == ["samosa", "pitha"]
    assert body["status"] == "applied"
    assert body["stall_fee_status"] == "pending"
    assert body["admin_note"] is None
    assert "alumna_uuid" not in body


def test_duplicate_stall_application_returns_conflict(
    client, client_login, open_stall_deadline, stall_payload
):
    assert client.post("/involve/stall", json=stall_payload).status_code == 201
    assert client.post("/involve/stall", json=stall_payload).status_code == 409


@pytest.mark.parametrize(
    "changes",
    [
        {"category": "invalid"},
        {"stall_name": " "},
        {"products": [""]},
        {"number_of_helpers": -1},
        {"contact_phone": "x"},
        {"website_or_social_link": "not-a-url"},
    ],
)
def test_invalid_stall_application_returns_validation_error(
    client, client_login, open_stall_deadline, stall_payload, changes
):
    response = client.post("/involve/stall", json={**stall_payload, **changes})
    assert response.status_code == 422


def test_stall_routes_require_authentication(client, stall_payload):
    assert client.post("/involve/stall", json=stall_payload).status_code == 401
    assert client.get("/involve/stall/me").status_code == 401
    assert client.put("/involve/stall/me", json=stall_payload).status_code == 401


def test_read_update_own_stall_application(
    client, client_login, open_stall_deadline, stall_payload
):
    client.post("/involve/stall", json=stall_payload)
    read = client.get("/involve/stall/me")
    assert read.status_code == 200
    assert read.json()["stall_name"] == stall_payload["stall_name"]
    updated_payload = {**stall_payload, "stall_name": "Updated kitchen"}
    updated = client.put("/involve/stall/me", json=updated_payload)
    assert updated.status_code == 200
    assert updated.json()["stall_name"] == "Updated kitchen"


def test_read_missing_stall_application_returns_not_found(client, client_login):
    assert client.get("/involve/stall/me").status_code == 404


def test_approved_stall_application_cannot_be_edited(
    client, client_login, engine, open_stall_deadline, stall_payload
):
    client.post("/involve/stall", json=stall_payload)
    with Session(engine) as session:
        application = session.exec(select(StallApplication)).one()
        application.status = "approved"
        session.add(application)
        session.commit()
    response = client.put(
        "/involve/stall/me", json={**stall_payload, "stall_name": "Changed"}
    )
    assert response.status_code == 409


def test_closed_stall_deadline_blocks_create_and_edit(
    client, client_login, engine, monkeypatch, stall_payload
):
    from app.routes import involve

    with Session(engine) as session:
        session.add(
            EventDeadline(
                key="stall",
                label="Stall submissions",
                deadline_at=datetime(2026, 1, 1, tzinfo=UTC),
            )
        )
        session.commit()
    monkeypatch.setattr(involve, "now", lambda: datetime(2026, 1, 2, tzinfo=UTC))
    assert client.post("/involve/stall", json=stall_payload).status_code == 403
    assert client.put("/involve/stall/me", json=stall_payload).status_code == 403


def test_alumna_cannot_read_another_users_stall_application(
    client, client_login, registration_payload, admin_headers, open_stall_deadline, stall_payload
):
    other = {**registration_payload, "email": "other@example.com"}
    other_body = client.post("/auth/register", json=other).json()
    client.patch(
        f"/admin/alumnae/{other_body['uuid']}/status",
        params={"new_status": "confirmed"},
        headers=admin_headers,
    )
    client.post("/involve/stall", json=stall_payload)
    client.post("/auth/logout")
    client.post(
        "/auth/login", json={"email": other["email"], "password": other["password"]}
    )
    assert client.get("/involve/stall/me").status_code == 404
    assert client.put("/involve/stall/me", json=stall_payload).status_code == 404

