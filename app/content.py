import logging
import os
import re
import threading
import xml.etree.ElementTree as etree
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import markdown
import yaml
from flask import Flask, current_app
from markdown.blockprocessors import BlockProcessor
from markdown.extensions import Extension
from watchdog.events import FileSystemEventHandler
from watchdog.observers.polling import PollingObserver

logger = logging.getLogger(__name__)

_posts_cache: list["Post"] = []
_cache_lock = threading.Lock()
_observer: PollingObserver | None = None
_footer_messages: list[str] = []


class GalleryBlockProcessor(BlockProcessor):
    """Custom markdown processor for image galleries with lightbox support.

    Syntax:
        :::gallery [rows=3] [title="Gallery Title"]
        ![alt text](image_url)
        ...
        :::
    """

    RE_IMAGE = re.compile(r'!\[([^\]]*)\]\(([^\)]+)\)')
    RE_ROWS = re.compile(r'rows=(\d+)')
    RE_TITLE = re.compile(r'title="([^"]*)"')

    def test(self, parent, block):
        # Check if the first line starts with :::gallery
        lines = block.split('\n')
        return lines[0].strip().startswith(':::gallery')

    def run(self, parent, blocks):
        block = blocks.pop(0)
        lines = block.split('\n')

        # Parse first line for options
        first_line = lines.pop(0).strip()

        # Extract rows parameter (default: 3)
        rows_match = self.RE_ROWS.search(first_line)
        rows = int(rows_match.group(1)) if rows_match else 3

        # Extract title parameter
        title_match = self.RE_TITLE.search(first_line)
        title = title_match.group(1) if title_match else None

        # Collect lines until we hit :::
        gallery_lines = []
        for line in lines:
            if line.strip() == ':::':
                break
            gallery_lines.append(line)

        # Create gallery wrapper
        gallery_wrapper = etree.SubElement(parent, 'div')
        gallery_wrapper.set('class', 'gallery-wrapper')

        # Add title if provided
        if title:
            title_div = etree.SubElement(gallery_wrapper, 'div')
            title_div.set('class', 'gallery-title')
            title_div.text = title

        # Create gallery container
        gallery_div = etree.SubElement(gallery_wrapper, 'div')
        gallery_div.set('class', 'image-gallery')
        gallery_div.set('data-rows', str(rows))

        # Parse images from collected content
        content = '\n'.join(gallery_lines)
        for match in self.RE_IMAGE.finditer(content):
            alt_text = match.group(1)
            img_url = match.group(2)

            item_div = etree.SubElement(gallery_div, 'div')
            item_div.set('class', 'gallery-item')

            link = etree.SubElement(item_div, 'a')
            link.set('href', img_url)
            link.set('class', 'glightbox')
            link.set('data-gallery', 'gallery')

            img = etree.SubElement(link, 'img')
            img.set('src', img_url)
            img.set('alt', alt_text)
            img.set('loading', 'lazy')

        return True


class GalleryExtension(Extension):
    """Markdown extension for image galleries."""

    def extendMarkdown(self, md):
        md.parser.blockprocessors.register(
            GalleryBlockProcessor(md.parser), 'gallery', 175
        )


@dataclass
class Post:
    slug: str
    title: str
    date: datetime
    author: str
    content_html: str
    content_raw: str
    excerpt_html: str = ""

    @property
    def excerpt(self) -> str:
        return self.excerpt_html


def parse_frontmatter(content: str) -> tuple[dict, str]:
    pattern = r"^---\s*\n(.*?)\n---\s*\n(.*)$"
    match = re.match(pattern, content, re.DOTALL)

    if match:
        try:
            frontmatter = yaml.safe_load(match.group(1))
            body = match.group(2)
            return frontmatter or {}, body
        except yaml.YAMLError:
            pass

    return {}, content


def strip_media_from_text(text: str) -> str:
    """Remove images, audio, and video from markdown/HTML text."""
    # Remove markdown images: ![alt](url)
    text = re.sub(r'!\[([^\]]*)\]\([^\)]+\)', '', text)

    # Remove HTML img tags (both self-closing and with closing tags)
    text = re.sub(r'<img[^>]*/?>', '', text, flags=re.IGNORECASE)

    # Remove HTML audio tags and their content
    text = re.sub(r'<audio[^>]*>.*?</audio>', '', text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r'<audio[^>]*/>', '', text, flags=re.IGNORECASE)

    # Remove HTML video tags and their content
    text = re.sub(r'<video[^>]*>.*?</video>', '', text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r'<video[^>]*/>', '', text, flags=re.IGNORECASE)

    return text


def load_posts() -> None:
    global _posts_cache

    content_path = current_app.config.get("CONTENT_PATH", "/content")
    posts_dir = Path(content_path) / "posts"

    if not posts_dir.exists():
        logger.warning(f"Posts directory does not exist: {posts_dir}")
        with _cache_lock:
            _posts_cache = []
        return

    posts = []
    md = markdown.Markdown(extensions=["fenced_code", "tables", "nl2br", GalleryExtension()])

    for file_path in posts_dir.glob("*.md"):
        try:
            content = file_path.read_text(encoding="utf-8")
            frontmatter, body = parse_frontmatter(content)

            slug = file_path.stem
            date = frontmatter.get("date", datetime.now())
            if isinstance(date, str):
                date = datetime.fromisoformat(date)

            md.reset()
            content_html = md.convert(body)

            # Create excerpt (first 500 chars of raw, strip media, then render)
            excerpt_raw = strip_media_from_text(body.strip())
            if len(excerpt_raw) > 500:
                excerpt_raw = excerpt_raw[:500].rsplit(" ", 1)[0] + "..."
            md.reset()
            excerpt_html = md.convert(excerpt_raw)

            posts.append(
                Post(
                    slug=slug,
                    title=frontmatter.get("title", slug),
                    date=date,
                    author=frontmatter.get("author", "Anonim"),
                    content_html=content_html,
                    content_raw=body,
                    excerpt_html=excerpt_html,
                )
            )
        except Exception as e:
            logger.error(f"Error loading post {file_path}: {e}")

    posts.sort(key=lambda x: x.date, reverse=True)

    with _cache_lock:
        _posts_cache = posts

    logger.info(f"Loaded {len(posts)} posts from {posts_dir}")


def get_posts() -> list[Post]:
    with _cache_lock:
        return list(_posts_cache)


def get_post(slug: str) -> Post | None:
    with _cache_lock:
        for post in _posts_cache:
            if post.slug == slug:
                return post
    return None


def get_media_path(path: str) -> Path | None:
    content_path = current_app.config.get("CONTENT_PATH", "/content")
    media_path = Path(content_path) / "media" / path

    if media_path.exists() and media_path.is_file():
        safe_path = media_path.resolve()
        content_resolved = Path(content_path).resolve()
        if str(safe_path).startswith(str(content_resolved)):
            return safe_path

    return None


def load_footer_messages() -> None:
    """Load footer messages from YAML file."""
    global _footer_messages

    content_path = current_app.config.get("CONTENT_PATH", "/content")
    messages_file = Path(content_path) / "other" / "footer-messages.yaml"

    default_messages = ["Nie napalaj się na zbyt wiele"]

    if not messages_file.exists():
        logger.warning(f"Footer messages file does not exist: {messages_file}")
        _footer_messages = default_messages
        return

    try:
        with open(messages_file, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
            messages = data.get("messages", []) if data else []
            if messages and isinstance(messages, list):
                _footer_messages = messages
                logger.info(f"Loaded {len(messages)} footer messages")
            else:
                logger.warning("No messages found in footer-messages.yaml, using defaults")
                _footer_messages = default_messages
    except Exception as e:
        logger.error(f"Error loading footer messages: {e}")
        _footer_messages = default_messages


def get_footer_messages() -> list[str]:
    """Get the list of footer messages."""
    return list(_footer_messages) if _footer_messages else ["Nie napalaj się na zbyt wiele"]


class PostsEventHandler(FileSystemEventHandler):
    def __init__(self, app: Flask):
        self.app = app
        self._debounce_timer: threading.Timer | None = None

    def _reload_posts(self) -> None:
        with self.app.app_context():
            load_posts()
            logger.info("Posts reloaded due to filesystem change")

    def _schedule_reload(self) -> None:
        if self._debounce_timer:
            self._debounce_timer.cancel()
        self._debounce_timer = threading.Timer(1.0, self._reload_posts)
        self._debounce_timer.start()

    def on_created(self, event) -> None:
        if event.src_path.endswith(".md"):
            self._schedule_reload()

    def on_modified(self, event) -> None:
        if event.src_path.endswith(".md"):
            self._schedule_reload()

    def on_deleted(self, event) -> None:
        if event.src_path.endswith(".md"):
            self._schedule_reload()


class ContentEventHandler(FileSystemEventHandler):
    """Handler for footer-messages.yaml and other content root files."""
    def __init__(self, app: Flask):
        self.app = app
        self._debounce_timer: threading.Timer | None = None

    def _reload_footer_messages(self) -> None:
        with self.app.app_context():
            load_footer_messages()
            logger.info("Footer messages reloaded due to filesystem change")

    def _schedule_reload(self) -> None:
        if self._debounce_timer:
            self._debounce_timer.cancel()
        self._debounce_timer = threading.Timer(1.0, self._reload_footer_messages)
        self._debounce_timer.start()

    def on_created(self, event) -> None:
        if event.src_path.endswith("footer-messages.yaml"):
            self._schedule_reload()

    def on_modified(self, event) -> None:
        if event.src_path.endswith("footer-messages.yaml"):
            self._schedule_reload()

    def on_deleted(self, event) -> None:
        if event.src_path.endswith("footer-messages.yaml"):
            self._schedule_reload()


def start_watcher(app: Flask) -> None:
    global _observer

    content_path = app.config.get("CONTENT_PATH", "/content")
    content_dir = Path(content_path)
    posts_dir = content_dir / "posts"
    other_dir = content_dir / "other"

    if not posts_dir.exists():
        logger.warning(f"Cannot start watcher - posts directory does not exist: {posts_dir}")
        return

    _observer = PollingObserver(timeout=5)

    # Watch posts directory for markdown files
    posts_handler = PostsEventHandler(app)
    _observer.schedule(posts_handler, str(posts_dir), recursive=False)

    # Watch content/other directory for footer-messages.yaml
    if other_dir.exists():
        content_handler = ContentEventHandler(app)
        _observer.schedule(content_handler, str(other_dir), recursive=False)
        logger.info(f"Started polling file watcher on {posts_dir} and {other_dir} (NFS-compatible mode)")
    else:
        logger.info(f"Started polling file watcher on {posts_dir} (NFS-compatible mode)")

    _observer.daemon = True
    _observer.start()


def stop_watcher() -> None:
    global _observer
    if _observer:
        _observer.stop()
        _observer.join()
        _observer = None
