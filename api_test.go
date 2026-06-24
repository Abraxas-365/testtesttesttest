package main

import (
	"bytes"
	"database/sql"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"os"
	"strconv"
	"testing"
	"time"
)

// testServer spins up a server backed by a real PostgreSQL database. It uses
// the connection from environment variables (defaults to the local-dev
// instance on port 5433). Each call gets a clean expenses table.
func testServer(t *testing.T) (*server, *sql.DB) {
	t.Helper()
	db, err := openDB()
	if err != nil {
		t.Skipf("skipping DB-backed test: cannot connect to PostgreSQL: %v", err)
	}
	if err := migrate(db); err != nil {
		t.Fatalf("migrate: %v", err)
	}
	if _, err := db.Exec("TRUNCATE expenses RESTART IDENTITY"); err != nil {
		t.Fatalf("truncate: %v", err)
	}
	return newServer(newStore(db)), db
}

// do executes an HTTP request against the server's router and returns the
// recorded response.
func do(t *testing.T, srv *server, method, path string, body interface{}) *httptest.ResponseRecorder {
	t.Helper()
	var buf bytes.Buffer
	if body != nil {
		if err := json.NewEncoder(&buf).Encode(body); err != nil {
			t.Fatalf("encode body: %v", err)
		}
	}
	req := httptest.NewRequest(method, path, &buf)
	rec := httptest.NewRecorder()
	srv.routes().ServeHTTP(rec, req)
	return rec
}

func TestCreateAndListExpenses(t *testing.T) {
	srv, db := testServer(t)
	defer db.Close()

	// Create two expenses on different dates.
	r1 := do(t, srv, http.MethodPost, "/api/expenses", map[string]interface{}{
		"amount": 12.50, "category": "food", "description": "lunch", "date": "2024-01-10",
	})
	if r1.Code != http.StatusCreated {
		t.Fatalf("create: got %d, body=%s", r1.Code, r1.Body.String())
	}
	var created Expense
	if err := json.Unmarshal(r1.Body.Bytes(), &created); err != nil {
		t.Fatalf("decode created: %v", err)
	}
	if created.ID == 0 || created.Amount != 12.50 || created.Category != "food" {
		t.Fatalf("unexpected created expense: %+v", created)
	}

	r2 := do(t, srv, http.MethodPost, "/api/expenses", map[string]interface{}{
		"amount": 40.0, "category": "transport", "date": "2024-02-20",
	})
	if r2.Code != http.StatusCreated {
		t.Fatalf("create 2: got %d, body=%s", r2.Code, r2.Body.String())
	}

	// List should return both, newest date first.
	rl := do(t, srv, http.MethodGet, "/api/expenses", nil)
	if rl.Code != http.StatusOK {
		t.Fatalf("list: got %d", rl.Code)
	}
	if ct := rl.Header().Get("Content-Type"); ct != "application/json" {
		t.Fatalf("list content-type: got %q", ct)
	}
	var list []Expense
	if err := json.Unmarshal(rl.Body.Bytes(), &list); err != nil {
		t.Fatalf("decode list: %v", err)
	}
	if len(list) != 2 {
		t.Fatalf("expected 2 expenses, got %d", len(list))
	}
	if list[0].Date != "2024-02-20" || list[1].Date != "2024-01-10" {
		t.Fatalf("expected date descending, got %s then %s", list[0].Date, list[1].Date)
	}
}

func TestCreateDefaultsDateToToday(t *testing.T) {
	srv, db := testServer(t)
	defer db.Close()

	rec := do(t, srv, http.MethodPost, "/api/expenses", map[string]interface{}{
		"amount": 5.0, "category": "misc",
	})
	if rec.Code != http.StatusCreated {
		t.Fatalf("create: got %d, body=%s", rec.Code, rec.Body.String())
	}
	var e Expense
	if err := json.Unmarshal(rec.Body.Bytes(), &e); err != nil {
		t.Fatalf("decode: %v", err)
	}
	today := time.Now().Format("2006-01-02")
	if e.Date != today {
		t.Fatalf("expected date %s, got %s", today, e.Date)
	}
	if e.Description != "" {
		t.Fatalf("expected empty description, got %q", e.Description)
	}
}

func TestCreateValidation(t *testing.T) {
	srv, db := testServer(t)
	defer db.Close()

	cases := []struct {
		name string
		body map[string]interface{}
	}{
		{"missing amount", map[string]interface{}{"category": "food"}},
		{"missing category", map[string]interface{}{"amount": 10.0}},
		{"blank category", map[string]interface{}{"amount": 10.0, "category": "  "}},
		{"bad date format", map[string]interface{}{"amount": 10.0, "category": "food", "date": "10-01-2024"}},
		{"invalid calendar date", map[string]interface{}{"amount": 10.0, "category": "food", "date": "2024-13-40"}},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			rec := do(t, srv, http.MethodPost, "/api/expenses", tc.body)
			if rec.Code != http.StatusBadRequest {
				t.Fatalf("expected 400, got %d, body=%s", rec.Code, rec.Body.String())
			}
		})
	}
}

func TestDeleteExpense(t *testing.T) {
	srv, db := testServer(t)
	defer db.Close()

	rec := do(t, srv, http.MethodPost, "/api/expenses", map[string]interface{}{
		"amount": 9.99, "category": "food",
	})
	var e Expense
	_ = json.Unmarshal(rec.Body.Bytes(), &e)

	// Delete existing -> 204.
	del := do(t, srv, http.MethodDelete, "/api/expenses/"+itoa(e.ID), nil)
	if del.Code != http.StatusNoContent {
		t.Fatalf("delete: expected 204, got %d", del.Code)
	}
	if del.Body.Len() != 0 {
		t.Fatalf("delete: expected empty body, got %q", del.Body.String())
	}

	// Delete again -> 404.
	del2 := do(t, srv, http.MethodDelete, "/api/expenses/"+itoa(e.ID), nil)
	if del2.Code != http.StatusNotFound {
		t.Fatalf("delete missing: expected 404, got %d", del2.Code)
	}

	// Bad id -> 400.
	del3 := do(t, srv, http.MethodDelete, "/api/expenses/abc", nil)
	if del3.Code != http.StatusBadRequest {
		t.Fatalf("delete bad id: expected 400, got %d", del3.Code)
	}
}

func TestSummary(t *testing.T) {
	srv, db := testServer(t)
	defer db.Close()

	seed := []map[string]interface{}{
		{"amount": 10.0, "category": "food"},
		{"amount": 5.5, "category": "food"},
		{"amount": 30.0, "category": "transport"},
	}
	for _, s := range seed {
		if rec := do(t, srv, http.MethodPost, "/api/expenses", s); rec.Code != http.StatusCreated {
			t.Fatalf("seed create failed: %d", rec.Code)
		}
	}

	rec := do(t, srv, http.MethodGet, "/api/expenses/summary", nil)
	if rec.Code != http.StatusOK {
		t.Fatalf("summary: got %d", rec.Code)
	}
	var summary map[string]float64
	if err := json.Unmarshal(rec.Body.Bytes(), &summary); err != nil {
		t.Fatalf("decode summary: %v", err)
	}
	if got := summary["food"]; got != 15.5 {
		t.Fatalf("food total: expected 15.5, got %v", got)
	}
	if got := summary["transport"]; got != 30.0 {
		t.Fatalf("transport total: expected 30.0, got %v", got)
	}
}

func TestListEmptyReturnsArray(t *testing.T) {
	srv, db := testServer(t)
	defer db.Close()

	rec := do(t, srv, http.MethodGet, "/api/expenses", nil)
	if rec.Code != http.StatusOK {
		t.Fatalf("list: got %d", rec.Code)
	}
	if got := bytes.TrimSpace(rec.Body.Bytes()); string(got) != "[]" {
		t.Fatalf("expected [] for empty list, got %q", got)
	}
}

func TestCORSHeaders(t *testing.T) {
	srv, db := testServer(t)
	defer db.Close()

	rec := do(t, srv, http.MethodGet, "/api/expenses", nil)
	if origin := rec.Header().Get("Access-Control-Allow-Origin"); origin != "*" {
		t.Fatalf("CORS origin: expected *, got %q", origin)
	}

	// Preflight OPTIONS returns 204 with CORS headers.
	req := httptest.NewRequest(http.MethodOptions, "/api/expenses", nil)
	pre := httptest.NewRecorder()
	srv.routes().ServeHTTP(pre, req)
	if pre.Code != http.StatusNoContent {
		t.Fatalf("preflight: expected 204, got %d", pre.Code)
	}
	if origin := pre.Header().Get("Access-Control-Allow-Origin"); origin != "*" {
		t.Fatalf("preflight CORS origin: expected *, got %q", origin)
	}
}

// itoa converts an int64 id to its decimal string form.
func itoa(n int64) string {
	return strconv.FormatInt(n, 10)
}

func TestMain(m *testing.M) {
	// Allow overriding the DB port for CI via env; defaults handled in db.go.
	os.Exit(m.Run())
}
