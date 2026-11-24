import { useEffect, useState } from "react";
import { api } from "./api";
import type { Board, Card, Column } from "./api";

type Props = { boardId: number; onBack: () => void };

export function BoardView({ boardId, onBack }: Props) {
  const [board, setBoard] = useState<Board | null>(null);
  const [error, setError] = useState("");

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
};

function ColumnView({ column, previous, next, run }: ColumnProps) {
  const [title, setTitle] = useState("");

  function move(card: Card, target: Column) {
    void run(() => api.moveCard(card.id, target.id, target.cards.length));
  }

  return (
    <section className="column">
      <h2>
        {column.name} <span>{column.cards.length}</span>
      </h2>
      {column.cards.map((card) => (
        <article key={card.id} className="card">
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
      ))}
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
