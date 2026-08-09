"""
services/destinations-service/models.py
Places and reviews data access, backed by MongoDB Atlas.
"""
import os
from pymongo import MongoClient
from dotenv import load_dotenv

_BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv(os.path.join(_BASE_DIR, ".env"))

MONGO_URI = os.environ.get("MONGO_URI")
_client = MongoClient(MONGO_URI)
_db = _client["globetrotter"]
_places = _db["places"]
_reviews = _db["reviews"]
_settings = _db["settings"]


def get_all_places():
    return list(_places.find({}, {"_id": 0}))


def get_place_by_id(place_id):
    return _places.find_one({"id": place_id}, {"_id": 0})


def add_place(place):
    _places.insert_one(dict(place))
    return place


def update_place(place_id, updates):
    result = _places.find_one_and_update(
        {"id": place_id}, {"$set": updates}, return_document=True
    )
    if result:
        result.pop("_id", None)
    return result


def delete_place(place_id):
    result = _places.delete_one({"id": place_id})
    return result.deleted_count > 0


def get_reviews_for_place(place_id):
    return list(_reviews.find({"place_id": place_id}, {"_id": 0}))

def get_all_reviews():
    return list(_reviews.find({}, {"_id": 0}))

def add_review(review):
    _reviews.insert_one(dict(review))
    return review

def get_settings():
    """Site-wide settings (fare rates, etc). Single document."""
    settings = _settings.find_one({"_id": "site_settings"}, {"_id": 0})
    if not settings:
        return {"taxi_rate_per_km": None, "bike_rate_per_km": None}
    return settings


def update_settings(updates):
    _settings.update_one(
        {"_id": "site_settings"},
        {"$set": updates},
        upsert=True,
    )
    return get_settings()