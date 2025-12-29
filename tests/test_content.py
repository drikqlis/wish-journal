import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from app.content import (
    get_footer_messages,
    get_media_path,
    get_post,
    get_posts,
    get_script_path,
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


def test_get_script_path_valid(app, tmp_path):
    """Test get_script_path with valid script."""
    content_path = tmp_path / "content"
    scripts_path = content_path / "scripts"
    scripts_path.mkdir(parents=True)

    script_file = scripts_path / "test.py"
    script_file.write_text('print("test")')

    app.config["CONTENT_PATH"] = str(content_path)

    with app.app_context():
        result = get_script_path("test.py")
        assert result is not None
        assert result.name == "test.py"


def test_get_script_path_subdirectory(app, tmp_path):
    """Test get_script_path with script in subdirectory."""
    content_path = tmp_path / "content"
    examples_path = content_path / "scripts" / "examples"
    examples_path.mkdir(parents=True)

    script_file = examples_path / "hello.py"
    script_file.write_text('print("hello")')

    app.config["CONTENT_PATH"] = str(content_path)

    with app.app_context():
        result = get_script_path("examples/hello.py")
        assert result is not None
        assert result.name == "hello.py"


def test_get_script_path_nonexistent(app, tmp_path):
    """Test get_script_path with nonexistent script."""
    content_path = tmp_path / "content"
    content_path.mkdir(parents=True)

    app.config["CONTENT_PATH"] = str(content_path)

    with app.app_context():
        result = get_script_path("nonexistent.py")
        assert result is None


def test_get_script_path_not_python(app, tmp_path):
    """Test get_script_path rejects non-Python files."""
    content_path = tmp_path / "content"
    scripts_path = content_path / "scripts"
    scripts_path.mkdir(parents=True)

    script_file = scripts_path / "test.sh"
    script_file.write_text('echo "test"')

    app.config["CONTENT_PATH"] = str(content_path)

    with app.app_context():
        result = get_script_path("test.sh")
        assert result is None


def test_get_script_path_directory_traversal(app, tmp_path):
    """Test get_script_path blocks directory traversal."""
    content_path = tmp_path / "content"
    scripts_path = content_path / "scripts"
    scripts_path.mkdir(parents=True)

    # Create file outside content directory
    outside_file = tmp_path / "outside.py"
    outside_file.write_text('print("outside")')

    app.config["CONTENT_PATH"] = str(content_path)

    with app.app_context():
        # Try to access file outside content directory
        result = get_script_path("../../outside.py")
        assert result is None


def test_get_script_path_is_directory(app, tmp_path):
    """Test get_script_path rejects directories."""
    content_path = tmp_path / "content"
    scripts_path = content_path / "scripts"
    examples_path = scripts_path / "examples"
    examples_path.mkdir(parents=True)

    app.config["CONTENT_PATH"] = str(content_path)

    with app.app_context():
        result = get_script_path("examples")
        assert result is None


def test_python_script_block_processor(app, tmp_path):
    """Test markdown processing of python-script blocks."""
    # Create content directory with script
    content_path = tmp_path / "content"
    scripts_path = content_path / "scripts"
    scripts_path.mkdir(parents=True)

    script_file = scripts_path / "test.py"
    script_file.write_text('print("test")')

    # Create post with python-script block
    posts_path = content_path / "posts"
    posts_path.mkdir()

    post_file = posts_path / "test.md"
    post_file.write_text("""---
title: Test Script
date: 2025-01-15
author: Test
---

:::python-script path="test.py" title="Test Script"
:::
""")

    app.config["CONTENT_PATH"] = str(content_path)

    with app.app_context():
        load_posts()
        post = get_post("test")

        assert post is not None
        assert 'script-wrapper' in post.content_html
        assert 'data-script-path="test.py"' in post.content_html
        assert 'Test Script' in post.content_html
        assert 'script-terminal' in post.content_html
        assert 'script-output' in post.content_html
        assert 'script-input' in post.content_html
        assert 'script-controls' in post.content_html
        assert 'script-start' in post.content_html


def test_python_script_block_processor_default_title(app, tmp_path):
    """Test python-script block uses filename as default title."""
    content_path = tmp_path / "content"
    scripts_path = content_path / "scripts"
    scripts_path.mkdir(parents=True)

    script_file = scripts_path / "hello.py"
    script_file.write_text('print("hello")')

    posts_path = content_path / "posts"
    posts_path.mkdir()

    post_file = posts_path / "test.md"
    post_file.write_text("""---
title: Test
date: 2025-01-15
author: Test
---

:::python-script path="hello.py"
:::
""")

    app.config["CONTENT_PATH"] = str(content_path)

    with app.app_context():
        load_posts()
        post = get_post("test")

        assert post is not None
        # Should use filename without extension as title
        assert '>hello<' in post.content_html


def test_python_script_block_processor_invalid_path(app, tmp_path):
    """Test python-script block with invalid path shows error."""
    content_path = tmp_path / "content"
    posts_path = content_path / "posts"
    posts_path.mkdir(parents=True)

    post_file = posts_path / "test.md"
    post_file.write_text("""---
title: Test
date: 2025-01-15
author: Test
---

:::python-script path="nonexistent.py"
:::
""")

    app.config["CONTENT_PATH"] = str(content_path)

    with app.app_context():
        load_posts()
        post = get_post("test")

        assert post is not None
        assert 'script-error' in post.content_html
        assert 'nie znaleziono' in post.content_html.lower()


def test_python_script_block_processor_missing_path(app, tmp_path):
    """Test python-script block without path attribute."""
    content_path = tmp_path / "content"
    posts_path = content_path / "posts"
    posts_path.mkdir(parents=True)

    post_file = posts_path / "test.md"
    post_file.write_text("""---
title: Test
date: 2025-01-15
author: Test
---

:::python-script title="Test"
:::
""")

    app.config["CONTENT_PATH"] = str(content_path)

    with app.app_context():
        load_posts()
        post = get_post("test")

        # Should not render script block without path
        assert post is not None
        assert 'script-wrapper' not in post.content_html
