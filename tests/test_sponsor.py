from datetime import UTC, datetime, timedelta

import pytest
from sqlmodel import Session

from app.models import EventDeadline


@pytest.fixture
def open_sponsor_deadline(engine):
    with Session(engine) as session:
        session.add(
            EventDeadline(
                key="sponsor",
                label="Sponsor submissions",
                deadline_at=datetime.now(UTC) + timedelta(days=1),
            )
        )
        session.commit()


@pytest.fixture
def sponsor_payload():
    return {
        "sponsor_type": "company",
        "sponsor_name": "Acme Ltd",
        "contact_person": "Ayesha Rahman",
        "phone": "01712345678",
        "email": "sponsor@example.com",
        "proposed_amount_bdt": 100000,
        "in_kind_description": None,
        "message": "We would like to sponsor the event.",
    }


def test_submit_and_read_own_sponsor_offers(
    client, client_login, open_sponsor_deadline, sponsor_payload
):
    created = client.post("/involve/sponsor", json=sponsor_payload)
    assert created.status_code == 201
    assert created.json()["status"] == "submitted"
    assert created.json()["admin_note"] is None
    assert "alumna_uuid" not in created.json()

    response = client.get("/involve/sponsor/me")
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["sponsor_name"] == "Acme Ltd"


def test_sponsor_routes_require_auth(client, sponsor_payload):
    assert client.post("/involve/sponsor", json=sponsor_payload).status_code == 401
    assert client.get("/involve/sponsor/me").status_code == 401


@pytest.mark.parametrize(
    "changes",
    [
        {"sponsor_type": "other"},
        {"sponsor_name": "  "},
        {"email": "not-an-email"},
        {"proposed_amount_bdt": 0},
        {"proposed_amount_bdt": None},
        {"sponsor_type": "in_kind", "proposed_amount_bdt": None, "in_kind_description": " "},
        {"sponsor_type": "in_kind", "proposed_amount_bdt": 5, "in_kind_description": "Meals"},
    ],
)
def test_invalid_sponsor_data_returns_422(
    client, client_login, open_sponsor_deadline, sponsor_payload, changes
):
    response = client.post("/involve/sponsor", json={**sponsor_payload, **changes})
    assert response.status_code == 422


def test_in_kind_offer_can_omit_amount(client, client_login, open_sponsor_deadline, sponsor_payload):
    payload = {
        **sponsor_payload,
        "sponsor_type": "in_kind",
        "proposed_amount_bdt": None,
        "in_kind_description": "Audio equipment and stage lighting",
    }
    response = client.post("/involve/sponsor", json=payload)
    assert response.status_code == 201
    assert response.json()["proposed_amount_bdt"] is None


def test_offer_limit_is_enforced(client, client_login, open_sponsor_deadline, sponsor_payload):
    for _ in range(3):
        assert client.post("/involve/sponsor", json=sponsor_payload).status_code == 201
    response = client.post("/involve/sponsor", json=sponsor_payload)
    assert response.status_code == 409


def test_closed_deadline_blocks_sponsor_submission(
    client, client_login, engine, monkeypatch, sponsor_payload
):
    from app.routes import involve

    with Session(engine) as session:
        session.add(
            EventDeadline(
                key="sponsor",
                label="Sponsor submissions",
                deadline_at=datetime(2026, 1, 1, tzinfo=UTC),
            )
        )
        session.commit()
    monkeypatch.setattr(involve, "now", lambda: datetime(2026, 1, 2, tzinfo=UTC))
    response = client.post("/involve/sponsor", json=sponsor_payload)
    assert response.status_code == 403
    assert response.json()["detail"] == "Submissions closed"


def test_user_only_reads_own_offers(
    client, client_login, other_alumna, open_sponsor_deadline, sponsor_payload
):
    client.post("/involve/sponsor", json=sponsor_payload)
    client.post(
        "/auth/login",
        json={"email": other_alumna["email"], "password": other_alumna["password"]},
    )
    assert client.get("/involve/sponsor/me").json() == []
