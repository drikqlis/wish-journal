import pytest
from pathlib import Path


def test_index_requires_auth(client):
    response = client.get("/")
    assert response.status_code == 302
    assert "/auth/login" in response.location


def test_index_shows_posts(logged_in_client):
    response = logged_in_client.get("/")
    assert response.status_code == 200
    assert b"Testowy wpis" in response.data


def test_post_detail_page(logged_in_client):
    response = logged_in_client.get("/post/test-post")
    assert response.status_code == 200
    assert b"Testowy wpis" in response.data
    assert b"Tester" in response.data
    assert b"testowa tresc" in response.data


def test_post_not_found(logged_in_client):
    response = logged_in_client.get("/post/nonexistent")
    assert response.status_code == 404


def test_comment_submission(logged_in_client):
    with logged_in_client.session_transaction() as sess:
        csrf_token = sess.get("csrf_token", "")

    if not csrf_token:
        response = logged_in_client.get("/post/test-post")
        with logged_in_client.session_transaction() as sess:
            csrf_token = sess.get("csrf_token", "")

    response = logged_in_client.post(
        "/post/test-post/comment",
        data={"csrf_token": csrf_token, "content": "Testowy komentarz"},
        follow_redirects=False,
    )
    assert response.status_code == 302
    assert "success=1" in response.location


def test_comment_empty_content(logged_in_client):
    logged_in_client.get("/post/test-post")
    with logged_in_client.session_transaction() as sess:
        csrf_token = sess.get("csrf_token", "")

    response = logged_in_client.post(
        "/post/test-post/comment",
        data={"csrf_token": csrf_token, "content": ""},
        follow_redirects=True,
    )
    assert b"Komentarz nie moze byc pusty" in response.data


def test_comment_invalid_csrf(logged_in_client):
    response = logged_in_client.post(
        "/post/test-post/comment",
        data={"csrf_token": "invalid-token", "content": "Test"},
        follow_redirects=True,
    )
    assert b"Nieprawidlowy token" in response.data


def test_media_serving(logged_in_client, app_with_user):
    content_path = app_with_user.config["CONTENT_PATH"]
    media_dir = Path(content_path) / "media"
    test_file = media_dir / "test.txt"
    test_file.write_text("Test content", encoding="utf-8")

    response = logged_in_client.get("/media/test.txt")
    assert response.status_code == 200
    assert b"Test content" in response.data


def test_media_not_found(logged_in_client):
    response = logged_in_client.get("/media/nonexistent.jpg")
    assert response.status_code == 404


def test_media_requires_auth(client):
    response = client.get("/media/test.txt")
    assert response.status_code == 302
    assert "/auth/login" in response.location


def test_footer_messages_in_template_context(app_with_user, logged_in_client):
    content_path = app_with_user.config["CONTENT_PATH"]
    other_dir = Path(content_path) / "other"
    other_dir.mkdir(exist_ok=True)

    footer_file = other_dir / "footer-messages.yaml"
    footer_file.write_text(
        """messages:
  - Custom footer message
  - Another custom message
""",
        encoding="utf-8",
    )

    # Reload footer messages
    from app import content
    with app_with_user.app_context():
        content.load_footer_messages()

    response = logged_in_client.get("/")
    assert response.status_code == 200
    # Footer should contain one of the custom messages
    assert b"Custom footer message" in response.data or b"Another custom message" in response.data
