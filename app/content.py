import logging
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

# Default footer message constant
DEFAULT_FOOTER_MESSAGE = "Nie napalaj się na zbyt wiele"

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


class InteractiveWidgetBlockProcessor(BlockProcessor):
    """Custom markdown processor for web-native interactive widgets.

    Syntax:
        :::widget type="terminal-sim" title="Widget Title" config='{"key": "value"}'
        :::

    Generates HTML structure:
        <div class="interactive-widget" data-widget-type="terminal-sim" data-config='{"key": "value"}'>
          <div class="widget-title">Widget Title</div>
        </div>

    The JavaScript framework (interactive-widgets.js) handles widget initialization.
    """

    RE_TYPE = re.compile(r'type="([^"]*)"')
    RE_TITLE = re.compile(r'title="([^"]*)"')
    RE_CONFIG = re.compile(r"config='([^']*)'")

    def test(self, parent, block):
        """Check if block starts with :::widget"""
        lines = block.split('\n')
        return lines[0].strip().startswith(':::widget')

    def run(self, parent, blocks):
        """Parse the widget block and generate HTML."""
        block = blocks.pop(0)
        lines = block.split('\n')

        # Parse first line for attributes
        first_line = lines[0]

        # Extract type (required)
        type_match = self.RE_TYPE.search(first_line)
        if not type_match:
            logger.warning("widget block missing required type attribute")
            return False

        widget_type = type_match.group(1)

        # Extract title (optional, defaults to widget type)
        title_match = self.RE_TITLE.search(first_line)
        title = title_match.group(1) if title_match else widget_type.replace('-', ' ').title()

        # Extract config (optional JSON string)
        config_match = self.RE_CONFIG.search(first_line)
        config_json = config_match.group(1) if config_match else '{}'

        # Create wrapper div with data attributes
        wrapper = etree.SubElement(parent, 'div')
        wrapper.set('class', 'interactive-widget')
        wrapper.set('data-widget-type', widget_type)
        wrapper.set('data-config', config_json)

        # Create title header
        title_div = etree.SubElement(wrapper, 'div')
        title_div.set('class', 'widget-title')
        title_div.text = title

        return True


class InteractiveWidgetExtension(Extension):
    """Markdown extension for web-native interactive widgets."""

    def extendMarkdown(self, md):
        md.parser.blockprocessors.register(
            InteractiveWidgetBlockProcessor(md.parser), 'interactive-widget', 177
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
    """Remove images, audio, video, galleries, and interactive widgets from markdown/HTML text."""
    # Remove gallery blocks: :::gallery ... :::
    text = re.sub(r':::gallery[^\n]*\n.*?:::', '', text, flags=re.DOTALL)

    # Remove widget blocks: :::widget ... :::
    text = re.sub(r':::widget[^\n]*\n.*?:::', '', text, flags=re.DOTALL)

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
    md = markdown.Markdown(extensions=[
        "fenced_code",
        "tables",
        "nl2br",
        GalleryExtension(),
        InteractiveWidgetExtension()
    ])

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

    default_messages = [DEFAULT_FOOTER_MESSAGE]

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
    return list(_footer_messages) if _footer_messages else [DEFAULT_FOOTER_MESSAGE]


class DebouncedFileEventHandler(FileSystemEventHandler):
    """Base class for file event handlers with debounced reload functionality."""

    def __init__(self, app: Flask, file_pattern: str, reload_callback: callable, debounce_delay: float = 1.0):
        """
        Initialize the debounced event handler.

        Args:
            app: Flask application instance
            file_pattern: File pattern to watch (e.g., ".md", "footer-messages.yaml")
            reload_callback: Function to call when files change
            debounce_delay: Delay in seconds before triggering reload (default: 1.0)
        """
        self.app = app
        self.file_pattern = file_pattern
        self.reload_callback = reload_callback
        self.debounce_delay = debounce_delay
        self._debounce_timer: threading.Timer | None = None

    def _reload(self) -> None:
        """Execute the reload callback within app context."""
        with self.app.app_context():
            self.reload_callback()

    def _schedule_reload(self) -> None:
        """Schedule a reload with debouncing."""
        if self._debounce_timer:
            self._debounce_timer.cancel()
        self._debounce_timer = threading.Timer(self.debounce_delay, self._reload)
        self._debounce_timer.start()

    def _should_handle_event(self, event_path: str) -> bool:
        """Check if the event should trigger a reload."""
        return event_path.endswith(self.file_pattern)

    def on_created(self, event) -> None:
        if self._should_handle_event(event.src_path):
            self._schedule_reload()

    def on_modified(self, event) -> None:
        if self._should_handle_event(event.src_path):
            self._schedule_reload()

    def on_deleted(self, event) -> None:
        if self._should_handle_event(event.src_path):
            self._schedule_reload()


class PostsEventHandler(DebouncedFileEventHandler):
    """Handler for markdown post files."""

    def __init__(self, app: Flask):
        def reload_posts_with_logging():
            load_posts()
            logger.info("Posts reloaded due to filesystem change")

        super().__init__(app, ".md", reload_posts_with_logging)


class ContentEventHandler(DebouncedFileEventHandler):
    """Handler for footer-messages.yaml and other content root files."""

    def __init__(self, app: Flask):
        def reload_footer_with_logging():
            load_footer_messages()
            logger.info("Footer messages reloaded due to filesystem change")

        super().__init__(app, "footer-messages.yaml", reload_footer_with_logging)


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
