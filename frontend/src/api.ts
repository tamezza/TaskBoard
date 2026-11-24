const TOKEN_KEY = "taskboard_token";

export type BoardSummary = { id: number; name: string; archived: boolean };

export type Card = {
  id: number;
  title: string;
  description: string | null;
  due_date: string | null;
  position: number;
  column_id: number;
};

export type Column = {
  id: number;
  name: string;
  position: number;
  cards: Card[];
};

export type Board = BoardSummary & { columns: Column[] };

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string | null): void {
  if (token) localStorage.setItem(TOKEN_KEY, token);
  else localStorage.removeItem(TOKEN_KEY);
}

async function request<T>(
  method: string,
  path: string,
  body?: unknown,
): Promise<T> {
  const headers: Record<string, string> = {};
  const token = getToken();
  if (token) headers["Authorization"] = `Bearer ${token}`;
  if (body !== undefined) headers["Content-Type"] = "application/json";

  const response = await fetch(`/api${path}`, {
    method,
    headers,
    body: body === undefined ? undefined : JSON.stringify(body),
  });

  if (response.status === 204) return undefined as T;
  const data = await response.json().catch(() => null);
  if (!response.ok) {
    const detail =
      typeof data?.detail === "string" ? data.detail : "Request failed";
    throw new ApiError(response.status, detail);
  }
  return data as T;
}

export const api = {
  register: (email: string, password: string) =>
    request<{ id: number }>("POST", "/auth/register", { email, password }),

  login: async (email: string, password: string) => {
    const result = await request<{ access_token: string }>(
      "POST",
      "/auth/login",
      { email, password },
    );
    setToken(result.access_token);
  },

  listBoards: (archived = false) =>
    request<BoardSummary[]>("GET", `/boards?archived=${archived}`),

  setArchived: (boardId: number, archived: boolean) =>
    request<BoardSummary>("PATCH", `/boards/${boardId}`, { archived }),

  createBoard: (name: string) =>
    request<BoardSummary>("POST", "/boards", { name }),

  getBoard: (boardId: number) => request<Board>("GET", `/boards/${boardId}`),

  deleteBoard: (boardId: number) =>
    request<void>("DELETE", `/boards/${boardId}`),

  createCard: (columnId: number, title: string) =>
    request<Card>("POST", `/columns/${columnId}/cards`, { title }),

  moveCard: (cardId: number, columnId: number, position: number) =>
    request<Card>("POST", `/cards/${cardId}/move`, {
      column_id: columnId,
      position,
    }),

  deleteCard: (cardId: number) => request<void>("DELETE", `/cards/${cardId}`),
};
