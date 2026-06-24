package main

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"
)

// newTestServer spins up an in-memory SQLite-backed server for each test.
func newTestServer(t *testing.T) (http.Handler, func()) {
	t.Helper()
	db, err := initDB(":memory:")
	if err != nil {
		t.Fatalf("initDB: %v", err)
	}
	return newServer(db), func() { db.Close() }
}

func doJSON(t *testing.T, h http.Handler, method, path, body string) *httptest.ResponseRecorder {
	t.Helper()
	var r *http.Request
	if body == "" {
		r = httptest.NewRequest(method, path, nil)
	} else {
		r = httptest.NewRequest(method, path, bytes.NewBufferString(body))
	}
	w := httptest.NewRecorder()
	h.ServeHTTP(w, r)
	return w
}

func TestListEmpty(t *testing.T) {
	h, cleanup := newTestServer(t)
	defer cleanup()

	w := doJSON(t, h, http.MethodGet, "/api/tasks", "")
	if w.Code != http.StatusOK {
		t.Fatalf("status = %d, want 200", w.Code)
	}
	var tasks []Task
	if err := json.Unmarshal(w.Body.Bytes(), &tasks); err != nil {
		t.Fatalf("unmarshal: %v (body=%q)", err, w.Body.String())
	}
	if len(tasks) != 0 {
		t.Fatalf("len(tasks) = %d, want 0", len(tasks))
	}
	// Must be a JSON array, not null.
	if got := w.Body.String(); got == "null\n" || got == "null" {
		t.Fatalf("body = %q, want empty array", got)
	}
}

func TestCreateTask(t *testing.T) {
	h, cleanup := newTestServer(t)
	defer cleanup()

	w := doJSON(t, h, http.MethodPost, "/api/tasks", `{"title":"Buy milk","description":"2%"}`)
	if w.Code != http.StatusCreated {
		t.Fatalf("status = %d, want 201", w.Code)
	}
	var task Task
	if err := json.Unmarshal(w.Body.Bytes(), &task); err != nil {
		t.Fatalf("unmarshal: %v", err)
	}
	if task.ID == 0 {
		t.Fatalf("expected non-zero id")
	}
	if task.Title != "Buy milk" || task.Description != "2%" {
		t.Fatalf("unexpected task: %+v", task)
	}
	if task.Done {
		t.Fatalf("done should default to false")
	}
	if task.CreatedAt.IsZero() {
		t.Fatalf("created_at should be set")
	}
}

func TestCreateTaskMissingTitle(t *testing.T) {
	h, cleanup := newTestServer(t)
	defer cleanup()

	w := doJSON(t, h, http.MethodPost, "/api/tasks", `{"description":"no title"}`)
	if w.Code != http.StatusBadRequest {
		t.Fatalf("status = %d, want 400", w.Code)
	}
}

func TestCreateTaskInvalidJSON(t *testing.T) {
	h, cleanup := newTestServer(t)
	defer cleanup()

	w := doJSON(t, h, http.MethodPost, "/api/tasks", `{bad json`)
	if w.Code != http.StatusBadRequest {
		t.Fatalf("status = %d, want 400", w.Code)
	}
}

func TestUpdateTask(t *testing.T) {
	h, cleanup := newTestServer(t)
	defer cleanup()

	created := doJSON(t, h, http.MethodPost, "/api/tasks", `{"title":"Original"}`)
	var task Task
	json.Unmarshal(created.Body.Bytes(), &task)

	w := doJSON(t, h, http.MethodPut, "/api/tasks/1", `{"title":"Updated","done":true}`)
	if w.Code != http.StatusOK {
		t.Fatalf("status = %d, want 200", w.Code)
	}
	var updated Task
	json.Unmarshal(w.Body.Bytes(), &updated)
	if updated.Title != "Updated" || !updated.Done {
		t.Fatalf("unexpected updated task: %+v", updated)
	}
	if updated.ID != task.ID {
		t.Fatalf("id changed: %d != %d", updated.ID, task.ID)
	}
}

func TestUpdateTaskPartial(t *testing.T) {
	h, cleanup := newTestServer(t)
	defer cleanup()

	doJSON(t, h, http.MethodPost, "/api/tasks", `{"title":"Keep me","description":"keep desc"}`)

	// Only update done; title and description must persist.
	w := doJSON(t, h, http.MethodPut, "/api/tasks/1", `{"done":true}`)
	if w.Code != http.StatusOK {
		t.Fatalf("status = %d, want 200", w.Code)
	}
	var updated Task
	json.Unmarshal(w.Body.Bytes(), &updated)
	if updated.Title != "Keep me" || updated.Description != "keep desc" || !updated.Done {
		t.Fatalf("partial update wrong: %+v", updated)
	}
}

func TestUpdateTaskNotFound(t *testing.T) {
	h, cleanup := newTestServer(t)
	defer cleanup()

	w := doJSON(t, h, http.MethodPut, "/api/tasks/999", `{"title":"x"}`)
	if w.Code != http.StatusNotFound {
		t.Fatalf("status = %d, want 404", w.Code)
	}
}

func TestDeleteTask(t *testing.T) {
	h, cleanup := newTestServer(t)
	defer cleanup()

	doJSON(t, h, http.MethodPost, "/api/tasks", `{"title":"delete me"}`)

	w := doJSON(t, h, http.MethodDelete, "/api/tasks/1", "")
	if w.Code != http.StatusNoContent {
		t.Fatalf("status = %d, want 204", w.Code)
	}

	// Confirm it's gone.
	list := doJSON(t, h, http.MethodGet, "/api/tasks", "")
	var tasks []Task
	json.Unmarshal(list.Body.Bytes(), &tasks)
	if len(tasks) != 0 {
		t.Fatalf("expected 0 tasks after delete, got %d", len(tasks))
	}
}

func TestDeleteTaskNotFound(t *testing.T) {
	h, cleanup := newTestServer(t)
	defer cleanup()

	w := doJSON(t, h, http.MethodDelete, "/api/tasks/999", "")
	if w.Code != http.StatusNotFound {
		t.Fatalf("status = %d, want 404", w.Code)
	}
}

func TestInvalidID(t *testing.T) {
	h, cleanup := newTestServer(t)
	defer cleanup()

	w := doJSON(t, h, http.MethodPut, "/api/tasks/abc", `{"title":"x"}`)
	if w.Code != http.StatusBadRequest {
		t.Fatalf("status = %d, want 400", w.Code)
	}
}

func TestCORSHeaders(t *testing.T) {
	h, cleanup := newTestServer(t)
	defer cleanup()

	w := doJSON(t, h, http.MethodGet, "/api/tasks", "")
	if got := w.Header().Get("Access-Control-Allow-Origin"); got != "*" {
		t.Fatalf("CORS origin = %q, want *", got)
	}
}

func TestCORSPreflight(t *testing.T) {
	h, cleanup := newTestServer(t)
	defer cleanup()

	w := doJSON(t, h, http.MethodOptions, "/api/tasks", "")
	if w.Code != http.StatusNoContent {
		t.Fatalf("preflight status = %d, want 204", w.Code)
	}
	if got := w.Header().Get("Access-Control-Allow-Methods"); got == "" {
		t.Fatalf("expected Allow-Methods header")
	}
}

func TestFullLifecycle(t *testing.T) {
	h, cleanup := newTestServer(t)
	defer cleanup()

	// Create two tasks.
	doJSON(t, h, http.MethodPost, "/api/tasks", `{"title":"first"}`)
	doJSON(t, h, http.MethodPost, "/api/tasks", `{"title":"second","done":true}`)

	w := doJSON(t, h, http.MethodGet, "/api/tasks", "")
	var tasks []Task
	json.Unmarshal(w.Body.Bytes(), &tasks)
	if len(tasks) != 2 {
		t.Fatalf("expected 2 tasks, got %d", len(tasks))
	}
	if tasks[0].Title != "first" || tasks[1].Title != "second" {
		t.Fatalf("unexpected ordering: %+v", tasks)
	}
}
