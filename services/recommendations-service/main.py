"""
services/recommendations-service/main.py
Recommendations microservice.

This service does NOT read any files directly. Instead, it calls two
other microservices over HTTP:
  - auth-service (port 5001)         -> to verify the user's token
  - destinations-service (port 5002) -> to get the destination catalogue

This is real inter-service communication: if either of those services is
down, this service breaks too. That dependency is the whole point of
Phase 2 (and the seed for Phase 4's resilience work).
"""
import os
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

AUTH_SERVICE_URL = os.environ.get("AUTH_SERVICE_URL", "http://localhost:5001")
DESTINATIONS_SERVICE_URL = os.environ.get("DESTINATIONS_SERVICE_URL", "http://localhost:5002")


def verify_token(auth_header):
    """Call auth-service to check the token and get the username.
    Returns username string, or None if invalid/unreachable.
    """
    if not auth_header:
        return None
    try:
        resp = requests.get(
            f"{AUTH_SERVICE_URL}/verify",
            headers={"Authorization": auth_header, "Accept-Encoding": "identity"},
            timeout=30,
        )
        if resp.status_code == 200:
            data = resp.json()
            if data.get("valid"):
                return data.get("username")
        return None
    except requests.RequestException:
        # auth-service is down or unreachable
        return None


def get_user_preferences(username):
    """We still need the user's preferences (beach, food, etc).
    For now, auth-service only verifies tokens, so we ask it to expose
    a small endpoint for this too. Simplest approach: re-use verify's
    payload isn't enough (it only returns username), so we call a
    dedicated endpoint.
    """
    try:
        resp = requests.get(
            f"{AUTH_SERVICE_URL}/users/{username}",
            headers={"Accept-Encoding": "identity"},
            timeout=30,
        )
        if resp.status_code == 200:
            return resp.json().get("preferences", [])
        return []
    except requests.RequestException:
        return []


def get_destinations():
    """Call destinations-service to get the full catalogue."""
    try:
        resp = requests.get(
            f"{DESTINATIONS_SERVICE_URL}/destinations",
            headers={"Accept-Encoding": "identity"},
            timeout=30,
        )
        if resp.status_code == 200:
            return resp.json()
        return []
    except requests.RequestException:
        return []


@app.route("/recommendations", methods=["GET"])
def get_recommendations():
    auth_header = request.headers.get("Authorization", "")
    username = verify_token(auth_header)
    if not username:
        return jsonify({"error": "authentication required"}), 401

    try:
        limit = int(request.args.get("limit", 5))
    except ValueError:
        return jsonify({"error": "limit must be an integer"}), 400

    preferences = [p.lower() for p in get_user_preferences(username)]
    destinations = get_destinations()

    scored = []
    for dest in destinations:
        dest_tags = [t.lower() for t in dest.get("tags", [])]
        score = sum(1 for pref in preferences if pref in dest_tags)
        scored.append((score, dest))

    scored.sort(key=lambda x: (-x[0], x[1].get("name", "")))

    results = []
    for score, dest in scored[:limit]:
        entry = dict(dest)
        entry["match_score"] = score
        results.append(entry)

    return jsonify(results), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5003, debug=False)