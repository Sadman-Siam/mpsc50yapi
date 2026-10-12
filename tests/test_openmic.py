from datetime import UTC, datetime, timedelta

import pytest
from sqlmodel import Session

from app.models import EventDeadline, OpenMicEntry


@pytest.fixture
def open_openmic_deadline(engine):
    with Session(engine) as session:
        session.add(EventDeadline(
            key="openmic", label="Open mic submissions",
            deadline_at=datetime.now(UTC) + timedelta(days=1),
        ))
        session.commit()


@pytest.fixture
def openmic_payload():
    return {
        "performance_type": "poet",
        "title_or_description": "A poem for our school",
        "duration_minutes": 5,
        "needs_equipment_or_accompaniment": False,
        "equipment_notes": None,
        "performance_link": "https://example.com/performance",
    }


@pytest.fixture
def other_confirmed_alumna(client, admin_headers, registration_payload):
    payload = {**registration_payload, "email": "other-openmic@example.com"}
    body = client.post("/auth/register", json=payload).json()
    client.patch(
        f"/admin/alumnae/{body['uuid']}/status",
        params={"new_status": "confirmed"},
        headers=admin_headers,
    )
    return payload


def test_openmic_submit_read_edit_delete(client, client_login, open_openmic_deadline, openmic_payload):
    created = client.post("/involve/openmic", json=openmic_payload)
    assert created.status_code == 201
    body = created.json()
    assert body["status"] == "submitted"
    assert body["admin_note"] is None
    assert body["scheduled_slot"] is None
    assert "alumna_uuid" not in body

    own = client.get("/involve/openmic/me")
    assert own.status_code == 200
    assert len(own.json()) == 1
    updated = client.put(f"/involve/openmic/{body['uuid']}", json={**openmic_payload, "duration_minutes": 10})
    assert updated.status_code == 200
    assert updated.json()["duration_minutes"] == 10
    assert client.delete(f"/involve/openmic/{body['uuid']}").status_code == 204
    assert client.get("/involve/openmic/me").json() == []


def test_openmic_requires_auth(client, openmic_payload):
    assert client.post("/involve/openmic", json=openmic_payload).status_code == 401
    assert client.get("/involve/openmic/me").status_code == 401
    assert client.put("/involve/openmic/00000000-0000-0000-0000-000000000001", json=openmic_payload).status_code == 401
    assert client.delete("/involve/openmic/00000000-0000-0000-0000-000000000001").status_code == 401


@pytest.mark.parametrize("changes", [
    {"performance_type": "comedian"},
    {"title_or_description": " "},
    {"duration_minutes": 0},
    {"duration_minutes": 11},
    {"duration_minutes": 1.5},
    {"performance_link": "ftp://example.com/file"},
])
def test_openmic_validation(client, client_login, open_openmic_deadline, openmic_payload, changes):
    assert client.post("/involve/openmic", json={**openmic_payload, **changes}).status_code == 422


def test_openmic_entry_limit(client, client_login, open_openmic_deadline, openmic_payload):
    assert client.post("/involve/openmic", json=openmic_payload).status_code == 201
    assert client.post("/involve/openmic", json=openmic_payload).status_code == 201
    assert client.post("/involve/openmic", json=openmic_payload).status_code == 409


def test_openmic_duration_limit_is_configurable(
    client, client_login, open_openmic_deadline, openmic_payload, monkeypatch
):
    from app.settings import settings

    monkeypatch.setattr(settings, "openmic_max_duration_minutes", 12)
    assert client.post(
        "/involve/openmic", json={**openmic_payload, "duration_minutes": 12}
    ).status_code == 201
    assert client.post(
        "/involve/openmic", json={**openmic_payload, "duration_minutes": 13}
    ).status_code == 422


def test_closed_openmic_deadline_blocks_submit_edit_and_delete(
    client, client_login, engine, monkeypatch, openmic_payload
):
    from app.routes import involve

    with Session(engine) as session:
        session.add(EventDeadline(
            key="openmic", label="Open mic submissions", deadline_at=datetime(2026, 1, 1, tzinfo=UTC)
        ))
        entry = OpenMicEntry(
            alumna_uuid=client_login["uuid"], **openmic_payload
        )
        session.add(entry)
        session.commit()
        entry_id = entry.uuid
    monkeypatch.setattr(involve, "now", lambda: datetime(2026, 1, 2, tzinfo=UTC))
    assert client.post("/involve/openmic", json=openmic_payload).status_code == 403
    assert client.put(f"/involve/openmic/{entry_id}", json=openmic_payload).status_code == 403
    assert client.delete(f"/involve/openmic/{entry_id}").status_code == 403


def test_openmic_entries_are_scoped_to_owner(
    client, client_login, other_confirmed_alumna, open_openmic_deadline, openmic_payload
):
    created = client.post("/involve/openmic", json=openmic_payload).json()
    client.post("/auth/login", json={"email": other_confirmed_alumna["email"], "password": other_confirmed_alumna["password"]})
    assert client.get("/involve/openmic/me").json() == []
    assert client.put(f"/involve/openmic/{created['uuid']}", json=openmic_payload).status_code == 404
    assert client.delete(f"/involve/openmic/{created['uuid']}").status_code == 404
