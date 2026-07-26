"""
services/itineraries-service/main.py
Itineraries microservice: create and list a user's itineraries.
Calls auth-service to verify tokens (does not decode JWTs itself).
"""
import os
import uuid
import datetime
import requests
from flask import Flask, request, jsonify

from models import get_itineraries_for_user, save_itinerary

app = Flask(__name__)

AUTH_SERVICE_URL = os.environ.get("AUTH_SERVICE_URL", "http://localhost:5001")


def verify_token(auth_header):
    if not auth_header:
        return None
    try:
        resp = requests.get(
            f"{AUTH_SERVICE_URL}/verify",
            headers={"Authorization": auth_header},
            timeout=5,
        )
        if resp.status_code == 200:
            data = resp.json()
            if data.get("valid"):
                return data.get("username")
        return None
    except requests.RequestException:
        return None


@app.route("/itineraries", methods=["POST"])
def create_itinerary():
    username = verify_token(request.headers.get("Authorization", ""))
    if not username:
        return jsonify({"error": "authentication required"}), 401

    data = request.get_json(silent=True) or {}
    title = data.get("title", "").strip()
    destinations = data.get("destinations", [])
    start_date = data.get("start_date", "")
    end_date = data.get("end_date", "")
    notes = data.get("notes", "")

    if not title:
        return jsonify({"error": "title is required"}), 400

    itinerary = {
        "id": str(uuid.uuid4()),
        "username": username,
        "title": title,
        "destinations": destinations,
        "start_date": start_date,
        "end_date": end_date,
        "notes": notes,
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
    save_itinerary(itinerary)
    return jsonify(itinerary), 201


@app.route("/itineraries", methods=["GET"])
def list_itineraries():
    username = verify_token(request.headers.get("Authorization", ""))
    if not username:
        return jsonify({"error": "authentication required"}), 401

    return jsonify(get_itineraries_for_user(username)), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5004, debug=False)