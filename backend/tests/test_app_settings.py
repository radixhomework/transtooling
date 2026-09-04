def test_get_settings_requires_admin(client):
    response = client.get("/api/admin/settings")
    assert response.status_code == 401


def test_admin_can_get_settings(client, admin_headers):
    response = client.get("/api/admin/settings", headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert "max_file_size_mb" in data
    assert "max_duration_min" in data


def test_admin_can_update_max_file_size(client, admin_headers):
    response = client.patch(
        "/api/admin/settings",
        json={"max_file_size_mb": 150},
        headers=admin_headers,
    )
    assert response.status_code == 200
    assert response.json()["max_file_size_mb"] == 150

    # Restore a sensible default so later tests are not affected.
    client.patch(
        "/api/admin/settings",
        json={"max_file_size_mb": 200},
        headers=admin_headers,
    )


def test_update_settings_rejects_negative_values(client, admin_headers):
    response = client.patch(
        "/api/admin/settings",
        json={"max_file_size_mb": -10},
        headers=admin_headers,
    )
    assert response.status_code == 400


def test_regular_user_cannot_update_settings(client, admin_headers):
    client.post(
        "/api/users",
        json={"login": "settingsuser", "password": "SettingsPass1", "role": "user"},
        headers=admin_headers,
    )
    login_resp = client.post(
        "/api/auth/login",
        json={"login": "settingsuser", "password": "SettingsPass1"},
    )
    user_headers = {"Authorization": f"Bearer {login_resp.json()['access_token']}"}

    response = client.patch(
        "/api/admin/settings",
        json={"max_file_size_mb": 999},
        headers=user_headers,
    )
    assert response.status_code == 403
