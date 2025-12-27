# Wish Journal - Project Overview

## Project Purpose

**Wish Journal** is a minimalist, password-protected personal blog application designed for private journaling and sharing thoughts with selected readers. The application features a unique authentication system where users are identified solely by their password (no username required), making it simple yet secure.

### Core Features
- **Password-only authentication** - Unique login system using only passwords
- **Markdown-based blog posts** - Write posts in Markdown with YAML frontmatter
- **Comments system** - Authenticated users can comment on posts
- **Media support** - Display images, audio (with custom player), and videos
- **Real-time content updates** - Automatic reload when content files change (NFS-compatible)
- **Polish interface** - Fully localized UI with custom dark purple theme

---

## Technology Stack

### Backend
- **Framework**: Flask 3.1.0 (Python web framework)
- **WSGI Server**: Gunicorn 23.0.0
- **Database**: SQLite 3
- **Security**: bcrypt 4.2.1 (password hashing), CSRF token validation
- **Content Processing**:
  - `Markdown 3.7` - Converts Markdown to HTML
  - `PyYAML 6.0.2` - Parses YAML frontmatter
- **File Monitoring**: watchdog 6.0.0 (NFS-compatible file watching)
- **HTTP Utilities**: Werkzeug 3.1.3

### Frontend
- **Templating**: Jinja2
- **JavaScript**: Vanilla JS for interactivity
- **Styling**: Custom CSS with dark purple color scheme

### DevOps
- **Containerization**: Docker (Python 3.13-slim base)
- **CI/CD**: GitHub Actions
- **Testing**: pytest with pytest-cov
- **Code Coverage**: Codecov integration

---

## Project Structure

```
wish-journal/
├── app/                          # Main Flask application
│   ├── __init__.py              # App factory, configuration, blueprints
│   ├── auth.py                  # Authentication blueprint (login/logout)
│   ├── routes.py                # Main routes (posts, comments, media)
│   ├── models.py                # Database models and operations
│   ├── content.py               # Content loading, parsing, file watching
│   └── utils.py                 # Utilities (date formatting, CSRF)
├── templates/                    # Jinja2 HTML templates
│   ├── base.html                # Base layout with header/footer
│   ├── login.html               # Login page
│   ├── index.html               # Post listing page
│   ├── post.html                # Post detail with comments
│   └── 404.html                 # 404 error page
├── static/                       # Frontend assets
│   ├── style.css                # Custom dark purple theme
│   └── favicon.ico              # Site favicon
├── content/                      # Content storage (dynamic)
│   ├── posts/                   # Markdown post files (*.md)
│   ├── media/                   # Images, audio, video files
│   │   ├── images/
│   │   ├── audio/
│   │   └── video/
│   └── other/
│       └── footer-messages.yaml # Random footer messages
├── data/                         # SQLite database location
│   └── wish_journal.db          # Created at runtime
├── tests/                        # Test suite
│   ├── conftest.py              # Test fixtures and setup
│   ├── test_auth.py             # Authentication tests
│   ├── test_routes.py           # Route and view tests
│   ├── test_content.py          # Content parsing tests
│   ├── test_models.py           # Database model tests
│   └── test_utils.py            # Utility function tests
├── .github/workflows/
│   └── build.yml                # CI/CD pipeline
├── Dockerfile                    # Container configuration
├── requirements.txt              # Python dependencies
├── README.md                     # Main documentation
├── USERS.md                      # User management guide
└── AUDIO_PLAYER_USAGE.md        # Audio player documentation
```

---

## How It Works

### Authentication Flow
1. User visits `/auth/login`
2. Enters **only a password** (no username field)
3. System queries SQLite for matching bcrypt hash using optimized prefix lookup
4. On success, session is created with user ID
5. Cookie-based authentication for subsequent requests
6. Protected routes check session state

### Content Management
1. **Posts** are Markdown files in `content/posts/` with YAML frontmatter:
   ```yaml
   ---
   title: "Post Title"
   date: "2025-01-15"
   author: "Author Name"
   ---
   Post content in Markdown...
   ```
2. On startup, `load_posts()` reads and parses all `.md` files
3. Markdown body converted to HTML
4. Excerpts generated (first 500 chars, media stripped)
5. Posts cached in memory, sorted by date (newest first)
6. **File watcher** monitors changes and auto-reloads content

### Comments System
- Stored in SQLite with fields: `user_id`, `post_slug`, `content`, `timestamp`
- CSRF-protected form submission
- Only authenticated users can comment
- Comments displayed with author name and timestamp

### Media Serving
- Files referenced via `/media/images/photo.jpg` paths
- System validates paths are within `content/media/` (prevents directory traversal)
- MIME types auto-detected
- Custom audio player with metadata support (title, artist, artwork)

### Footer Messages
- Loaded from `content/other/footer-messages.yaml`
- Random message selected on each page load
- Authenticated users see logout link

---

## Testing

### Test Infrastructure

The project has **comprehensive test coverage** across all modules:

| Test File | Coverage |
|-----------|----------|
| `test_auth.py` | Authentication flow, login/logout, protected routes |
| `test_routes.py` | Post display, comments, media serving, CSRF protection |
| `test_content.py` | Markdown parsing, post loading, sorting, footer messages |
| `test_models.py` | Database operations, user creation, comment storage |
| `test_utils.py` | Date formatting (Polish), CSRF token generation |

### Test Fixtures (`conftest.py`)
- Temporary test database and content directories
- Pre-populated sample posts
- Test user creation
- Fixtures: `app`, `client`, `logged_in_client`, `client_with_user`

### Running Tests

**IMPORTANT**: Always run tests in a virtual environment:

```bash
# Activate virtual environment
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows

# Run all tests
pytest

# Run with verbose output
pytest -v

# Run with coverage report
pytest --cov=app --cov-report=term-missing

# Run specific test file
pytest tests/test_auth.py -v

# Run specific test function
pytest tests/test_auth.py::test_login_success -v
```

### CI/CD Integration

GitHub Actions automatically:
1. Runs full test suite: `pytest tests/ -v --cov=app --cov-report=xml`
2. Uploads coverage to Codecov
3. Builds Docker image (only if tests pass)
4. Pushes to GitHub Container Registry

---

## Development Guidelines

### Adding New Features

When making changes to the codebase:

1. **Write tests first** (TDD approach recommended)
2. **Run existing tests** to ensure no regressions
3. **Add new tests** for new functionality:
   - Add to appropriate test file (`test_*.py`)
   - Use existing fixtures from `conftest.py`
   - Follow existing test patterns
   - Ensure edge cases are covered
4. **Run tests in venv** before committing
5. **Update this documentation** if architecture changes

### Testing Best Practices

- **Always activate venv** before running tests: `source venv/bin/activate`
- **Test coverage goal**: Maintain high coverage (currently comprehensive)
- **Test isolation**: Each test should be independent
- **Use fixtures**: Leverage `conftest.py` fixtures for common setup
- **Mock external dependencies**: Use pytest mocks for file I/O, time, etc.

### Code Organization Principles

- **Separation of concerns**: Each module has a single responsibility
- **Blueprint architecture**: Routes organized by functionality (auth, main)
- **Content decoupling**: Content files separate from application code
- **Security first**: CSRF protection, bcrypt hashing, path validation

---

## Database Schema

### Users Table
```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    password_hash TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Comments Table
```sql
CREATE TABLE comments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    post_slug TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```

---

## Configuration

### Environment Variables
- `SECRET_KEY` - Flask secret key (auto-generated if not set)
- `DATABASE_PATH` - SQLite database location (default: `data/wish_journal.db`)
- `CONTENT_DIR` - Content directory path (default: `content`)

### Content Directory Structure
```
content/
├── posts/           # Markdown files (*.md)
├── media/
│   ├── images/      # Image files
│   ├── audio/       # Audio files (MP3, OGG, etc.)
│   └── video/       # Video files
└── other/
    └── footer-messages.yaml
```

---

## Deployment

### Docker
```bash
# Build image
docker build -t wish-journal .

# Run container
docker run -p 8000:8000 \
  -v $(pwd)/content:/app/content \
  -v $(pwd)/data:/app/data \
  wish-journal
```

### Manual Deployment
```bash
# Install dependencies
pip install -r requirements.txt

# Run with Gunicorn
gunicorn -w 4 -b 0.0.0.0:8000 'app:create_app()'
```

---

## Recent Development Activity

Latest improvements focus on:
- UI/UX polish (footer styling, mobile optimization)
- Navigation height fixes
- Font and color refinement
- Audio player implementation
- Performance improvements (password prefix lookup optimization)

---

## Additional Documentation

- **README.md** - Setup and installation guide
- **USERS.md** - User management instructions
- **AUDIO_PLAYER_USAGE.md** - Audio player feature guide

---

## Quick Reference

### Most Common Commands
```bash
# Activate venv and run tests
source venv/bin/activate && pytest -v

# Run with coverage
pytest --cov=app --cov-report=term-missing

# Run development server
flask run --debug

# Create new user (from Python shell)
from app import create_app
from app.models import create_user
app = create_app()
with app.app_context():
    create_user("SecurePassword123", "User Name")
```

### Key Files to Know
- **app/__init__.py** - Application factory and initialization
- **app/routes.py** - Main application routes
- **app/auth.py** - Authentication logic
- **app/content.py** - Content loading and file watching
- **tests/conftest.py** - Test fixtures
