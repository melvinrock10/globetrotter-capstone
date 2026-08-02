"""
services/itineraries-service/models.py
Itineraries data access, backed by MongoDB Atlas.
"""
import os
from pymongo import MongoClient
from dotenv import load_dotenv

_BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv(os.path.join(_BASE_DIR, ".env"))

MONGO_URI = os.environ.get("MONGO_URI")
_client = MongoClient(MONGO_URI)
_db = _client["globetrotter"]
_itineraries = _db["itineraries"]


def get_all_itineraries():
    return list(_itineraries.find({}, {"_id": 0}))


def get_itineraries_for_user(username):
    return list(_itineraries.find({"username": username}, {"_id": 0}))


def save_itinerary(itinerary):
    _itineraries.insert_one(dict(itinerary))
    return itinerary