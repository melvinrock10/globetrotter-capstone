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

from models import get_user_by_username, save_user

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


@app.route("/register", methods=["POST"])
def register():
    data = request.get_json(silent=True) or {}
    username = data.get("username", "").strip()
    password = data.get("password", "")
    preferences = data.get("preferences", [])

    if not username or not password:
        return jsonify({"error": "username and password are required"}), 400

    if get_user_by_username(username):
        return jsonify({"error": "username already exists"}), 409

    user = {
        "id": str(uuid.uuid4()),
        "username": username,
        "password_hash": generate_password_hash(password),
        "preferences": preferences,
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
    Returns: { "valid": true, "username": "alice" } or { "valid": false }
    """
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return jsonify({"valid": False}), 401

    token = auth_header.split(" ", 1)[1]
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return jsonify({"valid": True, "username": payload.get("sub")}), 200
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
    }), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=False)