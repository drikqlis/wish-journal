import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from app.content import get_post, get_posts, load_posts, parse_frontmatter


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
