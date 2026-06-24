package main

import (
	"database/sql"
	"time"
)

// store wraps database operations on expenses.
type store struct {
	db *sql.DB
}

func newStore(db *sql.DB) *store {
	return &store{db: db}
}

// list returns all expenses sorted by date descending (then id descending for
// stable ordering of same-date rows).
func (s *store) list() ([]Expense, error) {
	rows, err := s.db.Query(
		`SELECT id, amount, category, description, to_char(date, 'YYYY-MM-DD')
		 FROM expenses
		 ORDER BY date DESC, id DESC`)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	// Initialise to non-nil so JSON encodes an empty array, not null.
	expenses := []Expense{}
	for rows.Next() {
		var e Expense
		if err := rows.Scan(&e.ID, &e.Amount, &e.Category, &e.Description, &e.Date); err != nil {
			return nil, err
		}
		expenses = append(expenses, e)
	}
	return expenses, rows.Err()
}

// create inserts a new expense. date must be a YYYY-MM-DD string; if empty,
// today's date is used.
func (s *store) create(amount float64, category, description, date string) (Expense, error) {
	if date == "" {
		date = time.Now().Format("2006-01-02")
	}
	var e Expense
	err := s.db.QueryRow(
		`INSERT INTO expenses (amount, category, description, date)
		 VALUES ($1, $2, $3, $4)
		 RETURNING id, amount, category, description, to_char(date, 'YYYY-MM-DD')`,
		amount, category, description, date,
	).Scan(&e.ID, &e.Amount, &e.Category, &e.Description, &e.Date)
	return e, err
}

// delete removes the expense with the given id. It reports whether a row was
// actually deleted.
func (s *store) delete(id int64) (bool, error) {
	res, err := s.db.Exec(`DELETE FROM expenses WHERE id = $1`, id)
	if err != nil {
		return false, err
	}
	n, err := res.RowsAffected()
	if err != nil {
		return false, err
	}
	return n > 0, nil
}

// summary returns total amount grouped by category.
func (s *store) summary() (map[string]float64, error) {
	rows, err := s.db.Query(
		`SELECT category, SUM(amount) FROM expenses GROUP BY category`)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	result := map[string]float64{}
	for rows.Next() {
		var category string
		var total float64
		if err := rows.Scan(&category, &total); err != nil {
			return nil, err
		}
		result[category] = total
	}
	return result, rows.Err()
}
