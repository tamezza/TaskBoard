from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_create_and_complete_task():
    response = client.post("/tasks", json={"title": "write tests"})
    assert response.status_code == 201
    task_id = response.json()["id"]

    response = client.patch(f"/tasks/{task_id}/done")
    assert response.status_code == 200
    assert response.json()["done"] is True


def test_unknown_task_returns_404():
    assert client.get("/tasks/9999").status_code == 404
