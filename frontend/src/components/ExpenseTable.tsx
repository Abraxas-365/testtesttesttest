import type { Expense } from "../api";

interface Props {
  expenses: Expense[];
  onDelete: (id: number) => void;
}

function formatAmount(amount: number): string {
  return `$${amount.toFixed(2)}`;
}

export default function ExpenseTable({ expenses, onDelete }: Props) {
  if (expenses.length === 0) {
    return (
      <p className="empty-state" data-testid="empty-state">
        No expenses yet. Add one using the form.
      </p>
    );
  }

  return (
    <table className="expense-table" data-testid="expense-table">
      <thead>
        <tr>
          <th>Date</th>
          <th>Category</th>
          <th>Amount</th>
          <th>Description</th>
          <th aria-label="Actions"></th>
        </tr>
      </thead>
      <tbody>
        {expenses.map((e) => (
          <tr key={e.id} data-testid="expense-row">
            <td>{e.date}</td>
            <td>{e.category}</td>
            <td className="amount">{formatAmount(e.amount)}</td>
            <td>{e.description}</td>
            <td>
              <button
                type="button"
                className="delete-btn"
                aria-label={`Delete expense ${e.id}`}
                onClick={() => onDelete(e.id)}
              >
                Delete
              </button>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
