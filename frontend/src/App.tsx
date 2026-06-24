import { useCallback, useEffect, useState } from "react";
import {
  createExpense,
  deleteExpense,
  getSummary,
  listExpenses,
  type Expense,
  type NewExpense,
  type Summary,
} from "./api";
import ExpenseForm from "./components/ExpenseForm";
import ExpenseTable from "./components/ExpenseTable";
import CategoryPieChart from "./components/CategoryPieChart";

export default function App() {
  const [expenses, setExpenses] = useState<Expense[]>([]);
  const [summary, setSummary] = useState<Summary>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // refresh re-fetches both the expense list and the category summary so the
  // table and pie chart stay in sync after any mutation.
  const refresh = useCallback(async () => {
    setError(null);
    try {
      const [list, sum] = await Promise.all([listExpenses(), getSummary()]);
      setExpenses(list);
      setSummary(sum);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load data");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const handleAdd = useCallback(
    async (expense: NewExpense) => {
      await createExpense(expense);
      await refresh();
    },
    [refresh]
  );

  const handleDelete = useCallback(
    async (id: number) => {
      try {
        await deleteExpense(id);
        await refresh();
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to delete");
      }
    },
    [refresh]
  );

  const total = expenses.reduce((sum, e) => sum + e.amount, 0);

  return (
    <div className="app">
      <header className="app-header">
        <h1>Expense Dashboard</h1>
        <p className="total" data-testid="total">
          Total: ${total.toFixed(2)}
        </p>
      </header>

      {error && (
        <p className="app-error" role="alert">
          {error}
        </p>
      )}

      <div className="layout">
        <aside className="sidebar">
          <ExpenseForm onAdd={handleAdd} />
          <CategoryPieChart summary={summary} />
        </aside>
        <main className="content">
          <h2>Expenses</h2>
          {loading ? (
            <p>Loading…</p>
          ) : (
            <ExpenseTable expenses={expenses} onDelete={handleDelete} />
          )}
        </main>
      </div>
    </div>
  );
}
