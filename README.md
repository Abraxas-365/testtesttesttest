# Expense Tracker

A full-stack expense tracking app with Go API, PostgreSQL, and React dashboard.

## Go REST API

A REST API built with the standard library `net/http` and the `lib/pq`
PostgreSQL driver. It manages expenses (amount, category, description, date).

### Configuration

Database settings are read from environment variables with local-dev defaults:

| Variable      | Default     |
| ------------- | ----------- |
| `DB_HOST`     | `localhost` |
| `DB_PORT`     | `5433`      |
| `DB_USER`     | `test`      |
| `DB_PASSWORD` | `test`      |
| `DB_NAME`     | `testdb`    |
| `DB_SSLMODE`  | `disable`   |

The `expenses` table is auto-created on startup (`CREATE TABLE IF NOT EXISTS`).
CORS headers allow all origins. The server listens on port `8080`.

### Endpoints

| Method   | Path                    | Description                                  |
| -------- | ----------------------- | -------------------------------------------- |
| `GET`    | `/api/expenses`         | All expenses as JSON, sorted by date desc    |
| `POST`   | `/api/expenses`         | Create an expense                            |
| `DELETE` | `/api/expenses/:id`     | Delete an expense (returns `204`)            |
| `GET`    | `/api/expenses/summary` | Total amount by category as a JSON object    |
| `GET`    | `/api/health`           | Health check                                 |

`POST /api/expenses` body:

```json
{
  "amount": 12.50,        // float, required
  "category": "food",     // string, required
  "description": "lunch", // string, optional
  "date": "2024-01-10"    // YYYY-MM-DD, optional (defaults to today)
}
```

### Running

```sh
# Start PostgreSQL (example via Docker)
docker run -d --name expense-pg \
  -e POSTGRES_USER=test -e POSTGRES_PASSWORD=test -e POSTGRES_DB=testdb \
  -p 5433:5432 postgres:16-alpine

go run .
```

### Testing

```sh
go test ./... -v
```

The test suite runs against a real PostgreSQL instance. Set `DB_HOST`/`DB_PORT`
to point at your database; tests that cannot reach the database are skipped.
