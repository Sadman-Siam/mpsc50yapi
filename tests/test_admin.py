def test_list_requires_admin_secret(client, registration_payload):
    client.post("/auth/register", json=registration_payload)
    assert client.get("/admin/alumnae").status_code == 401


def test_list_rejects_wrong_admin_secret(client):
    response = client.get("/admin/alumnae", headers={"X-Admin-Secret": "nope"})
    assert response.status_code == 401


def test_list_with_admin_secret(client, registration_payload):
    client.post("/auth/register", json=registration_payload)
    response = client.get("/admin/alumnae", headers={"X-Admin-Secret": "test-admin-secret"})
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_admin_can_see_pending_accounts_that_cannot_log_in(
    client, registration_payload
):
    """Registration creates a pending account; the admin list is the only way
    to see and approve it."""
    client.post("/auth/register", json=registration_payload)

    pending = client.get(
        "/admin/alumnae",
        params={"status": "pending"},
        headers={"X-Admin-Secret": "test-admin-secret"},
    ).json()
    assert len(pending) == 1
    assert pending[0]["status"] == "pending"


def test_status_filter_rejects_unknown_value(client):
    response = client.get(
        "/admin/alumnae",
        params={"status": "bogus"},
        headers={"X-Admin-Secret": "test-admin-secret"},
    )
    assert response.status_code == 422


def test_status_update_unblocks_login(client, registration_payload, admin_headers):
    body = client.post("/auth/register", json=registration_payload).json()

    assert client.post(
        "/auth/login", json={"email": "ayesha@example.com", "password": "secret123"}
    ).status_code == 403

    approved = client.patch(
        f"/admin/alumnae/{body['uuid']}/status",
        params={"new_status": "confirmed"},
        headers=admin_headers,
    )
    assert approved.status_code == 200
    assert approved.json()["status"] == "confirmed"

    assert client.post(
        "/auth/login", json={"email": "ayesha@example.com", "password": "secret123"}
    ).status_code == 200


def test_status_update_requires_secret(client, registration_payload):
    body = client.post("/auth/register", json=registration_payload).json()
    response = client.patch(
        f"/admin/alumnae/{body['uuid']}/status", params={"new_status": "confirmed"}
    )
    assert response.status_code == 401


def test_status_update_rejects_invalid_status(client, registration_payload, admin_headers):
    body = client.post("/auth/register", json=registration_payload).json()
    response = client.patch(
        f"/admin/alumnae/{body['uuid']}/status",
        params={"new_status": "deleted"},
        headers=admin_headers,
    )
    assert response.status_code == 422


def test_status_update_404_for_unknown_uuid(client, admin_headers):
    import uuid

    response = client.patch(
        f"/admin/alumnae/{uuid.uuid4()}/status",
        params={"new_status": "confirmed"},
        headers=admin_headers,
    )
    assert response.status_code == 404


def test_counts_group_by_status(client, registration_payload, admin_headers):
    assert client.get("/admin/alumnae/counts", headers=admin_headers).json() == {
        "pending": 0,
        "confirmed": 0,
        "cancelled": 0,
    }

    first = client.post("/auth/register", json=registration_payload).json()
    client.post(
        "/auth/register", json={**registration_payload, "email": "second@example.com"}
    )
    client.patch(
        f"/admin/alumnae/{first['uuid']}/status",
        params={"new_status": "confirmed"},
        headers=admin_headers,
    )

    counts = client.get("/admin/alumnae/counts", headers=admin_headers).json()
    assert counts == {"pending": 1, "confirmed": 1, "cancelled": 0}


def test_counts_requires_secret(client):
    assert client.get("/admin/alumnae/counts").status_code == 401


def test_admin_list_supports_pagination(client, registration_payload, admin_headers):
    for index in range(5):
        client.post(
            "/auth/register",
            json={**registration_payload, "email": f"user{index}@example.com"},
        )

    page = client.get(
        "/admin/alumnae",
        params={"limit": 2, "offset": 0},
        headers=admin_headers,
    ).json()
    assert len(page) == 2

    second_page = client.get(
        "/admin/alumnae",
        params={"limit": 2, "offset": 2},
        headers=admin_headers,
    ).json()
    assert len(second_page) == 2
    assert page[0]["uuid"] != second_page[0]["uuid"]


def test_admin_list_rejects_out_of_range_limit(client, admin_headers):
    response = client.get(
        "/admin/alumnae", params={"limit": 5000}, headers=admin_headers
    )
    assert response.status_code == 422