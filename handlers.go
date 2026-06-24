package main

import (
	"encoding/json"
	"net/http"
	"regexp"
	"strconv"
	"strings"
	"time"
)

// server holds dependencies for the HTTP handlers.
type server struct {
	store *store
}

func newServer(st *store) *server {
	return &server{store: st}
}

var dateRe = regexp.MustCompile(`^\d{4}-\d{2}-\d{2}$`)

// writeJSON serialises v as JSON with the given status code.
func writeJSON(w http.ResponseWriter, status int, v interface{}) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(v)
}

// writeError writes a JSON error body.
func writeError(w http.ResponseWriter, status int, msg string) {
	writeJSON(w, status, map[string]string{"error": msg})
}

// cors wraps a handler, adding permissive CORS headers and handling
// preflight OPTIONS requests.
func cors(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Access-Control-Allow-Origin", "*")
		w.Header().Set("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
		w.Header().Set("Access-Control-Allow-Headers", "Content-Type, Authorization")
		if r.Method == http.MethodOptions {
			w.WriteHeader(http.StatusNoContent)
			return
		}
		next.ServeHTTP(w, r)
	})
}

// routes builds the application's HTTP handler with all routes wired up.
func (s *server) routes() http.Handler {
	mux := http.NewServeMux()
	mux.HandleFunc("/api/expenses/summary", s.handleSummary)
	mux.HandleFunc("/api/expenses", s.handleExpenses)
	mux.HandleFunc("/api/expenses/", s.handleExpenseByID)
	mux.HandleFunc("/api/health", s.handleHealth)
	return cors(mux)
}

func (s *server) handleHealth(w http.ResponseWriter, r *http.Request) {
	writeJSON(w, http.StatusOK, map[string]string{"status": "ok"})
}

// handleExpenses dispatches GET (list) and POST (create) on /api/expenses.
func (s *server) handleExpenses(w http.ResponseWriter, r *http.Request) {
	switch r.Method {
	case http.MethodGet:
		s.listExpenses(w, r)
	case http.MethodPost:
		s.createExpense(w, r)
	default:
		writeError(w, http.StatusMethodNotAllowed, "method not allowed")
	}
}

func (s *server) listExpenses(w http.ResponseWriter, r *http.Request) {
	expenses, err := s.store.list()
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	writeJSON(w, http.StatusOK, expenses)
}

func (s *server) createExpense(w http.ResponseWriter, r *http.Request) {
	var req createExpenseRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeError(w, http.StatusBadRequest, "invalid JSON body")
		return
	}

	if req.Amount == nil {
		writeError(w, http.StatusBadRequest, "amount is required")
		return
	}
	if strings.TrimSpace(req.Category) == "" {
		writeError(w, http.StatusBadRequest, "category is required")
		return
	}
	if req.Date != "" {
		if !dateRe.MatchString(req.Date) {
			writeError(w, http.StatusBadRequest, "date must be in YYYY-MM-DD format")
			return
		}
		if _, err := time.Parse("2006-01-02", req.Date); err != nil {
			writeError(w, http.StatusBadRequest, "date is not a valid calendar date")
			return
		}
	}

	expense, err := s.store.create(*req.Amount, req.Category, req.Description, req.Date)
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	writeJSON(w, http.StatusCreated, expense)
}

// handleExpenseByID handles DELETE /api/expenses/:id.
func (s *server) handleExpenseByID(w http.ResponseWriter, r *http.Request) {
	idStr := strings.TrimPrefix(r.URL.Path, "/api/expenses/")
	if idStr == "" || strings.Contains(idStr, "/") {
		writeError(w, http.StatusNotFound, "not found")
		return
	}

	if r.Method != http.MethodDelete {
		writeError(w, http.StatusMethodNotAllowed, "method not allowed")
		return
	}

	id, err := strconv.ParseInt(idStr, 10, 64)
	if err != nil {
		writeError(w, http.StatusBadRequest, "invalid id")
		return
	}

	deleted, err := s.store.delete(id)
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	if !deleted {
		writeError(w, http.StatusNotFound, "expense not found")
		return
	}
	w.WriteHeader(http.StatusNoContent)
}

// handleSummary handles GET /api/expenses/summary.
func (s *server) handleSummary(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		writeError(w, http.StatusMethodNotAllowed, "method not allowed")
		return
	}
	summary, err := s.store.summary()
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	writeJSON(w, http.StatusOK, summary)
}
