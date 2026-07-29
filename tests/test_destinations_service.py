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
    {"name": "Bali", "country": "Indonesia", "continent": "Asia",
     "description": "Tropical island", "tags": ["beach", "nature"], "avg_cost_per_day": 45},
    {"name": "Paris", "country": "France", "continent": "Europe",
     "description": "City of lights", "tags": ["culture", "food"], "avg_cost_per_day": 150},
    {"name": "Bangkok", "country": "Thailand", "continent": "Asia",
     "description": "Street food capital", "tags": ["food", "budget"], "avg_cost_per_day": 35},
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
    assert len(data) == 2
    names = [d["name"] for d in data]
    assert "Paris" in names and "Bangkok" in names


def test_filter_by_max_cost(client):
    resp = client.get("/destinations?max_cost=50")
    data = resp.get_json()
    names = [d["name"] for d in data]
    assert names == ["Bali", "Bangkok"]


def test_filter_by_continent(client):
    resp = client.get("/destinations?continent=Asia")
    data = resp.get_json()
    assert len(data) == 2


def test_free_text_search(client):
    resp = client.get("/destinations?q=street food")
    data = resp.get_json()
    assert len(data) == 1
    assert data[0]["name"] == "Bangkok"


def test_invalid_max_cost_returns_400(client):
    resp = client.get("/destinations?max_cost=notanumber")
    assert resp.status_code == 400