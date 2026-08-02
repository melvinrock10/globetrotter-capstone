"""
services/destinations-service/models.py
Data access for places (formerly "destinations") and their reviews.
"""
import json
import os

_BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = os.environ.get("DATA_DIR", os.path.join(_BASE_DIR, "data"))
DESTINATIONS_FILE = os.path.join(DATA_DIR, "destinations.json")
REVIEWS_FILE = os.path.join(DATA_DIR, "reviews.json")


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


# ---------------------------------------------------------------------------
# Places
# ---------------------------------------------------------------------------

def get_all_places():
    return _read_json(DESTINATIONS_FILE)


def get_place_by_id(place_id):
    for place in get_all_places():
        if place.get("id") == place_id:
            return place
    return None


def add_place(place):
    places = get_all_places()
    places.append(place)
    _write_json(DESTINATIONS_FILE, places)
    return place


def update_place(place_id, updates):
    places = get_all_places()
    for place in places:
        if place.get("id") == place_id:
            place.update(updates)
            _write_json(DESTINATIONS_FILE, places)
            return place
    return None


def delete_place(place_id):
    places = get_all_places()
    new_places = [p for p in places if p.get("id") != place_id]
    if len(new_places) == len(places):
        return False
    _write_json(DESTINATIONS_FILE, new_places)
    return True


# ---------------------------------------------------------------------------
# Reviews
# ---------------------------------------------------------------------------

def get_reviews_for_place(place_id):
    all_reviews = _read_json(REVIEWS_FILE)
    return [r for r in all_reviews if r.get("place_id") == place_id]


def add_review(review):
    all_reviews = _read_json(REVIEWS_FILE)
    all_reviews.append(review)
    _write_json(REVIEWS_FILE, all_reviews)
    return review