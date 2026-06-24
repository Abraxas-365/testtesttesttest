package main

// Expense represents a single tracked expense.
type Expense struct {
	ID          int64   `json:"id"`
	Amount      float64 `json:"amount"`
	Category    string  `json:"category"`
	Description string  `json:"description"`
	Date        string  `json:"date"` // YYYY-MM-DD
}

// createExpenseRequest is the payload accepted by POST /api/expenses.
// Amount and Category are required; Description and Date are optional.
type createExpenseRequest struct {
	Amount      *float64 `json:"amount"`
	Category    string   `json:"category"`
	Description string   `json:"description"`
	Date        string   `json:"date"`
}
