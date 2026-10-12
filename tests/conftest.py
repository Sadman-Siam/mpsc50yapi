import os

# Settings are instantiated at import time, so the environment must be primed
# before anything from `app` is imported.
os.environ.setdefault("DATABASE_URI", "sqlite://")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret")
os.environ.setdefault("JWT_PUBLIC_KEY", "test-secret")
os.environ.setdefault("JWT_ALGORITHM", "HS256")
os.environ.setdefault("ACCESS_TOKEN_NAME", "mpsc_access_token")
os.environ.setdefault("ADMIN_SECRET", "test-admin-secret")
os.environ.setdefault("COOKIE_DOMAIN", "")
os.environ.setdefault("FRONTEND_URL", "http://localhost:3000")
os.environ.setdefault("DEV_MODE", "1")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app import models  # noqa: F401  (registers tables on SQLModel.metadata)
from app.database import get_database_session
from app.main_app import create_app


@pytest.fixture
def engine():
    # StaticPool is required: an in-memory SQLite database lives inside the
    # connection, so every new connection would otherwise get an empty DB.
    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(test_engine)
    yield test_engine
    test_engine.dispose()


@pytest.fixture
def client(engine):
    app = create_app(create_tables=False)

    def override_session():
        with Session(bind=engine) as session:
            yield session

    app.dependency_overrides[get_database_session] = override_session

    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def admin_headers():
    return {"X-Admin-Secret": "test-admin-secret"}


@pytest.fixture
def registration_payload():
    return {
        "full_name": "Ayesha Rahman",
        "email": "ayesha@example.com",
        "phone_number": "01712345678",
        "password": "secret123",
        "batch_year": 2010,
        "tee_shirt_size": "M",
    }


@pytest.fixture
def confirmed_client(client, registration_payload, admin_headers):
    """Registers an alumna and approves her, mirroring the real approval flow."""
    body = client.post("/auth/register", json=registration_payload).json()
    client.patch(
        f"/admin/alumnae/{body['uuid']}/status",
        params={"new_status": "confirmed"},
        headers=admin_headers,
    )
    return body


@pytest.fixture
def client_login(client, confirmed_client):
    """Logs the confirmed alumna in on the shared `client` session."""
    response = client.post(
        "/auth/login",
        json={"email": "ayesha@example.com", "password": "secret123"},
    )
    assert response.status_code == 200, "fixture login failed"
    return confirmed_client