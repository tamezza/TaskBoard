from datetime import date

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import CurrentUser
from app.deps import DbSession
from app.models import Board, BoardColumn, Card, User

router = APIRouter(tags=["boards"])

DEFAULT_COLUMNS = ["To do", "Doing", "Done"]


class BoardIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)

    model_config = {"extra": "forbid"}


class BoardUpdate(BaseModel):
    archived: bool

    model_config = {"extra": "forbid"}


class CardIn(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = None
    due_date: date | None = None

    model_config = {"extra": "forbid"}


class CardUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    due_date: date | None = None

    model_config = {"extra": "forbid"}


class CardMove(BaseModel):
    column_id: int
    position: int = Field(ge=0)

    model_config = {"extra": "forbid"}


class CardOut(BaseModel):
    id: int
    title: str
    description: str | None
    due_date: date | None
    position: int
    column_id: int

    model_config = {"from_attributes": True}


class ColumnOut(BaseModel):
    id: int
    name: str
    position: int
    cards: list[CardOut]

    model_config = {"from_attributes": True}


class BoardSummary(BaseModel):
    id: int
    name: str
    archived: bool

    model_config = {"from_attributes": True}


class BoardOut(BoardSummary):
    columns: list[ColumnOut]


def get_board(db: Session, user: User, board_id: int) -> Board:
    board = db.get(Board, board_id)
    if board is None or board.owner_id != user.id:
        raise HTTPException(status_code=404, detail="board not found")
    return board


def get_column(db: Session, user: User, column_id: int) -> BoardColumn:
    column = db.get(BoardColumn, column_id)
    if column is None or column.board.owner_id != user.id:
        raise HTTPException(status_code=404, detail="column not found")
    return column


def get_card(db: Session, user: User, card_id: int) -> Card:
    card = db.get(Card, card_id)
    if card is None or card.column.board.owner_id != user.id:
        raise HTTPException(status_code=404, detail="card not found")
    return card


@router.post("/boards", response_model=BoardOut, status_code=201)
def create_board(body: BoardIn, user: CurrentUser, db: DbSession):
    board = Board(name=body.name, owner_id=user.id)
    board.columns = [
        BoardColumn(name=name, position=index)
        for index, name in enumerate(DEFAULT_COLUMNS)
    ]
    db.add(board)
    db.commit()
    db.refresh(board)
    return board


@router.get("/boards", response_model=list[BoardSummary])
def list_boards(user: CurrentUser, db: DbSession, archived: bool = False):
    query = (
        select(Board)
        .where(Board.owner_id == user.id, Board.archived == archived)
        .order_by(Board.id)
    )
    return db.scalars(query).all()


@router.get("/boards/{board_id}", response_model=BoardOut)
def read_board(board_id: int, user: CurrentUser, db: DbSession):
    return get_board(db, user, board_id)


@router.patch("/boards/{board_id}", response_model=BoardSummary)
def update_board(board_id: int, body: BoardUpdate, user: CurrentUser, db: DbSession):
    board = get_board(db, user, board_id)
    board.archived = body.archived
    db.commit()
    db.refresh(board)
    return board


@router.delete("/boards/{board_id}", status_code=204)
def delete_board(board_id: int, user: CurrentUser, db: DbSession):
    db.delete(get_board(db, user, board_id))
    db.commit()


@router.post("/columns/{column_id}/cards", response_model=CardOut, status_code=201)
def create_card(column_id: int, body: CardIn, user: CurrentUser, db: DbSession):
    column = get_column(db, user, column_id)
    card = Card(**body.model_dump(), position=len(column.cards))
    column.cards.append(card)
    db.commit()
    db.refresh(card)
    return card


@router.patch("/cards/{card_id}", response_model=CardOut)
def update_card(card_id: int, body: CardUpdate, user: CurrentUser, db: DbSession):
    card = get_card(db, user, card_id)
    changes = body.model_dump(exclude_unset=True)
    if changes.get("title", "") is None:
        raise HTTPException(status_code=422, detail="title cannot be empty")
    for field, value in changes.items():
        setattr(card, field, value)
    db.commit()
    db.refresh(card)
    return card


@router.post("/cards/{card_id}/move", response_model=CardOut)
def move_card(card_id: int, body: CardMove, user: CurrentUser, db: DbSession):
    card = get_card(db, user, card_id)
    source = card.column
    target = get_column(db, user, body.column_id)
    if target.board_id != source.board_id:
        raise HTTPException(status_code=400, detail="column is on another board")

    remaining = [item for item in source.cards if item is not card]
    destination = remaining if target is source else list(target.cards)
    destination.insert(min(body.position, len(destination)), card)

    card.column = target
    for cards in (remaining, destination):
        for index, item in enumerate(cards):
            item.position = index
    db.commit()
    db.refresh(card)
    return card


@router.delete("/cards/{card_id}", status_code=204)
def delete_card(card_id: int, user: CurrentUser, db: DbSession):
    db.delete(get_card(db, user, card_id))
    db.commit()
