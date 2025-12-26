# Wish Journal

A minimal, password-protected blog application that reads Markdown posts from local filesystem.

## Features

- Password-based authentication (password identifies user)
- Markdown posts with YAML frontmatter
- User comments
- Auto-reload on file changes (watchdog)
- Dark terminal theme (purple on black)
- Polish UI

## Content Directory Structure

```
/content/
├── posts/
│   ├── my-first-post.md
│   └── another-post.md
└── media/
    ├── images/
    │   └── photo.jpg
    ├── audio/
    │   └── song.mp3
    └── video/
        └── clip.mp4
```

## Post Format

```markdown
---
title: "Post Title"
date: 2024-01-15
author: "Jan"
---

Post content in Markdown...

![Image](/media/images/photo.jpg)

<audio controls src="/media/audio/song.mp3"></audio>

<video controls src="/media/video/clip.mp4"></video>
```

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

# Create directories and example content
mkdir -p data content/posts content/media/images

# Copy example posts
cp -r examples/posts/* content/posts/

# Add a test user
python -c "
from app import create_app
from app.models import create_user
app = create_app({'DATABASE_PATH': 'data/wish-journal.db', 'CONTENT_PATH': 'content'})
with app.app_context():
    create_user('Jan', 'Kowalski', 'janek', 'secret123')
    print('User created! Password: secret123')
"

# Run the app
DATABASE_PATH=data/wish-journal.db CONTENT_PATH=content flask --app app run
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

```bash
pip install pytest pytest-cov
pytest tests/ -v --cov=app
```

## User Management

See [USERS.md](USERS.md) for instructions on adding, removing, and managing users.

## License

Private use.
