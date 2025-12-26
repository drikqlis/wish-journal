import os
import tempfile
from pathlib import Path

import pytest

from app import create_app
from app.models import create_user, init_db




@pytest.fixture
def app():
    db_fd, db_path = tempfile.mkstemp()
    content_dir = tempfile.mkdtemp()

    posts_dir = Path(content_dir) / "posts"
    posts_dir.mkdir()

    media_dir = Path(content_dir) / "media"
    media_dir.mkdir()

    sample_post = posts_dir / "test-post.md"
    sample_post.write_text(
        """---
title: "Testowy wpis"
date: 2024-01-15
author: "Tester"
---

To jest testowa tresc wpisu.
""",
        encoding="utf-8",
    )

    # Clear global posts cache before creating new app
    from app import content
    content._posts_cache = []

    app = create_app(
        {
            "TESTING": True,
            "DATABASE_PATH": db_path,
            "CONTENT_PATH": content_dir,
            "SECRET_KEY": "test-secret-key",
        }
    )

    with app.app_context():
        init_db()
        # Load posts for this app's content directory
        content.load_posts()

    yield app

    # Clean up on teardown
    content.stop_watcher()
    content._posts_cache = []

    os.close(db_fd)
    os.unlink(db_path)

    import shutil
    shutil.rmtree(content_dir)


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def runner(app):
    return app.test_cli_runner()


@pytest.fixture
def app_with_user(app):
    with app.app_context():
        create_user("Jan", "Kowalski", "janek", "testpass123")
    return app


@pytest.fixture
def client_with_user(app_with_user):
    return app_with_user.test_client()


@pytest.fixture
def logged_in_client(app_with_user):
    client = app_with_user.test_client()
    client.post("/auth/login", data={"password": "testpass123"})
    return client
