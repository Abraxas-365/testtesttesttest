# Task Manager

A full-stack task management app with a Go API backend and React frontend.

- **Backend** — Go (`net/http`) REST API with SQLite storage (`main.go`).
- **Frontend** — React + Vite SPA (`frontend/`), served in production by nginx.
- **Orchestration** — `docker-compose.yml` runs both services; nginx proxies
  `/api` requests to the Go API.

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) (with the `docker compose` plugin)
- For the integration test script (`test.sh`): `bash`, `curl`, and
  [`jq`](https://jqlang.github.io/jq/) installed on the host.

To develop the backend or run the unit tests directly you also need Go 1.22+
with `CGO_ENABLED=1` and a C compiler (gcc), since the SQLite driver uses cgo.

## Running with Docker Compose

Build and start the full stack:

```sh
docker compose up --build
```

Then open the app at <http://localhost:8081>. The nginx `web` service serves the
React SPA and forwards any `/api/...` request to the Go `api` service.

Services:

| Service | Description                          | Host port |
| ------- | ------------------------------------ | --------- |
| `web`   | nginx serving the SPA + `/api` proxy | `8081`    |
| `api`   | Go REST API (internal only)          | —         |

SQLite data is stored in the `api-data` named volume (mounted at `/data` in the
`api` container), so tasks persist across restarts. To stop and remove the
stack including its data:

```sh
docker compose down -v
```

## Integration tests

`test.sh` builds and starts the stack, waits for both services to become
healthy, and exercises the end-to-end request flow through the nginx proxy
(create, list, update, and delete a task). Containers and volumes are cleaned
up automatically on exit.

```sh
./test.sh
```

## API endpoints

| Method   | Path              | Description            |
| -------- | ----------------- | ---------------------- |
| `GET`    | `/api/tasks`      | List all tasks         |
| `POST`   | `/api/tasks`      | Create a task          |
| `PUT`    | `/api/tasks/{id}` | Update a task (partial)|
| `DELETE` | `/api/tasks/{id}` | Delete a task          |

## Backend unit tests

```sh
go test ./...
```
