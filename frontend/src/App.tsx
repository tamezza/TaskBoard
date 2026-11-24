import { useEffect, useState } from "react";
import { ApiError, api, getToken, setToken } from "./api";
import type { BoardSummary } from "./api";
import { BoardView } from "./BoardView";

function LoginForm({ onLoggedIn }: { onLoggedIn: () => void }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  async function handle(mode: "login" | "register") {
    setError("");
    try {
      if (mode === "register") await api.register(email, password);
      await api.login(email, password);
      onLoggedIn();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong");
    }
  }

  return (
    <form
      className="panel"
      onSubmit={(event) => {
        event.preventDefault();
        void handle("login");
      }}
    >
      <h1>TaskBoard</h1>
      <input
        type="email"
        placeholder="Email"
        value={email}
        onChange={(event) => setEmail(event.target.value)}
        required
      />
      <input
        type="password"
        placeholder="Password (8 characters or more)"
        value={password}
        onChange={(event) => setPassword(event.target.value)}
        minLength={8}
        required
      />
      <button type="submit">Log in</button>
      <button type="button" onClick={() => void handle("register")}>
        Create account
      </button>
      {error && <p role="alert">{error}</p>}
    </form>
  );
}

type BoardsProps = {
  setLoggedIn: (value: boolean) => void;
  onOpen: (boardId: number) => void;
};

function Boards({ setLoggedIn, onOpen }: BoardsProps) {
  const [boards, setBoards] = useState<BoardSummary[]>([]);
  const [archived, setArchived] = useState<BoardSummary[]>([]);
  const [showArchived, setShowArchived] = useState(false);
  const [name, setName] = useState("");
  // The board whose "Delete" was clicked and is waiting for confirmation
  const [confirming, setConfirming] = useState<number | null>(null);
  const [error, setError] = useState("");

  function logout() {
    setToken(null);
    setLoggedIn(false);
  }

  useEffect(() => {
    Promise.all([api.listBoards(), api.listBoards(true)])
      .then(([active, hidden]) => {
        setBoards(active);
        setArchived(hidden);
      })
      .catch(() => {
        setToken(null);
        setLoggedIn(false);
      });
  }, [setLoggedIn]);

  async function addBoard() {
    const board = await api.createBoard(name);
    setBoards([...boards, board]);
    setName("");
  }

  async function removeBoard(boardId: number) {
    try {
      await api.deleteBoard(boardId);
      setBoards(boards.filter((board) => board.id !== boardId));
      setArchived(archived.filter((board) => board.id !== boardId));
      setError("");
    } catch {
      setError("That board could not be deleted");
    }
    setConfirming(null);
  }

  // Archiving and restoring are the same request with a different value:
  // the board leaves one list and joins the other.
  async function moveBoard(board: BoardSummary, toArchive: boolean) {
    try {
      const updated = await api.setArchived(board.id, toArchive);
      const [from, to] = toArchive ? [boards, archived] : [archived, boards];
      const without = from.filter((item) => item.id !== board.id);
      const withIt = [...to, updated].sort((a, b) => a.id - b.id);
      setBoards(toArchive ? without : withIt);
      setArchived(toArchive ? withIt : without);
      setError("");
    } catch {
      setError("That change could not be saved");
    }
  }

  function row(board: BoardSummary) {
    if (confirming === board.id) {
      return (
        <li key={board.id} className="confirm">
          <span>Delete "{board.name}" and all its cards?</span>
          <button
            type="button"
            className="danger"
            onClick={() => void removeBoard(board.id)}
          >
            Delete
          </button>
          <button type="button" onClick={() => setConfirming(null)}>
            Cancel
          </button>
        </li>
      );
    }
    return (
      <li key={board.id}>
        <button
          type="button"
          className="open"
          onClick={() => onOpen(board.id)}
        >
          {board.name}
        </button>
        <button
          type="button"
          onClick={() => void moveBoard(board, !board.archived)}
        >
          {board.archived ? "Restore" : "Archive"}
        </button>
        <button
          type="button"
          onClick={() => setConfirming(board.id)}
          aria-label={`Delete board ${board.name}`}
        >
          ✕
        </button>
      </li>
    );
  }

  return (
    <main className="panel">
      <h1>Your boards</h1>
      {error && <p role="alert">{error}</p>}
      <ul className="board-list">{boards.map(row)}</ul>
      <form
        onSubmit={(event) => {
          event.preventDefault();
          void addBoard();
        }}
      >
        <input
          placeholder="New board name"
          value={name}
          onChange={(event) => setName(event.target.value)}
          required
        />
        <button type="submit">Add board</button>
      </form>
      {archived.length > 0 && (
        <button
          type="button"
          className="link"
          onClick={() => setShowArchived(!showArchived)}
        >
          {showArchived ? "Hide" : "Show"} archived boards ({archived.length})
        </button>
      )}
      {showArchived && archived.length > 0 && (
        <ul className="board-list archived">{archived.map(row)}</ul>
      )}
      <button type="button" onClick={logout}>
        Log out
      </button>
    </main>
  );
}

export default function App() {
  const [loggedIn, setLoggedIn] = useState(getToken() !== null);
  const [openBoard, setOpenBoard] = useState<number | null>(null);

  if (!loggedIn) return <LoginForm onLoggedIn={() => setLoggedIn(true)} />;
  if (openBoard !== null) {
    return <BoardView boardId={openBoard} onBack={() => setOpenBoard(null)} />;
  }
  return <Boards setLoggedIn={setLoggedIn} onOpen={setOpenBoard} />;
}
