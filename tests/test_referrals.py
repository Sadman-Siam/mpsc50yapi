from uuid import UUID

from sqlmodel import Session, select

from app.models import Alumna, AlumniProfile
from app.services.referrals import counts_as_referral


def _register(client, payload, email, **extra):
    return client.post(
        "/auth/register",
        json={**payload, "email": email, "reg_code": email.split("@")[0], **extra},
    )


def _confirm(client, body, admin_headers):
    client.patch(
        f"/admin/alumnae/{body['uuid']}/status?new_status=confirmed",
        headers=admin_headers,
    )


def test_registration_records_referrer_and_rejects_invalid_or_self(
    client, registration_payload, engine
):
    referrer = _register(client, registration_payload, "referrer@example.com").json()
    code = referrer["profile"]["reg_code"]
    referred = _register(
        client, registration_payload, "referred@example.com", referrer=code
    )
    assert referred.status_code == 201

    with Session(engine) as session:
        referred_profile = session.exec(
            select(AlumniProfile).where(
                AlumniProfile.alumna_uuid == UUID(referred.json()["uuid"])
            )
        ).one()
        assert referred_profile.referred_by_alumna_uuid == referrer["uuid"]

    invalid = _register(
        client, registration_payload, "invalid@example.com", referrer="NO-SUCH-CODE"
    )
    assert invalid.status_code == 422
    self_referral = _register(
        client,
        registration_payload,
        "self@example.com",
        reg_code="SELF",
        referrer="SELF",
    )
    assert self_referral.status_code == 422


def test_counting_rule_requires_confirmed_account(
    client, registration_payload, admin_headers, engine
):
    referrer = _register(client, registration_payload, "referrer@example.com").json()
    referred = _register(
        client,
        registration_payload,
        "referred@example.com",
        referrer=referrer["profile"]["reg_code"],
    ).json()
    with Session(engine) as session:
        referred_alumna = session.get(Alumna, UUID(referred["uuid"]))
        assert referred_alumna is not None
        assert counts_as_referral(referred_alumna) is False
        referred_alumna.status = "confirmed"
        assert counts_as_referral(referred_alumna) is True
    _confirm(client, referrer, admin_headers)
    client.post("/auth/login", json={"email": "referrer@example.com", "password": "secret123"})
    personal = client.get("/involve/referrals/me")
    assert personal.status_code == 200
    assert personal.json()["referral_count"] == 0
    _confirm(client, referred, admin_headers)
    assert client.get("/involve/referrals/me").json()["referral_count"] == 1


def test_referrals_require_auth_and_hide_contact_details(client, registration_payload, admin_headers):
    assert client.get("/involve/referrals/me").status_code == 401
    referrer = _register(client, registration_payload, "referrer@example.com").json()
    referred = _register(
        client,
        registration_payload,
        "referred@example.com",
        referrer=referrer["profile"]["reg_code"],
    ).json()
    _confirm(client, referrer, admin_headers)
    _confirm(client, referred, admin_headers)
    client.post("/auth/login", json={"email": "referrer@example.com", "password": "secret123"})
    body = client.get("/involve/referrals/me").json()
    assert body["referral_count"] == 1
    assert body["referrals"][0]["full_name"] == referred["full_name"]
    assert "email" not in str(body).lower()
    assert "phone" not in str(body).lower()


def test_admin_leaderboard_uses_earliest_qualifying_referral_as_tiebreak(
    client, registration_payload, admin_headers
):
    first = _register(client, registration_payload, "first@example.com").json()
    second = _register(client, registration_payload, "second@example.com").json()
    _register(client, registration_payload, "first-ref@example.com", referrer=first["profile"]["reg_code"])
    _register(client, registration_payload, "second-ref@example.com", referrer=second["profile"]["reg_code"])
    for body in (first, second):
        _confirm(client, body, admin_headers)
    for email in ("first-ref@example.com", "second-ref@example.com"):
        found = client.get("/admin/alumnae", headers=admin_headers).json()
        account = next(row for row in found if row["email"] == email)
        _confirm(client, account, admin_headers)
    leaderboard = client.get("/admin/referrals", headers=admin_headers)
    assert leaderboard.status_code == 200
    qualifying = [row for row in leaderboard.json() if row["referral_count"] == 1]
    assert qualifying[0]["alumna_uuid"] == first["uuid"]
    assert client.get("/admin/referrals").status_code == 401
