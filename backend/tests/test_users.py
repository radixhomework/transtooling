def test_list_users_requires_admin(client):
    response = client.get("/api/users")
    assert response.status_code == 401


def test_admin_can_list_users(client, admin_headers):
    response = client.get("/api/users", headers=admin_headers)
    assert response.status_code == 200
    logins = [u["login"] for u in response.json()]
    assert "admin" in logins


def test_admin_can_create_user(client, admin_headers):
    response = client.post(
        "/api/users",
        json={"login": "alice", "password": "AlicePass123", "role": "user"},
        headers=admin_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["login"] == "alice"
    assert data["role"] == "user"
    assert data["is_active"] is True


def test_create_user_duplicate_email(client, admin_headers):
    client.post(
        "/api/users",
        json={"login": "bob", "password": "BobPass1234", "role": "user"},
        headers=admin_headers,
    )
    response = client.post(
        "/api/users",
        json={"login": "bob", "password": "BobPass1234", "role": "user"},
        headers=admin_headers,
    )
    assert response.status_code == 400


def test_create_user_weak_password_rejected(client, admin_headers):
    response = client.post(
        "/api/users",
        json={"login": "weak", "password": "weak", "role": "user"},
        headers=admin_headers,
    )
    assert response.status_code == 422


def test_regular_user_cannot_create_user(client, admin_headers):
    # Create a non-admin user then log in with that account
    client.post(
        "/api/users",
        json={"login": "regular", "password": "RegularPass1", "role": "user"},
        headers=admin_headers,
    )
    login_response = client.post(
        "/api/auth/login",
        json={"login": "regular", "password": "RegularPass1"},
    )
    user_token = login_response.json()["access_token"]
    user_headers = {"Authorization": f"Bearer {user_token}"}

    response = client.post(
        "/api/users",
        json={"login": "hacker", "password": "HackerPass1", "role": "admin"},
        headers=user_headers,
    )
    assert response.status_code == 403


def test_admin_can_deactivate_user(client, admin_headers):
    create_response = client.post(
        "/api/users",
        json={"login": "todeactivate", "password": "DeactPass1", "role": "user"},
        headers=admin_headers,
    )
    user_id = create_response.json()["id"]

    response = client.patch(
        f"/api/users/{user_id}",
        json={"is_active": False},
        headers=admin_headers,
    )
    assert response.status_code == 200
    assert response.json()["is_active"] is False

    # The disabled user can no longer log in
    login_response = client.post(
        "/api/auth/login",
        json={"login": "todeactivate", "password": "DeactPass1"},
    )
    assert login_response.status_code == 403


def test_admin_can_reset_user_password(client, admin_headers):
    create_response = client.post(
        "/api/users",
        json={"login": "resetme", "password": "OldPass1234", "role": "user"},
        headers=admin_headers,
    )
    user_id = create_response.json()["id"]

    response = client.post(
        f"/api/users/{user_id}/reset-password",
        json={"new_password": "NewPass1234"},
        headers=admin_headers,
    )
    assert response.status_code == 204

    login_response = client.post(
        "/api/auth/login",
        json={"login": "resetme", "password": "NewPass1234"},
    )
    assert login_response.status_code == 200


def test_admin_can_delete_user(client, admin_headers):
    create_response = client.post(
        "/api/users",
        json={"login": "todelete", "password": "DeletePass1", "role": "user"},
        headers=admin_headers,
    )
    user_id = create_response.json()["id"]

    response = client.delete(f"/api/users/{user_id}", headers=admin_headers)
    assert response.status_code == 204

    get_response = client.get("/api/users", headers=admin_headers)
    logins = [u["login"] for u in get_response.json()]
    assert "todelete" not in logins


def test_admin_cannot_delete_self(client, admin_headers):
    me_response = client.get("/api/users/me", headers=admin_headers)
    admin_id = me_response.json()["id"]

    response = client.delete(f"/api/users/{admin_id}", headers=admin_headers)
    assert response.status_code == 400


def test_update_nonexistent_user_returns_404(client, admin_headers):
    response = client.patch(
        "/api/users/999999",
        json={"is_active": False},
        headers=admin_headers,
    )
    assert response.status_code == 404
