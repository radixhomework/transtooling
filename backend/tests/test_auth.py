def test_login_success(client):
    response = client.post(
        "/api/auth/login",
        json={"login": "admin", "password": "AdminPass123"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


def test_login_wrong_password(client):
    response = client.post(
        "/api/auth/login",
        json={"login": "admin", "password": "wrong-password"},
    )
    assert response.status_code == 401


def test_login_unknown_user(client):
    response = client.post(
        "/api/auth/login",
        json={"login": "inconnu", "password": "whatever123"},
    )
    assert response.status_code == 401


def test_login_lockout_after_repeated_failures(client):
    login_name = "lockout-test"
    for _ in range(5):
        response = client.post(
            "/api/auth/login",
            json={"login": login_name, "password": "wrong-password"},
        )
        assert response.status_code == 401

    # 6th attempt: must be blocked by the brute-force protection
    response = client.post(
        "/api/auth/login",
        json={"login": login_name, "password": "wrong-password"},
    )
    assert response.status_code == 429


def test_refresh_token_flow(client):
    login_response = client.post(
        "/api/auth/login",
        json={"login": "admin", "password": "AdminPass123"},
    )
    refresh_token = login_response.json()["refresh_token"]

    response = client.post("/api/auth/refresh", json={"refresh_token": refresh_token})
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data


def test_refresh_with_invalid_token(client):
    response = client.post("/api/auth/refresh", json={"refresh_token": "not-a-valid-token"})
    assert response.status_code == 401


def test_get_me_requires_auth(client):
    response = client.get("/api/users/me")
    assert response.status_code == 401


def test_get_me_with_valid_token(client, admin_headers):
    response = client.get("/api/users/me", headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["login"] == "admin"
    assert data["role"] == "admin"


def test_change_password_wrong_current(client, admin_headers):
    response = client.post(
        "/api/auth/change-password",
        json={"current_password": "wrong", "new_password": "NewPass123"},
        headers=admin_headers,
    )
    assert response.status_code == 400


def test_change_password_weak_new_password(client, admin_headers):
    response = client.post(
        "/api/auth/change-password",
        json={"current_password": "AdminPass123", "new_password": "short"},
        headers=admin_headers,
    )
    # Erreur de validation Pydantic (mot de passe trop faible)
    assert response.status_code == 422
