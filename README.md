# Wish Journal

A minimal, password-protected blog application that reads Markdown posts from local filesystem with a beautiful dark purple theme.

## Features

- **Password-based authentication** - Password identifies user (no username needed)
- **Markdown posts** - Write posts with YAML frontmatter
- **User comments** - Authenticated users can comment on posts
- **Media support** - Images, audio with custom player, and videos
- **Auto-reload** - Watches for file changes (NFS-compatible with watchdog)
- **Dark purple theme** - Custom styled interface
- **Polish UI** - Fully localized interface

## Content Directory Structure

```
content/
├── posts/
│   ├── my-first-post.md
│   └── another-post.md
├── media/
│   ├── images/
│   │   └── photo.jpg
│   ├── audio/
│   │   └── song.mp3
│   └── video/
│       └── clip.mp4
└── other/
    └── footer-messages.yaml
```

## Post Format

Posts are Markdown files with YAML frontmatter:

```markdown
---
title: "Post Title"
date: 2025-01-15
author: "Jan"
---

Post content in Markdown...

![Image](/media/images/photo.jpg)

<audio controls
       data-title="Song Title"
       data-artist="Artist Name"
       data-artwork="/media/images/album-cover.jpg">
  <source src="/media/audio/song.mp3" type="audio/mpeg">
</audio>

<video controls src="/media/video/clip.mp4"></video>
```

### Audio Player

The application includes a custom-styled audio player that matches the purple theme. Use data attributes for metadata:

- `data-title` - Song title (default: "Bez tytułu")
- `data-artist` - Artist name (default: "Nieznany wykonawca")
- `data-artwork` - Path to album art (optional, displays as 80x80px thumbnail)

**Example:**
```html
<audio controls
       data-title="Save Me"
       data-artist="Queen"
       data-artwork="/media/images/queen-album.jpg">
  <source src="/media/audio/Queen-Save_Me.mp3" type="audio/mpeg">
</audio>
```

The player features:
- Full width design matching purple color palette
- Polish interface text (odtwórz/pauza, głośność)
- Custom progress bar with seek functionality
- Time display (current/duration)
- Album artwork display
- Hover effects matching site buttons

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| SECRET_KEY | Flask session encryption key | dev-key-change-in-production |
| DATABASE_PATH | SQLite file path | /data/wish-journal.db |
| CONTENT_PATH | Posts and media directory | /content |
| FLASK_ENV | Environment (production/development) | - |

## Local Development

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create directories
mkdir -p data content/posts content/media/{images,audio,video} content/other

# Add a test user (password-only authentication)
python -c "
from app import create_app
from app.models import create_user
app = create_app()
with app.app_context():
    create_user('secret123', 'Jan Kowalski')
    print('User created! Password: secret123')
"

# Run the app
flask --app app run --debug
```

Then open http://localhost:5000 and enter password `secret123`.

## Docker

```bash
docker build -t wish-journal .

docker run -d \
  -p 5000:5000 \
  -v ./data:/data \
  -v ./content:/content \
  -e SECRET_KEY=your-secret-key \
  wish-journal
```

## Kubernetes / Helm

Helm chart available in `drik-homelab-helm-charts` repository:

```bash
helm install wish-journal ./charts/wish-journal \
  --set ingress.enabled=true \
  --set ingress.hosts[0].host=blog.example.com \
  --set persistence.content.existingClaim=nfs-content
```

## Tests

**Always run tests in a virtual environment:**

```bash
# Activate virtual environment
source venv/bin/activate

# Install test dependencies
pip install pytest pytest-cov

# Run all tests
pytest tests/ -v

# Run with coverage report
pytest tests/ -v --cov=app --cov-report=term-missing

# Run specific test file
pytest tests/test_auth.py -v
```

The test suite includes:
- `test_auth.py` - Authentication flow and protected routes
- `test_routes.py` - Post display, comments, media serving
- `test_content.py` - Markdown parsing and post loading
- `test_models.py` - Database operations
- `test_utils.py` - Utility functions

## User Management

### Authentication System

This application uses **password-only authentication** - each user is identified by their unique password (no username field on login).

### Adding Users

#### Local Development

```bash
python -c "
from app import create_app
from app.models import create_user
app = create_app()
with app.app_context():
    create_user('unique-password-123', 'Jan Kowalski')
    print('User created!')
"
```

#### Via Docker

```bash
docker exec -it CONTAINER_NAME python3 << 'EOF'
from app import create_app
from app.models import create_user
app = create_app()
with app.app_context():
    create_user('unique-password-123', 'Jan Kowalski')
    print('User created!')
EOF
```

#### Via kubectl (Kubernetes)

```bash
kubectl exec -it deployment/wish-journal -n NAMESPACE -- python3 << 'EOF'
from app import create_app
from app.models import create_user
app = create_app()
with app.app_context():
    create_user('unique-password-123', 'Jan Kowalski')
    print('User created!')
EOF
```

### Listing Users

```bash
# Via kubectl
kubectl exec -it deployment/wish-journal -n NAMESPACE -- python3 << 'EOF'
import sqlite3
conn = sqlite3.connect('/data/wish-journal.db')
cursor = conn.cursor()
cursor.execute('SELECT id, name, created_at FROM users')
for row in cursor.fetchall():
    print(f"ID: {row[0]}, Name: {row[1]}, Created: {row[2]}")
conn.close()
EOF
```

### Deleting a User

```bash
# Via kubectl
kubectl exec -it deployment/wish-journal -n NAMESPACE -- python3 << 'EOF'
import sqlite3
conn = sqlite3.connect('/data/wish-journal.db')
conn.execute('DELETE FROM users WHERE id = ?', (USER_ID,))
conn.commit()
print("User deleted!")
conn.close()
EOF
```

### Changing Password

Since password identifies the user, changing password effectively creates a new identity. It's recommended to delete the old user and create a new one instead.

### Password Security

- Passwords are hashed with bcrypt (automatic salting)
- Never stored in plain text
- Each password must be unique (identifies the user)
- Recommended length: minimum 12 characters
- Use strong, unique passwords for each user

## License

Private use.
