#!/bin/bash

# Usage: ./sync-users.sh <csv-file> <namespace>
# CSV format: first_name,last_name,username,password

set -e

if [ "$#" -ne 2 ]; then
    echo "Usage: $0 <csv-file> <namespace>"
    echo "CSV format: first_name,last_name,username,password"
    exit 1
fi

CSV_FILE="$1"
NAMESPACE="$2"

if [ ! -f "$CSV_FILE" ]; then
    echo "Error: CSV file '$CSV_FILE' not found"
    exit 1
fi

echo "Reading users from $CSV_FILE..."
echo "Target namespace: $NAMESPACE"
echo ""

# Read CSV file and process each user
tail -n +2 "$CSV_FILE" | while IFS=, read -r first_name last_name username password; do
    # Skip empty lines
    if [ -z "$username" ]; then
        continue
    fi

    echo "Processing user: $username ($first_name $last_name)..."

    kubectl exec -it deployment/wish-journal -n "$NAMESPACE" -- python3 << EOF
import sqlite3
import bcrypt

# User details
first_name = "$first_name"
last_name = "$last_name"
username = "$username"
password = "$password"

# Connect to database
conn = sqlite3.connect('/data/wish-journal.db')
cursor = conn.cursor()

# Hash password
password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

# Check if user exists
cursor.execute('SELECT id FROM users WHERE username = ?', (username,))
existing_user = cursor.fetchone()

if existing_user:
    # Update existing user
    cursor.execute(
        'UPDATE users SET first_name = ?, last_name = ?, password_hash = ? WHERE username = ?',
        (first_name, last_name, password_hash.decode('utf-8'), username)
    )
    print(f"User {username} updated!")
else:
    # Insert new user
    cursor.execute(
        'INSERT INTO users (first_name, last_name, username, password_hash) VALUES (?, ?, ?, ?)',
        (first_name, last_name, username, password_hash.decode('utf-8'))
    )
    print(f"User {username} created!")

conn.commit()
conn.close()
EOF

    echo ""
done

echo "User synchronization complete!"
