// API client for the Go expense backend. All requests use relative /api URLs,
// which Vite proxies to http://localhost:8080.

export interface Expense {
  id: number;
  amount: number;
  category: string;
  description: string;
  date: string; // YYYY-MM-DD
}

export interface NewExpense {
  amount: number;
  category: string;
  description?: string;
  date?: string; // YYYY-MM-DD
}

// Summary maps category -> total amount.
export type Summary = Record<string, number>;

async function handle<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let message = `request failed with status ${res.status}`;
    try {
      const body = await res.json();
      if (body && typeof body.error === "string") {
        message = body.error;
      }
    } catch {
      // ignore JSON parse errors and use the default message
    }
    throw new Error(message);
  }
  return (await res.json()) as T;
}

export async function listExpenses(): Promise<Expense[]> {
  const res = await fetch("/api/expenses");
  return handle<Expense[]>(res);
}

export async function getSummary(): Promise<Summary> {
  const res = await fetch("/api/expenses/summary");
  return handle<Summary>(res);
}

export async function createExpense(expense: NewExpense): Promise<Expense> {
  const res = await fetch("/api/expenses", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(expense),
  });
  return handle<Expense>(res);
}

export async function deleteExpense(id: number): Promise<void> {
  const res = await fetch(`/api/expenses/${id}`, { method: "DELETE" });
  if (!res.ok) {
    throw new Error(`failed to delete expense ${id}`);
  }
}
