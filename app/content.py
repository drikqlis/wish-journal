import logging
import os
import re
import threading
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import markdown
import yaml
from flask import Flask, current_app
from watchdog.events import FileSystemEventHandler
from watchdog.observers.polling import PollingObserver

logger = logging.getLogger(__name__)

_posts_cache: list["Post"] = []
_cache_lock = threading.Lock()
_observer: PollingObserver | None = None


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
    md = markdown.Markdown(extensions=["fenced_code", "tables", "nl2br"])

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

            # Create excerpt (first 500 chars of raw, then render)
            excerpt_raw = body.strip()
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


def start_watcher(app: Flask) -> None:
    global _observer

    content_path = app.config.get("CONTENT_PATH", "/content")
    posts_dir = Path(content_path) / "posts"

    if not posts_dir.exists():
        logger.warning(f"Cannot start watcher - posts directory does not exist: {posts_dir}")
        return

    event_handler = PostsEventHandler(app)
    _observer = PollingObserver(timeout=5)
    _observer.schedule(event_handler, str(posts_dir), recursive=False)
    _observer.daemon = True
    _observer.start()
    logger.info(f"Started polling file watcher on {posts_dir} (NFS-compatible mode)")


def stop_watcher() -> None:
    global _observer
    if _observer:
        _observer.stop()
        _observer.join()
        _observer = None
