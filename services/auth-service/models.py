"""
services/auth-service/models.py
User data access, backed by MongoDB Atlas.
"""
import os
from pymongo import MongoClient
from dotenv import load_dotenv

_BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv(os.path.join(_BASE_DIR, ".env"))

MONGO_URI = os.environ.get("MONGO_URI")
_client = MongoClient(MONGO_URI)
_db = _client["globetrotter"]
_users = _db["users"]


def get_all_users():
    return list(_users.find({}, {"_id": 0}))


def get_user_by_username(username):
    return _users.find_one({"username": username}, {"_id": 0})


def save_user(user):
    _users.insert_one(dict(user))
    return user


def delete_user(username):
    result = _users.delete_one({"username": username})
    return result.deleted_count > 0