"""
tests/test_auth_service.py
Automated tests for auth-service (register, login, verify, get_user).

These tests load auth-service's Flask app directly (via its test client)
rather than needing the real server running — this is standard practice
for fast, isolated unit tests.
"""
import sys
import os
import importlib.util
import tempfile
import pytest

# Path to the auth-service folder
AUTH_SERVICE_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "services", "auth-service"
)


@pytest.fixture
def client(monkeypatch, tmp_path):
    """Spin up auth-service's Flask app with a temporary, throwaway
    users.json file, so tests never touch real project data.
    """
    sys.path.insert(0, AUTH_SERVICE_DIR)

    # Load models.py fresh
    models_spec = importlib.util.spec_from_file_location(
        "auth_models", os.path.join(AUTH_SERVICE_DIR, "models.py")
    )
    auth_models = importlib.util.module_from_spec(models_spec)
    models_spec.loader.exec_module(auth_models)

    # Redirect its data file to a temp location for this test only
    temp_users_file = tmp_path / "users.json"
    monkeypatch.setattr(auth_models, "USERS_FILE", str(temp_users_file))

    # Load main.py, but make sure it uses our patched models module
    sys.modules["models"] = auth_models
    main_spec = importlib.util.spec_from_file_location(
        "auth_main", os.path.join(AUTH_SERVICE_DIR, "main.py")
    )
    auth_main = importlib.util.module_from_spec(main_spec)
    main_spec.loader.exec_module(auth_main)

    auth_main.app.config["TESTING"] = True
    with auth_main.app.test_client() as test_client:
        yield test_client

    sys.path.remove(AUTH_SERVICE_DIR)
    del sys.modules["models"]


def test_register_new_user(client):
    resp = client.post("/register", json={
        "username": "alice_test", "password": "pass123", "preferences": ["beach"]
    })
    assert resp.status_code == 201
    assert resp.get_json()["username"] == "alice_test"


def test_register_duplicate_user_fails(client):
    client.post("/register", json={"username": "bob_test", "password": "pass123"})
    resp = client.post("/register", json={"username": "bob_test", "password": "pass123"})
    assert resp.status_code == 409


def test_register_missing_fields_fails(client):
    resp = client.post("/register", json={"username": "no_password"})
    assert resp.status_code == 400


def test_login_success_returns_token(client):
    client.post("/register", json={"username": "carol_test", "password": "pass123"})
    resp = client.post("/login", json={"username": "carol_test", "password": "pass123"})
    assert resp.status_code == 200
    assert "token" in resp.get_json()


def test_login_wrong_password_fails(client):
    client.post("/register", json={"username": "dave_test", "password": "pass123"})
    resp = client.post("/login", json={"username": "dave_test", "password": "wrong"})
    assert resp.status_code == 401


def test_verify_valid_token(client):
    client.post("/register", json={"username": "eve_test", "password": "pass123"})
    login_resp = client.post("/login", json={"username": "eve_test", "password": "pass123"})
    token = login_resp.get_json()["token"]

    resp = client.get("/verify", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.get_json()["valid"] is True
    assert resp.get_json()["username"] == "eve_test"


def test_verify_missing_token_fails(client):
    resp = client.get("/verify")
    assert resp.status_code == 401