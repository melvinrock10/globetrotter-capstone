"""
tests/test_destinations_service.py
Automated tests for destinations-service (search/filter logic).
"""
import sys
import os
import importlib.util
import json
import pytest

DEST_SERVICE_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "services", "destinations-service"
)

SAMPLE_DATA = [
    {"id": "bali-test", "name": "Bali Test Hospital", "category": "hospital", "town": "Buea",
     "address": "Test Rd", "description": "Test hospital", "tags": ["emergency"], "rating": 4.0},
    {"id": "paris-test", "name": "Paris Test Hotel", "category": "hotel", "town": "Limbe",
     "address": "Test Ave", "description": "Test hotel", "tags": ["pool"], "rating": 3.0},
    {"id": "bangkok-test", "name": "Bangkok Street Food Spot", "category": "restaurant", "town": "Buea",
     "address": "Test St", "description": "Street food specialist", "tags": ["food", "budget"], "rating": 4.5},
]


@pytest.fixture
def client(monkeypatch, tmp_path):
    sys.path.insert(0, DEST_SERVICE_DIR)

    models_spec = importlib.util.spec_from_file_location(
        "dest_models", os.path.join(DEST_SERVICE_DIR, "models.py")
    )
    dest_models = importlib.util.module_from_spec(models_spec)
    models_spec.loader.exec_module(dest_models)

    temp_file = tmp_path / "destinations.json"
    temp_file.write_text(json.dumps(SAMPLE_DATA), encoding="utf-8")
    monkeypatch.setattr(dest_models, "DESTINATIONS_FILE", str(temp_file))

    temp_reviews_file = tmp_path / "reviews.json"
    monkeypatch.setattr(dest_models, "REVIEWS_FILE", str(temp_reviews_file))

    sys.modules["models"] = dest_models
    main_spec = importlib.util.spec_from_file_location(
        "dest_main", os.path.join(DEST_SERVICE_DIR, "main.py")
    )
    dest_main = importlib.util.module_from_spec(main_spec)
    main_spec.loader.exec_module(dest_main)

    dest_main.app.config["TESTING"] = True
    with dest_main.app.test_client() as test_client:
        yield test_client

    sys.path.remove(DEST_SERVICE_DIR)
    del sys.modules["models"]


def test_get_all_destinations(client):
    resp = client.get("/destinations")
    assert resp.status_code == 200
    assert len(resp.get_json()) == 3


def test_filter_by_tag(client):
    resp = client.get("/destinations?tag=food")
    data = resp.get_json()
    assert len(data) == 1
    assert data[0]["name"] == "Bangkok Street Food Spot"


def test_filter_by_category(client):
    resp = client.get("/destinations?category=hotel")
    data = resp.get_json()
    assert len(data) == 1
    assert data[0]["name"] == "Paris Test Hotel"


def test_filter_by_town(client):
    resp = client.get("/destinations?town=Buea")
    data = resp.get_json()
    assert len(data) == 2


def test_free_text_search(client):
    resp = client.get("/destinations?q=street food")
    data = resp.get_json()
    assert len(data) == 1
    assert data[0]["name"] == "Bangkok Street Food Spot"


def test_filter_by_min_rating(client):
    resp = client.get("/destinations?min_rating=4")
    data = resp.get_json()
    names = [d["name"] for d in data]
    assert "Bali Test Hospital" in names
    assert "Bangkok Street Food Spot" in names
    assert "Paris Test Hotel" not in names


def test_invalid_min_rating_returns_400(client):
    resp = client.get("/destinations?min_rating=notanumber")
    assert resp.status_code == 400