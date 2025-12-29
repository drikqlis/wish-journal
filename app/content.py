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


class PythonScriptBlockProcessor(BlockProcessor):
    """Custom markdown processor for interactive Python scripts.

    Syntax:
        :::python-script path="examples/hello.py" title="Script Title"
        :::

    Generates HTML structure:
        <div class="script-wrapper" data-script-path="examples/hello.py">
          <div class="script-title">Script Title</div>
          <div class="script-terminal">
            <div class="script-output"></div>
            <div class="script-input-container">
              <span class="script-prompt">>>> </span>
              <input type="text" class="script-input" disabled>
            </div>
          </div>
          <div class="script-controls">
            <button class="script-start" aria-label="Uruchom skrypt">
              <span class="script-icon"></span>
            </button>
            <span class="script-status idle">Naciśnij przycisk aby rozpocząć</span>
          </div>
        </div>
    """

    RE_PATH = re.compile(r'path="([^"]*)"')
    RE_TITLE = re.compile(r'title="([^"]*)"')

    def test(self, parent, block):
        """Check if block starts with :::python-script"""
        lines = block.split('\n')
        return lines[0].strip().startswith(':::python-script')

    def run(self, parent, blocks):
        """Parse the python-script block and generate HTML."""
        block = blocks.pop(0)
        lines = block.split('\n')

        # Parse first line for attributes
        first_line = lines[0]

        # Extract path (required)
        path_match = self.RE_PATH.search(first_line)
        if not path_match:
            logger.warning("python-script block missing required path attribute")
            return False

        script_path = path_match.group(1)

        # Validate script path exists
        resolved_path = get_script_path(script_path)
        if not resolved_path:
            logger.warning(f"Invalid script path: {script_path}")
            # Create error message div
            error_div = etree.SubElement(parent, 'div')
            error_div.set('class', 'script-error')
            error_div.text = f"Błąd: nie znaleziono skryptu '{script_path}'"
            return True

        # Extract title (optional, defaults to filename)
        title_match = self.RE_TITLE.search(first_line)
        title = title_match.group(1) if title_match else Path(script_path).stem

        # Create wrapper div with data attribute
        wrapper = etree.SubElement(parent, 'div')
        wrapper.set('class', 'script-wrapper')
        wrapper.set('data-script-path', script_path)

        # Create title header
        title_div = etree.SubElement(wrapper, 'div')
        title_div.set('class', 'script-title')
        title_div.text = title

        # Create terminal area
        terminal = etree.SubElement(wrapper, 'div')
        terminal.set('class', 'script-terminal')

        # Output area (initially empty)
        output = etree.SubElement(terminal, 'div')
        output.set('class', 'script-output empty')

        # Input container
        input_container = etree.SubElement(terminal, 'div')
        input_container.set('class', 'script-input-container')

        # Input field (no visible prompt, browser cursor handles it)
        input_field = etree.SubElement(input_container, 'input')
        input_field.set('type', 'text')
        input_field.set('class', 'script-input')
        input_field.set('disabled', 'disabled')

        # Controls area
        controls = etree.SubElement(wrapper, 'div')
        controls.set('class', 'script-controls')

        # Start button (will become restart after first run)
        button = etree.SubElement(controls, 'button')
        button.set('class', 'script-start')
        button.set('aria-label', 'Uruchom skrypt')

        # Button icon (play initially, will change to restart via JS)
        # Use a span wrapper for inline SVG (populated by JavaScript using getIcon())
        icon = etree.SubElement(button, 'span')
        icon.set('class', 'script-icon')

        # Running indicator (hidden by default)
        indicator = etree.SubElement(controls, 'span')
        indicator.set('class', 'script-running-indicator')

        return True


class PythonScriptExtension(Extension):
    """Markdown extension for interactive Python scripts."""

    def extendMarkdown(self, md):
        md.parser.blockprocessors.register(
            PythonScriptBlockProcessor(md.parser), 'python-script', 176
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
    """Remove images, audio, video, galleries, and Python scripts from markdown/HTML text."""
    # Remove gallery blocks: :::gallery ... :::
    text = re.sub(r':::gallery[^\n]*\n.*?:::', '', text, flags=re.DOTALL)

    # Remove python-script blocks: :::python-script ... :::
    text = re.sub(r':::python-script[^\n]*\n.*?:::', '', text, flags=re.DOTALL)

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
        PythonScriptExtension()
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


def get_script_path(path: str) -> Path | None:
    """
    Validate and resolve script path within content/scripts/ directory.

    Args:
        path: Relative path to script (e.g., "examples/hello.py")

    Returns:
        Resolved Path object if valid, None otherwise

    Security checks:
    - Must exist and be a file
    - Must have .py extension
    - Must resolve within content directory (prevents directory traversal)
    """
    content_path = current_app.config.get("CONTENT_PATH", "/content")
    script_path = Path(content_path) / "scripts" / path

    # Check existence and file type
    if not script_path.exists() or not script_path.is_file():
        logger.warning(f"Script path does not exist or is not a file: {script_path}")
        return None

    # Check extension
    if script_path.suffix != '.py':
        logger.warning(f"Script path must be a .py file: {script_path}")
        return None

    # Resolve symlinks and verify within content directory
    safe_path = script_path.resolve()
    content_resolved = Path(content_path).resolve()
    if not str(safe_path).startswith(str(content_resolved)):
        logger.warning(f"Script path outside content directory: {safe_path}")
        return None

    return safe_path


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
