import { useEffect, useState } from "react";
import { api } from "./api";
import type { Board, Card, Column } from "./api";

type Props = { boardId: number; onBack: () => void };

// Where the dragged card would land if it were dropped now.
// beforeCardId null means "at the end of the column".
type DropTarget = { columnId: number; beforeCardId: number | null };

// The position to send to the API. The server takes the card out of its
// old place first, then inserts it, so we count without the dragged card.
function dropPosition(column: Column, dragged: Card, target: DropTarget) {
  const others = column.cards.filter((card) => card.id !== dragged.id);
  if (target.beforeCardId === null) return others.length;
  const index = others.findIndex((card) => card.id === target.beforeCardId);
  return index === -1 ? others.length : index;
}

export function BoardView({ boardId, onBack }: Props) {
  const [board, setBoard] = useState<Board | null>(null);
  const [error, setError] = useState("");
  const [dragged, setDragged] = useState<Card | null>(null);
  const [target, setTarget] = useState<DropTarget | null>(null);

  useEffect(() => {
    let ignore = false;
    api
      .getBoard(boardId)
      .then((data) => {
        if (!ignore) setBoard(data);
      })
      .catch(() => {
        if (!ignore) setError("Could not load this board");
      });
    return () => {
      ignore = true;
    };
  }, [boardId]);

  async function run(action: () => Promise<unknown>) {
    try {
      await action();
      setError("");
    } catch {
      setError("That change could not be saved");
    }
    try {
      setBoard(await api.getBoard(boardId));
    } catch {
      setError("Could not load this board");
    }
  }

  // dragover fires many times a second: only change state when the
  // target really changes, so React does not redraw for nothing.
  function aim(next: DropTarget) {
    setTarget((current) =>
      current?.columnId === next.columnId &&
      current.beforeCardId === next.beforeCardId
        ? current
        : next,
    );
  }

  function endDrag() {
    setDragged(null);
    setTarget(null);
  }

  function drop(column: Column) {
    if (dragged && target && target.columnId === column.id) {
      const position = dropPosition(column, dragged, target);
      const unchanged =
        dragged.column_id === column.id &&
        column.cards.findIndex((card) => card.id === dragged.id) === position;
      if (!unchanged) {
        void run(() => api.moveCard(dragged.id, column.id, position));
      }
    }
    endDrag();
  }

  if (error && !board) {
    return (
      <main className="panel">
        <p role="alert">{error}</p>
        <button type="button" onClick={onBack}>
          Back to boards
        </button>
      </main>
    );
  }
  if (!board) return <main className="panel">Loading…</main>;

  return (
    <main className="board">
      <header>
        <button type="button" onClick={onBack}>
          ← Boards
        </button>
        <h1>{board.name}</h1>
      </header>
      {error && <p role="alert">{error}</p>}
      <div className="columns">
        {board.columns.map((column, index) => (
          <ColumnView
            key={column.id}
            column={column}
            previous={board.columns[index - 1]}
            next={board.columns[index + 1]}
            run={run}
            dragged={dragged}
            target={target?.columnId === column.id ? target : null}
            onDragStart={setDragged}
            onDragOver={(beforeCardId) =>
              aim({ columnId: column.id, beforeCardId })
            }
            onDrop={() => drop(column)}
            onDragEnd={endDrag}
          />
        ))}
      </div>
    </main>
  );
}

type ColumnProps = {
  column: Column;
  previous?: Column;
  next?: Column;
  run: (action: () => Promise<unknown>) => Promise<void>;
  dragged: Card | null;
  target: DropTarget | null;
  onDragStart: (card: Card) => void;
  onDragOver: (beforeCardId: number | null) => void;
  onDrop: () => void;
  onDragEnd: () => void;
};

function ColumnView({
  column,
  previous,
  next,
  run,
  dragged,
  target,
  onDragStart,
  onDragOver,
  onDrop,
  onDragEnd,
}: ColumnProps) {
  const [title, setTitle] = useState("");

  function move(card: Card, destination: Column) {
    void run(() =>
      api.moveCard(card.id, destination.id, destination.cards.length),
    );
  }

  return (
    <section
      className={target ? "column drop-target" : "column"}
      onDragOver={(event) => {
        if (!dragged) return;
        event.preventDefault(); // without this the browser refuses the drop
        onDragOver(null);
      }}
      onDrop={(event) => {
        event.preventDefault();
        onDrop();
      }}
    >
      <h2>
        {column.name} <span>{column.cards.length}</span>
      </h2>
      {column.cards.map((card) => {
        const classes = ["card"];
        if (dragged?.id === card.id) classes.push("dragging");
        if (target?.beforeCardId === card.id) classes.push("drop-before");
        return (
          <article
            key={card.id}
            className={classes.join(" ")}
            draggable
            onDragStart={(event) => {
              event.dataTransfer.setData("text/plain", String(card.id));
              event.dataTransfer.effectAllowed = "move";
              onDragStart(card);
            }}
            onDragEnd={onDragEnd}
            onDragOver={(event) => {
              if (!dragged) return;
              event.preventDefault();
              event.stopPropagation(); // the column must not also answer
              onDragOver(card.id);
            }}
          >
            <p>{card.title}</p>
            {card.due_date && <small>Due {card.due_date}</small>}
            <div className="actions">
              <button
                type="button"
                disabled={!previous}
                onClick={() => previous && move(card, previous)}
                aria-label="Move left"
              >
                ◀
              </button>
              <button
                type="button"
                disabled={!next}
                onClick={() => next && move(card, next)}
                aria-label="Move right"
              >
                ▶
              </button>
              <button
                type="button"
                onClick={() => void run(() => api.deleteCard(card.id))}
                aria-label="Delete card"
              >
                ✕
              </button>
            </div>
          </article>
        );
      })}
      <form
        onSubmit={(event) => {
          event.preventDefault();
          void run(() => api.createCard(column.id, title));
          setTitle("");
        }}
      >
        <input
          placeholder="Add a card"
          value={title}
          onChange={(event) => setTitle(event.target.value)}
          required
        />
      </form>
    </section>
  );
}
