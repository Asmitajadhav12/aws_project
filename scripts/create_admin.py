"""Create an administrator without typing the full Flask CLI command.

Usage (with the virtual environment active, from the project root):

    python scripts/create_admin.py

It asks for a username, a full name and a password, hashes the password with
Werkzeug and inserts the account. Equivalent to:

    flask --app app create-admin
"""
import getpass
import sys
from pathlib import Path

# Allow "python scripts/create_admin.py" from the project root.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from werkzeug.security import generate_password_hash  # noqa: E402

from app import app  # noqa: E402
from services.db import execute, query_one  # noqa: E402


def main() -> int:
    username = input("Admin username: ").strip()
    full_name = input("Full name (optional): ").strip()
    password = getpass.getpass("Password (min 8 characters): ")
    confirm = getpass.getpass("Confirm password: ")

    if not username:
        print("A username is required.", file=sys.stderr)
        return 1
    if password != confirm:
        print("The passwords do not match.", file=sys.stderr)
        return 1
    if len(password) < 8:
        print("Use a password of at least 8 characters.", file=sys.stderr)
        return 1

    with app.app_context():
        existing = query_one("SELECT id FROM users WHERE username = %s", (username,))
        password_hash = generate_password_hash(password)
        if existing:
            execute(
                "UPDATE users SET password_hash = %s, role = 'admin', is_active = 1 WHERE id = %s",
                (password_hash, existing["id"]),
            )
            print(f"Updated '{username}' as an active admin.")
        else:
            execute(
                "INSERT INTO users (username, full_name, password_hash, role) "
                "VALUES (%s, %s, %s, 'admin')",
                (username, full_name or None, password_hash),
            )
            print(f"Created admin '{username}'.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
