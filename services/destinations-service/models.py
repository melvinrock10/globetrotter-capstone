"""
services/destinations-service/models.py
Reads the shared destinations catalogue from data/destinations.json.
"""
import json
import os

_BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = os.environ.get("DATA_DIR", os.path.join(_BASE_DIR, "data"))
DESTINATIONS_FILE = os.path.join(DATA_DIR, "destinations.json")


def get_all_destinations():
    if not os.path.exists(DESTINATIONS_FILE):
        return []
    with open(DESTINATIONS_FILE, "r", encoding="utf-8") as fh:
        content = fh.read().strip()
        return json.loads(content) if content else []