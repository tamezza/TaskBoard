from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def auth_headers(email: str) -> dict[str, str]:
    credentials = {"email": email, "password": "a-long-test-password"}
    client.post("/auth/register", json=credentials)
    token = client.post("/auth/login", json=credentials).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def new_board(headers: dict, name: str) -> dict:
    return client.post("/boards", json={"name": name}, headers=headers).json()


def add_card(headers: dict, column_id: int, title: str) -> dict:
    url = f"/columns/{column_id}/cards"
    return client.post(url, json={"title": title}, headers=headers).json()


def titles(column: dict) -> list[str]:
    return [card["title"] for card in column["cards"]]


def test_new_board_has_three_columns():
    headers = auth_headers("alice@example.com")
    response = client.post("/boards", json={"name": "Thesis"}, headers=headers)
    assert response.status_code == 201
    names = [column["name"] for column in response.json()["columns"]]
    assert names == ["To do", "Doing", "Done"]


def test_create_and_move_cards():
    headers = auth_headers("alice@example.com")
    board = new_board(headers, "Work")
    todo, doing, _ = board["columns"]
    add_card(headers, todo["id"], "A")
    card_b = add_card(headers, todo["id"], "B")
    card_c = add_card(headers, todo["id"], "C")

    move = {"column_id": doing["id"], "position": 0}
    url = f"/cards/{card_b['id']}/move"
    assert client.post(url, json=move, headers=headers).status_code == 200

    move = {"column_id": todo["id"], "position": 0}
    client.post(f"/cards/{card_c['id']}/move", json=move, headers=headers)

    board = client.get(f"/boards/{board['id']}", headers=headers).json()
    todo, doing, _ = board["columns"]
    assert titles(todo) == ["C", "A"]
    assert titles(doing) == ["B"]


def test_users_cannot_touch_each_others_boards():
    alice = auth_headers("alice@example.com")
    mallory = auth_headers("mallory@example.com")
    board = new_board(alice, "Private")
    column_id = board["columns"][0]["id"]
    card = add_card(alice, column_id, "Secret")

    board_url = f"/boards/{board['id']}"
    card_url = f"/cards/{card['id']}"
    cards_url = f"/columns/{column_id}/cards"
    assert client.get(board_url, headers=mallory).status_code == 404
    assert client.delete(board_url, headers=mallory).status_code == 404
    assert client.delete(card_url, headers=mallory).status_code == 404
    response = client.post(cards_url, json={"title": "x"}, headers=mallory)
    assert response.status_code == 404
    assert client.get("/boards", headers=mallory).json() == []

    assert client.get(board_url, headers=alice).status_code == 200


def test_boards_require_login():
    assert client.get("/boards").status_code == 401

def test_unknown_fields_are_rejected():
    headers = auth_headers("alice@example.com")
    board = new_board(headers, "Strict")
    card = add_card(headers, board["columns"][0]["id"], "A")

    body = {"column_id": 2, "position": 0}
    response = client.patch(f"/cards/{card['id']}", json=body, headers=headers)
    assert response.status_code == 422
