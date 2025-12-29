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


def test_script_stream_requires_auth(client):
    """Test that script streaming endpoint requires authentication."""
    response = client.get("/script/stream?path=test.py")
    assert response.status_code == 302
    assert "/auth/login" in response.location


def test_script_stream_invalid_path(logged_in_client):
    """Test script streaming with invalid/nonexistent script path."""
    response = logged_in_client.get("/script/stream?path=nonexistent.py")
    assert response.status_code == 200
    assert response.mimetype == "text/event-stream"
    # Should send error event
    assert b"event: error" in response.data
    assert b"Nie znaleziono" in response.data


def test_script_stream_valid_path(logged_in_client, app_with_user):
    """Test script streaming with valid script creates session."""
    content_path = app_with_user.config["CONTENT_PATH"]
    scripts_dir = Path(content_path) / "scripts"
    scripts_dir.mkdir(parents=True, exist_ok=True)

    # Create test script
    script_file = scripts_dir / "test.py"
    script_file.write_text('print("Hello from script")\n')

    response = logged_in_client.get("/script/stream?path=test.py")
    assert response.status_code == 200
    assert response.mimetype == "text/event-stream"
    assert response.headers.get("Cache-Control") == "no-cache"


def test_script_input_requires_auth(client):
    """Test that script input endpoint requires authentication."""
    response = client.post("/script/input", json={"session_id": "test", "text": "input"})
    assert response.status_code == 302
    assert "/auth/login" in response.location


def test_script_input_invalid_json(logged_in_client):
    """Test script input with invalid JSON body."""
    response = logged_in_client.post(
        "/script/input",
        data="not json",
        content_type="text/plain"
    )
    # Flask returns 415 for unsupported media type
    assert response.status_code == 415


def test_script_input_missing_csrf_token(logged_in_client, app_with_user):
    """Test script input without CSRF token."""
    # Create a valid session first so we don't get 500 error for missing session
    from app import script_runner
    from pathlib import Path

    content_path = app_with_user.config["CONTENT_PATH"]
    scripts_dir = Path(content_path) / "scripts"
    scripts_dir.mkdir(parents=True, exist_ok=True)
    script_file = scripts_dir / "test.py"
    script_file.write_text('print("test")')

    with app_with_user.app_context():
        session_id = script_runner.create_session(script_file)
        script_runner.start_execution(session_id)

    # Clear CSRF token from session to test missing token
    with logged_in_client.session_transaction() as sess:
        sess.pop("csrf_token", None)

    response = logged_in_client.post(
        "/script/input",
        json={"session_id": session_id, "text": "input", "csrf_token": "invalid"}
    )
    assert response.status_code == 403
    data = response.get_json()
    assert "error" in data
    assert "token" in data["error"].lower()


def test_script_input_missing_session_id(logged_in_client):
    """Test script input without session_id."""
    logged_in_client.get("/")  # Generate CSRF token
    with logged_in_client.session_transaction() as sess:
        csrf_token = sess.get("csrf_token", "")

    response = logged_in_client.post(
        "/script/input",
        json={"csrf_token": csrf_token, "text": "input"}
    )
    assert response.status_code == 400
    data = response.get_json()
    assert "session_id" in data["error"]


def test_script_input_invalid_session(logged_in_client):
    """Test script input with nonexistent session ID."""
    logged_in_client.get("/")
    with logged_in_client.session_transaction() as sess:
        csrf_token = sess.get("csrf_token", "")

    response = logged_in_client.post(
        "/script/input",
        json={"csrf_token": csrf_token, "session_id": "nonexistent", "text": "input"}
    )
    assert response.status_code == 500
    data = response.get_json()
    assert "error" in data


def test_script_keepalive_requires_auth(client):
    """Test that keepalive endpoint requires authentication."""
    response = client.post("/script/keepalive", json={"session_id": "test"})
    assert response.status_code == 302
    assert "/auth/login" in response.location


def test_script_keepalive_invalid_json(logged_in_client):
    """Test keepalive with invalid JSON body."""
    response = logged_in_client.post(
        "/script/keepalive",
        data="not json",
        content_type="text/plain"
    )
    # Flask returns 415 for unsupported media type
    assert response.status_code == 415


def test_script_keepalive_missing_csrf(logged_in_client, app_with_user):
    """Test keepalive without CSRF token."""
    # Create a valid session first
    from app import script_runner
    from pathlib import Path

    content_path = app_with_user.config["CONTENT_PATH"]
    scripts_dir = Path(content_path) / "scripts"
    scripts_dir.mkdir(parents=True, exist_ok=True)
    script_file = scripts_dir / "test.py"
    script_file.write_text('print("test")')

    with app_with_user.app_context():
        session_id = script_runner.create_session(script_file)

    # Clear CSRF token from session
    with logged_in_client.session_transaction() as sess:
        sess.pop("csrf_token", None)

    response = logged_in_client.post(
        "/script/keepalive",
        json={"session_id": session_id, "csrf_token": "invalid"}
    )
    assert response.status_code == 403
    data = response.get_json()
    assert "error" in data


def test_script_keepalive_missing_session_id(logged_in_client):
    """Test keepalive without session_id."""
    logged_in_client.get("/")
    with logged_in_client.session_transaction() as sess:
        csrf_token = sess.get("csrf_token", "")

    response = logged_in_client.post(
        "/script/keepalive",
        json={"csrf_token": csrf_token}
    )
    assert response.status_code == 400
    data = response.get_json()
    assert "session_id" in data["error"]


def test_script_keepalive_invalid_session(logged_in_client):
    """Test keepalive with nonexistent session."""
    logged_in_client.get("/")
    with logged_in_client.session_transaction() as sess:
        csrf_token = sess.get("csrf_token", "")

    response = logged_in_client.post(
        "/script/keepalive",
        json={"csrf_token": csrf_token, "session_id": "nonexistent"}
    )
    assert response.status_code == 404
    data = response.get_json()
    assert "error" in data


def test_script_stop_requires_auth(client):
    """Test that stop endpoint requires authentication."""
    response = client.post("/script/stop", json={"session_id": "test"})
    assert response.status_code == 302
    assert "/auth/login" in response.location


def test_script_stop_invalid_json(logged_in_client):
    """Test stop with invalid JSON body."""
    response = logged_in_client.post(
        "/script/stop",
        data="not json",
        content_type="text/plain"
    )
    # Flask returns 415 for unsupported media type
    assert response.status_code == 415


def test_script_stop_missing_csrf(logged_in_client, app_with_user):
    """Test stop without CSRF token."""
    # Create a valid session first
    from app import script_runner
    from pathlib import Path

    content_path = app_with_user.config["CONTENT_PATH"]
    scripts_dir = Path(content_path) / "scripts"
    scripts_dir.mkdir(parents=True, exist_ok=True)
    script_file = scripts_dir / "test.py"
    script_file.write_text('print("test")')

    with app_with_user.app_context():
        session_id = script_runner.create_session(script_file)

    # Clear CSRF token from session
    with logged_in_client.session_transaction() as sess:
        sess.pop("csrf_token", None)

    response = logged_in_client.post(
        "/script/stop",
        json={"session_id": session_id, "csrf_token": "invalid"}
    )
    assert response.status_code == 403
    data = response.get_json()
    assert "error" in data


def test_script_stop_missing_session_id(logged_in_client):
    """Test stop without session_id."""
    logged_in_client.get("/")
    with logged_in_client.session_transaction() as sess:
        csrf_token = sess.get("csrf_token", "")

    response = logged_in_client.post(
        "/script/stop",
        json={"csrf_token": csrf_token}
    )
    assert response.status_code == 400
    data = response.get_json()
    assert "session_id" in data["error"]


def test_script_stop_invalid_session(logged_in_client):
    """Test stop with nonexistent session."""
    logged_in_client.get("/")
    with logged_in_client.session_transaction() as sess:
        csrf_token = sess.get("csrf_token", "")

    response = logged_in_client.post(
        "/script/stop",
        json={"csrf_token": csrf_token, "session_id": "nonexistent"}
    )
    assert response.status_code == 404
    data = response.get_json()
    assert "error" in data
