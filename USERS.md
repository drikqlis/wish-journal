# User Management

## Authentication System

This blog uses a non-standard authentication system: **password identifies user**.

- Each user has a unique password
- Login requires only the password (no username field)
- Password must be unique for each user

## Adding Users

Users are added manually via SQLite database.

### Via kubectl (Kubernetes)

```bash
kubectl exec -it deployment/wish-journal -n NAMESPACE -- python3 << 'EOF'
import sqlite3
import bcrypt

# User details
first_name = "Jan"
last_name = "Kowalski"
username = "janek"        # Display name for comments
password = "secret-password"  # UNIQUE password for this user

# Connect to database
conn = sqlite3.connect('/data/wish-journal.db')

# Hash password
password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

# Add user
conn.execute(
    'INSERT INTO users (first_name, last_name, username, password_hash) VALUES (?, ?, ?, ?)',
    (first_name, last_name, username, password_hash.decode('utf-8'))
)
conn.commit()
conn.close()

print(f"User {username} created!")
EOF
```

### Via Docker

```bash
docker exec -it CONTAINER_NAME python3 << 'EOF'
import sqlite3
import bcrypt

first_name = "Jan"
last_name = "Kowalski"
username = "janek"
password = "secret-password"

conn = sqlite3.connect('/data/wish-journal.db')
password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
conn.execute(
    'INSERT INTO users (first_name, last_name, username, password_hash) VALUES (?, ?, ?, ?)',
    (first_name, last_name, username, password_hash.decode('utf-8'))
)
conn.commit()
conn.close()
print(f"User {username} created!")
EOF
```

### Local Development

```bash
python -c "
from app import create_app
from app.models import create_user
app = create_app({'DATABASE_PATH': 'data/wish-journal.db', 'CONTENT_PATH': 'content'})
with app.app_context():
    create_user('Jan', 'Kowalski', 'janek', 'secret123')
    print('User created!')
"
```

## Listing Users

```bash
kubectl exec -it deployment/wish-journal -n NAMESPACE -- python3 << 'EOF'
import sqlite3
conn = sqlite3.connect('/data/wish-journal.db')
cursor = conn.cursor()
cursor.execute('SELECT id, first_name, last_name, username, created_at FROM users')
for row in cursor.fetchall():
    print(f"ID: {row[0]}, Name: {row[1]} {row[2]}, Username: {row[3]}, Created: {row[4]}")
conn.close()
EOF
```

## Deleting a User

```bash
kubectl exec -it deployment/wish-journal -n NAMESPACE -- python3 << 'EOF'
import sqlite3
conn = sqlite3.connect('/data/wish-journal.db')
conn.execute('DELETE FROM users WHERE username = ?', ('janek',))
conn.commit()
print("User deleted!")
conn.close()
EOF
```

## Changing Password

```bash
kubectl exec -it deployment/wish-journal -n NAMESPACE -- python3 << 'EOF'
import sqlite3
import bcrypt

username = "janek"
new_password = "new-secret-password"

conn = sqlite3.connect('/data/wish-journal.db')
password_hash = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())
conn.execute(
    'UPDATE users SET password_hash = ? WHERE username = ?',
    (password_hash.decode('utf-8'), username)
)
conn.commit()
print(f"Password for {username} changed!")
conn.close()
EOF
```

## Password Security

- Passwords are hashed with bcrypt (automatic salting)
- Passwords are never stored in plain text
- Each password must be unique (identifies the user)
- Recommended password length: minimum 12 characters
