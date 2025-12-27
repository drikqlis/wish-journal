import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from app.content import (
    get_footer_messages,
    get_post,
    get_posts,
    load_footer_messages,
    load_posts,
    parse_frontmatter,
)


def test_parse_frontmatter_with_valid_frontmatter():
    content = """---
title: Test Post
date: 2024-01-15
author: Jan
---

This is the content.
"""
    frontmatter, body = parse_frontmatter(content)

    assert frontmatter["title"] == "Test Post"
    assert frontmatter["author"] == "Jan"
    assert "This is the content" in body


def test_parse_frontmatter_no_frontmatter():
    content = "Just plain content without frontmatter."
    frontmatter, body = parse_frontmatter(content)

    assert frontmatter == {}
    assert body == content


def test_parse_frontmatter_empty_frontmatter():
    content = """---
---

Content after empty frontmatter.
"""
    frontmatter, body = parse_frontmatter(content)

    assert frontmatter == {}
    assert "Content after empty frontmatter" in body


def test_get_posts(app):
    with app.app_context():
        posts = get_posts()
        assert len(posts) == 1
        assert posts[0].slug == "test-post"
        assert posts[0].title == "Testowy wpis"
        assert posts[0].author == "Tester"


def test_get_post_existing(app):
    with app.app_context():
        post = get_post("test-post")
        assert post is not None
        assert post.title == "Testowy wpis"
        assert "testowa tresc" in post.content_html


def test_get_post_nonexistent(app):
    with app.app_context():
        post = get_post("nonexistent-post")
        assert post is None


def test_posts_sorted_by_date(app):
    content_path = app.config["CONTENT_PATH"]
    posts_dir = Path(content_path) / "posts"

    (posts_dir / "older-post.md").write_text(
        """---
title: "Starszy wpis"
date: 2023-01-01
author: "Autor"
---

Starszy wpis.
""",
        encoding="utf-8",
    )

    (posts_dir / "newer-post.md").write_text(
        """---
title: "Nowszy wpis"
date: 2025-06-15
author: "Autor"
---

Nowszy wpis.
""",
        encoding="utf-8",
    )

    with app.app_context():
        load_posts()
        posts = get_posts()

        assert len(posts) == 3
        assert posts[0].slug == "newer-post"
        assert posts[-1].slug == "older-post"


def test_load_footer_messages_with_valid_file(app):
    content_path = app.config["CONTENT_PATH"]
    other_dir = Path(content_path) / "other"
    other_dir.mkdir(exist_ok=True)

    footer_file = other_dir / "footer-messages.yaml"
    footer_file.write_text(
        """messages:
  - Test message 1
  - Test message 2
  - Test message 3
""",
        encoding="utf-8",
    )

    with app.app_context():
        load_footer_messages()
        messages = get_footer_messages()

        assert len(messages) == 3
        assert "Test message 1" in messages
        assert "Test message 2" in messages
        assert "Test message 3" in messages


def test_load_footer_messages_file_not_exists(app):
    with app.app_context():
        load_footer_messages()
        messages = get_footer_messages()

        assert len(messages) == 1
        assert messages[0] == "Nie napalaj się na zbyt wiele"


def test_load_footer_messages_empty_file(app):
    content_path = app.config["CONTENT_PATH"]
    other_dir = Path(content_path) / "other"
    other_dir.mkdir(exist_ok=True)

    footer_file = other_dir / "footer-messages.yaml"
    footer_file.write_text("", encoding="utf-8")

    with app.app_context():
        load_footer_messages()
        messages = get_footer_messages()

        assert len(messages) == 1
        assert messages[0] == "Nie napalaj się na zbyt wiele"


def test_load_footer_messages_invalid_yaml(app):
    content_path = app.config["CONTENT_PATH"]
    other_dir = Path(content_path) / "other"
    other_dir.mkdir(exist_ok=True)

    footer_file = other_dir / "footer-messages.yaml"
    footer_file.write_text(
        """messages:
  - Test message 1
  this is invalid yaml [[[
""",
        encoding="utf-8",
    )

    with app.app_context():
        load_footer_messages()
        messages = get_footer_messages()

        assert len(messages) == 1
        assert messages[0] == "Nie napalaj się na zbyt wiele"


def test_load_footer_messages_no_messages_key(app):
    content_path = app.config["CONTENT_PATH"]
    other_dir = Path(content_path) / "other"
    other_dir.mkdir(exist_ok=True)

    footer_file = other_dir / "footer-messages.yaml"
    footer_file.write_text(
        """some_other_key:
  - Test message 1
""",
        encoding="utf-8",
    )

    with app.app_context():
        load_footer_messages()
        messages = get_footer_messages()

        assert len(messages) == 1
        assert messages[0] == "Nie napalaj się na zbyt wiele"


def test_get_footer_messages_returns_copy(app):
    content_path = app.config["CONTENT_PATH"]
    other_dir = Path(content_path) / "other"
    other_dir.mkdir(exist_ok=True)

    footer_file = other_dir / "footer-messages.yaml"
    footer_file.write_text(
        """messages:
  - Message 1
  - Message 2
""",
        encoding="utf-8",
    )

    with app.app_context():
        load_footer_messages()
        messages1 = get_footer_messages()
        messages2 = get_footer_messages()

        # Should return a copy, not the same list
        assert messages1 is not messages2
        assert messages1 == messages2
