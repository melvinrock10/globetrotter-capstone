"""
services/auth-service/main.py
Auth microservice: registration, login, and token verification.

Routes
------
POST /register  – create a new user account
POST /login     – authenticate and return a JWT token
GET  /verify     – used by OTHER services to check if a token is valid
                    (they call this over HTTP instead of decoding it themselves)
"""
import os
import uuid
import datetime

import jwt
from flask import Flask, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash

from models import get_user_by_username, save_user, get_all_users, delete_user

app = Flask(__name__)

SECRET_KEY = os.environ.get("SECRET_KEY", "globetrotter-secret-change-in-prod")


def create_token(username: str) -> str:
    now = datetime.datetime.now(datetime.timezone.utc)
    payload = {
        "sub": username,
        "iat": now,
        "exp": now + datetime.timedelta(hours=24),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")

def _get_requester_from_header(request_obj):
    """Decode the caller's own token to check who they are / if they're admin."""
    auth_header = request_obj.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None
    token = auth_header.split(" ", 1)[1]
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        username = payload.get("sub")
        user = get_user_by_username(username)
        if not user:
            return None
        return {"username": username, "is_admin": bool(user.get("is_admin"))}
    except jwt.PyJWTError:
        return None

@app.route("/register", methods=["POST"])
def register():
    data = request.get_json(silent=True) or {}
    username = data.get("username", "").strip()
    password = data.get("password", "")
    preferences = data.get("preferences", [])
    admin_code = data.get("admin_code", "")
    is_admin = admin_code == os.environ.get("ADMIN_SECRET", "globetrotter-admin-2026")

    if not username or not password:
        return jsonify({"error": "username and password are required"}), 400

    if get_user_by_username(username):
        return jsonify({"error": "username already exists"}), 409

    user = {
        "id": str(uuid.uuid4()),
        "username": username,
        "password_hash": generate_password_hash(password),
        "preferences": preferences,
        "is_admin": is_admin,
    }
    save_user(user)
    return jsonify({"message": "user registered successfully", "username": username}), 201


@app.route("/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    username = data.get("username", "").strip()
    password = data.get("password", "")

    if not username or not password:
        return jsonify({"error": "username and password are required"}), 400

    user = get_user_by_username(username)
    if not user or not check_password_hash(user["password_hash"], password):
        return jsonify({"error": "invalid credentials"}), 401

    token = create_token(username)
    return jsonify({"token": token}), 200


@app.route("/verify", methods=["GET"])
def verify():
    """Other services call this to check if a token is valid.
    Expects: Authorization: Bearer <token>
    Returns: { "valid": true, "username": "alice", "is_admin": false } or { "valid": false }
    """
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return jsonify({"valid": False}), 401

    token = auth_header.split(" ", 1)[1]
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        username = payload.get("sub")
        user = get_user_by_username(username)
        return jsonify({
            "valid": True,
            "username": username,
            "is_admin": bool(user.get("is_admin")) if user else False,
        }), 200
    except jwt.PyJWTError:
        return jsonify({"valid": False}), 401


@app.route("/users/<username>", methods=["GET"])
def get_user(username):
    """Expose limited user info (not password hash) for other services."""
    user = get_user_by_username(username)
    if not user:
        return jsonify({"error": "user not found"}), 404
    return jsonify({
        "username": user["username"],
        "preferences": user.get("preferences", []),
        "is_admin": bool(user.get("is_admin")),
    }), 200


@app.route("/users", methods=["GET"])
def list_all_users():
    """Admin-only: list every registered user (no password hashes)."""
    requester = _get_requester_from_header(request)
    if not requester:
        return jsonify({"error": "authentication required"}), 401
    if not requester.get("is_admin"):
        return jsonify({"error": "admin access required"}), 403

    users = get_all_users()
    safe_users = [
        {"username": u["username"], "preferences": u.get("preferences", []), "is_admin": bool(u.get("is_admin"))}
        for u in users
    ]
    return jsonify(safe_users), 200


@app.route("/users/<username>", methods=["DELETE"])
def remove_user(username):
    """Admin-only: delete a user account."""
    requester = _get_requester_from_header(request)
    if not requester:
        return jsonify({"error": "authentication required"}), 401
    if not requester.get("is_admin"):
        return jsonify({"error": "admin access required"}), 403
    if requester.get("username") == username:
        return jsonify({"error": "cannot delete your own account while logged in"}), 400

    deleted = delete_user(username)
    if not deleted:
        return jsonify({"error": "user not found"}), 404
    return jsonify({"message": "user deleted"}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=False)