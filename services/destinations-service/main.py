"""
services/destinations-service/main.py

Places microservice: browse/search places, admin-managed CRUD, and
user ratings/reviews.

Routes
------
GET    /destinations                  - search/filter places
GET    /destinations/<id>             - get one place (with rating summary)
POST   /destinations                  - add a place (admin only)
PUT    /destinations/<id>             - edit a place (admin only)
DELETE /destinations/<id>             - remove a place (admin only)
POST   /destinations/<id>/reviews     - submit a review (any logged-in user)
GET    /destinations/<id>/reviews     - list reviews for a place
"""
import os
import time
import uuid
import datetime
import requests
from flask import Flask, request, jsonify

from models import (
    get_all_places, get_place_by_id, add_place, update_place, delete_place,
    get_reviews_for_place, add_review, get_all_reviews,
    get_settings, update_settings,
)

app = Flask(__name__)


_places_cache = {"data": None, "timestamp": 0}
CACHE_TTL_SECONDS = 30


def get_cached_places():
    now = time.time()
    if _places_cache["data"] is None or (now - _places_cache["timestamp"]) > CACHE_TTL_SECONDS:
        try:
            fresh = get_all_places()
            _places_cache["data"] = fresh
            _places_cache["timestamp"] = now
        except Exception:
            # Atlas is unreachable right now — if we have ANY previous data,
            # serve that instead of a hard error. Only fail if we've never
            # successfully loaded anything yet.
            if _places_cache["data"] is None:
                raise
    return _places_cache["data"]

AUTH_SERVICE_URL = os.environ.get("AUTH_SERVICE_URL", "http://localhost:5001")


def get_verified_user(auth_header):
    """Ask auth-service who this token belongs to, and whether they're an admin.
    Returns (username, is_admin) or (None, False) if invalid.
    """
    if not auth_header:
        return None, False
    try:
        resp = requests.get(f"{AUTH_SERVICE_URL}/verify", headers={"Authorization": auth_header}, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("valid"):
                return data.get("username"), bool(data.get("is_admin"))
        return None, False
    except requests.RequestException:
        return None, False


def place_with_rating_summary(place, reviews_by_place=None):
    """Attach average rating + review count to a place dict.
    If reviews_by_place (a dict of place_id -> list of reviews) is provided,
    use it instead of querying the database again (avoids N+1 queries).
    """
    if reviews_by_place is not None:
        reviews = reviews_by_place.get(place.get("id"), [])
    else:
        reviews = get_reviews_for_place(place.get("id"))
    result = dict(place)
    if reviews:
        result["average_rating"] = round(sum(r["rating"] for r in reviews) / len(reviews), 1)
        result["review_count"] = len(reviews)
    else:
        result["average_rating"] = place.get("rating")
        result["review_count"] = 0
    return result


def _group_reviews_by_place():
    """Fetch ALL reviews once, then group them by place_id in memory."""
    grouped = {}
    for review in get_all_reviews():
        grouped.setdefault(review["place_id"], []).append(review)
    return grouped


# ---------------------------------------------------------------------------
# Browse / search
# ---------------------------------------------------------------------------

@app.route("/destinations", methods=["GET"])
def search_places():
    q = request.args.get("q", "").strip().lower()
    category = request.args.get("category", "").strip().lower()
    town = request.args.get("town", "").strip().lower()
    tag = request.args.get("tag", "").strip().lower()
    min_rating_str = request.args.get("min_rating", "").strip()

    min_rating = None
    if min_rating_str:
        try:
            min_rating = float(min_rating_str)
        except ValueError:
            return jsonify({"error": "min_rating must be a number"}), 400

    places = get_cached_places()
    reviews_by_place = _group_reviews_by_place()
    results = []
    for place in places:
        if q:
            searchable = " ".join([
                place.get("name", ""), place.get("address", ""), place.get("description", ""),
            ]).lower()
            if q not in searchable:
                continue
        if category and category != place.get("category", "").lower():
            continue
        if town and town != place.get("town", "").lower():
            continue
        if tag and tag not in [t.lower() for t in place.get("tags", [])]:
            continue
        if min_rating is not None and (place.get("rating") or 0) < min_rating:
            continue
        results.append(place_with_rating_summary(place, reviews_by_place))

    return jsonify(results), 200


@app.route("/destinations/<place_id>", methods=["GET"])
def get_place(place_id):
    place = get_place_by_id(place_id)
    if not place:
        return jsonify({"error": "place not found"}), 404
    return jsonify(place_with_rating_summary(place)), 200


# ---------------------------------------------------------------------------
# Admin CRUD
# ---------------------------------------------------------------------------

@app.route("/destinations", methods=["POST"])
def create_place():
    username, is_admin = get_verified_user(request.headers.get("Authorization", ""))
    if not username:
        return jsonify({"error": "authentication required"}), 401
    if not is_admin:
        return jsonify({"error": "admin access required"}), 403

    data = request.get_json(silent=True) or {}
    name = data.get("name", "").strip()
    if not name:
        return jsonify({"error": "name is required"}), 400

    place = {
        "id": str(uuid.uuid4()),
        "name": name,
        "category": data.get("category", "").strip(),
        "town": data.get("town", "").strip(),
        "address": data.get("address", "").strip(),
        "description": data.get("description", "").strip(),
        "tags": data.get("tags", []),
        "phone": data.get("phone"),
        "latitude": data.get("latitude"),
        "longitude": data.get("longitude"),
        "rating": data.get("rating"),
        "image_url": data.get("image_url", ""),
        "details": data.get("details", []),
        "added_by": username,
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
    add_place(place)
    _places_cache["data"] = None
    return jsonify(place), 201


@app.route("/destinations/<place_id>", methods=["PUT"])
def edit_place(place_id):
    username, is_admin = get_verified_user(request.headers.get("Authorization", ""))
    if not username:
        return jsonify({"error": "authentication required"}), 401
    if not is_admin:
        return jsonify({"error": "admin access required"}), 403

    data = request.get_json(silent=True) or {}
    allowed_fields = ["name", "category", "town", "address", "description", "tags", "phone", "latitude", "longitude", "rating", "image_url", "details"]
    updates = {k: v for k, v in data.items() if k in allowed_fields}

    updated = update_place(place_id, updates)
    _places_cache["data"] = None
    if not updated:
        return jsonify({"error": "place not found"}), 404
    return jsonify(updated), 200


@app.route("/destinations/<place_id>", methods=["DELETE"])
def remove_place(place_id):
    username, is_admin = get_verified_user(request.headers.get("Authorization", ""))
    if not username:
        return jsonify({"error": "authentication required"}), 401
    if not is_admin:
        return jsonify({"error": "admin access required"}), 403

    deleted = delete_place(place_id)
    _places_cache["data"] = None
    if not deleted:
        return jsonify({"error": "place not found"}), 404
    return jsonify({"message": "place deleted"}), 200


# ---------------------------------------------------------------------------
# Reviews (any logged-in user)
# ---------------------------------------------------------------------------

@app.route("/destinations/<place_id>/reviews", methods=["POST"])
def submit_review(place_id):
    username, _ = get_verified_user(request.headers.get("Authorization", ""))
    if not username:
        return jsonify({"error": "authentication required"}), 401

    place = get_place_by_id(place_id)
    if not place:
        return jsonify({"error": "place not found"}), 404

    data = request.get_json(silent=True) or {}
    rating = data.get("rating")
    comment = data.get("comment", "").strip()

    try:
        rating = int(rating)
    except (TypeError, ValueError):
        return jsonify({"error": "rating must be a whole number from 1 to 5"}), 400
    if rating < 1 or rating > 5:
        return jsonify({"error": "rating must be between 1 and 5"}), 400

    review = {
        "id": str(uuid.uuid4()),
        "place_id": place_id,
        "username": username,
        "rating": rating,
        "comment": comment,
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
    add_review(review)
    return jsonify(review), 201


@app.route("/destinations/<place_id>/reviews", methods=["GET"])
def list_reviews(place_id):
    place = get_place_by_id(place_id)
    if not place:
        return jsonify({"error": "place not found"}), 404
    reviews = get_reviews_for_place(place_id)
    return jsonify(reviews), 200

@app.route("/settings", methods=["GET"])
def get_site_settings():
    """Public: anyone can read the current fare rates."""
    return jsonify(get_settings()), 200


@app.route("/settings", methods=["PUT"])
def update_site_settings():
    """Admin-only: update fare rates and other site settings."""
    username, is_admin = get_verified_user(request.headers.get("Authorization", ""))
    if not username:
        return jsonify({"error": "authentication required"}), 401
    if not is_admin:
        return jsonify({"error": "admin access required"}), 403

    data = request.get_json(silent=True) or {}
    allowed = {"taxi_rate_per_km", "bike_rate_per_km"}
    updates = {k: v for k, v in data.items() if k in allowed}
    updated = update_settings(updates)
    return jsonify(updated), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5002, debug=False)