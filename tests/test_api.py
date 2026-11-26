from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.deps import get_db
from app.main import app

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ready_when_the_database_answers():
    response = client.get("/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ready"}


def test_not_ready_when_the_tables_are_missing():
    # An empty database: reachable, but never migrated
    empty = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    def empty_db():
        with Session(empty) as session:
            yield session

    app.dependency_overrides[get_db] = empty_db
    try:
        response = client.get("/ready")
        assert response.status_code == 503
        assert client.get("/health").status_code == 200
    finally:
        app.dependency_overrides.clear()