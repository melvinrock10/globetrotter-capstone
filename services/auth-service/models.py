"""
services/auth-service/models.py
Minimal data access for the auth service: reads/writes data/users.json
(shared with the rest of the project, one level up from /services).
"""
import json
import os

_BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = os.environ.get("DATA_DIR", os.path.join(_BASE_DIR, "data"))
USERS_FILE = os.path.join(DATA_DIR, "users.json")


def _read_json(filepath):
    if not os.path.exists(filepath):
        return []
    with open(filepath, "r", encoding="utf-8") as fh:
        content = fh.read().strip()
        return json.loads(content) if content else []


def _write_json(filepath, data):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)


def get_all_users():
    return _read_json(USERS_FILE)


def get_user_by_username(username):
    for user in get_all_users():
        if user.get("username") == username:
            return user
    return None


def save_user(user):
    users = get_all_users()
    users.append(user)
    _write_json(USERS_FILE, users)

def delete_user(username):
    users = get_all_users()
    new_users = [u for u in users if u.get("username") != username]
    if len(new_users) == len(users):
        return False
    _write_json(USERS_FILE, new_users)
    return True