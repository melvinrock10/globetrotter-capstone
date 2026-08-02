"""
migrate_to_mongo.py
One-time script: copies existing data from data/*.json into MongoDB Atlas.
Run this ONCE, then MongoDB becomes the source of truth going forward.
"""
import os
import json
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv(".env")
MONGO_URI = os.environ.get("MONGO_URI")

if not MONGO_URI:
    print("ERROR: MONGO_URI not found. Make sure .env exists with MONGO_URI set.")
    exit(1)

client = MongoClient(MONGO_URI)
db = client["globetrotter"]


def load_json(path):
    if not os.path.exists(path):
        print(f"  (skipped, file not found: {path})")
        return []
    with open(path, "r", encoding="utf-8") as fh:
        content = fh.read().strip()
        return json.loads(content) if content else []


def migrate(collection_name, filepath):
    data = load_json(filepath)
    if not data:
        print(f"{collection_name}: nothing to migrate.")
        return
    collection = db[collection_name]
    inserted = 0
    for item in data:
        # Avoid duplicate inserts if this script is run more than once
        key_field = "username" if collection_name == "users" else "id"
        if key_field in item and collection.find_one({key_field: item[key_field]}):
            continue
        collection.insert_one(dict(item))
        inserted += 1
    print(f"{collection_name}: inserted {inserted} new record(s) (of {len(data)} total in file).")


print("Starting migration to MongoDB Atlas...\n")
migrate("users", "data/users.json")
migrate("places", "data/destinations.json")
migrate("itineraries", "data/itineraries.json")
migrate("reviews", "data/reviews.json")
print("\nDone. Check your MongoDB Atlas 'globetrotter' database to confirm.")