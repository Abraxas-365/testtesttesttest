package main

import (
	"database/sql"
	"fmt"
	"os"

	_ "github.com/lib/pq"
)

// getenv returns the value of the environment variable named by key, or def if
// the variable is empty or unset.
func getenv(key, def string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return def
}

// connString builds a PostgreSQL connection string from environment variables,
// falling back to sensible local-dev defaults.
func connString() string {
	return fmt.Sprintf(
		"host=%s port=%s user=%s password=%s dbname=%s sslmode=%s",
		getenv("DB_HOST", "localhost"),
		getenv("DB_PORT", "5433"),
		getenv("DB_USER", "test"),
		getenv("DB_PASSWORD", "test"),
		getenv("DB_NAME", "testdb"),
		getenv("DB_SSLMODE", "disable"),
	)
}

// openDB opens a connection pool to PostgreSQL and verifies connectivity.
func openDB() (*sql.DB, error) {
	db, err := sql.Open("postgres", connString())
	if err != nil {
		return nil, fmt.Errorf("open db: %w", err)
	}
	if err := db.Ping(); err != nil {
		return nil, fmt.Errorf("ping db: %w", err)
	}
	return db, nil
}

// migrate creates the expenses table if it does not already exist.
func migrate(db *sql.DB) error {
	const schema = `
CREATE TABLE IF NOT EXISTS expenses (
	id          SERIAL PRIMARY KEY,
	amount      DOUBLE PRECISION NOT NULL,
	category    TEXT NOT NULL,
	description TEXT NOT NULL DEFAULT '',
	date        DATE NOT NULL DEFAULT CURRENT_DATE
);`
	if _, err := db.Exec(schema); err != nil {
		return fmt.Errorf("migrate: %w", err)
	}
	return nil
}
