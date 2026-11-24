import { useEffect, useState } from "react";
import { ApiError, api, getToken, setToken } from "./api";
import type { BoardSummary } from "./api";

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

function Boards({ setLoggedIn }: { setLoggedIn: (value: boolean) => void }) {
  const [boards, setBoards] = useState<BoardSummary[]>([]);
  const [name, setName] = useState("");

  function logout() {
    setToken(null);
    setLoggedIn(false);
  }

  useEffect(() => {
    api
      .listBoards()
      .then(setBoards)
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

  return (
    <main className="panel">
      <h1>Your boards</h1>
      <ul>
        {boards.map((board) => (
          <li key={board.id}>{board.name}</li>
        ))}
      </ul>
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
      <button type="button" onClick={logout}>
        Log out
      </button>
    </main>
  );
}

export default function App() {
  const [loggedIn, setLoggedIn] = useState(getToken() !== null);

  return loggedIn ? (
    <Boards setLoggedIn={setLoggedIn} />
  ) : (
    <LoginForm onLoggedIn={() => setLoggedIn(true)} />
  );
}
