import pytest


def test_login_page_renders(client):
    response = client.get("/auth/login")
    assert response.status_code == 200
    assert b"Wish Journal" in response.data


def test_login_with_valid_password(client_with_user):
    response = client_with_user.post(
        "/auth/login",
        data={"password": "testpass123"},
        follow_redirects=True,
    )
    assert response.status_code == 200


def test_login_with_invalid_password(client_with_user):
    response = client_with_user.post(
        "/auth/login",
        data={"password": "wrongpassword"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b'login-error' in response.data
    # Verify the error parameter triggers the JavaScript
    response_no_redirect = client_with_user.post(
        "/auth/login",
        data={"password": "wrongpassword"},
    )
    assert response_no_redirect.status_code == 302
    assert "error=1" in response_no_redirect.location


def test_login_redirects_to_index(client_with_user):
    response = client_with_user.post(
        "/auth/login",
        data={"password": "testpass123"},
    )
    assert response.status_code == 302
    assert "/" in response.location


def test_logout(logged_in_client):
    response = logged_in_client.get("/auth/logout")
    assert response.status_code == 302

    response = logged_in_client.get("/")
    assert response.status_code == 302
    assert "/auth/login" in response.location


def test_protected_route_requires_login(client):
    response = client.get("/")
    assert response.status_code == 302
    assert "/auth/login" in response.location


def test_already_logged_in_redirects_from_login(logged_in_client):
    response = logged_in_client.get("/auth/login")
    assert response.status_code == 302
    assert "/" in response.location
