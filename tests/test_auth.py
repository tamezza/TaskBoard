from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
USER = {"email": "ada@example.com", "password": "correct-horse-battery"}


def test_register_login_and_me():
    assert client.post("/auth/register", json=USER).status_code == 201
    assert client.post("/auth/register", json=USER).status_code == 409

    response = client.post("/auth/login", json=USER)
    assert response.status_code == 200
    token = response.json()["access_token"]

    headers = {"Authorization": f"Bearer {token}"}
    response = client.get("/auth/me", headers=headers)
    assert response.status_code == 200
    assert response.json()["email"] == USER["email"]
    assert "password" not in response.text


def test_wrong_password_is_rejected():
    client.post("/auth/register", json={**USER, "email": "bob@example.com"})
    bad = {"email": "bob@example.com", "password": "wrong-password-123"}
    assert client.post("/auth/login", json=bad).status_code == 401


def test_me_requires_a_valid_token():
    assert client.get("/auth/me").status_code == 401
    headers = {"Authorization": "Bearer not-a-real-token"}
    assert client.get("/auth/me", headers=headers).status_code == 401
