# syntax=docker/dockerfile:1

# ---- Build stage ----
# go-sqlite3 (mattn) is a cgo package, so CGO must be enabled and a C
# toolchain present at build time.
FROM golang:1.22-alpine AS build

# gcc + musl-dev provide the C toolchain cgo needs to compile go-sqlite3.
RUN apk add --no-cache gcc musl-dev

WORKDIR /src

# Cache module downloads.
COPY go.mod go.sum ./
RUN go mod download

# Build the API binary with CGO enabled (required for SQLite).
COPY main.go ./
ENV CGO_ENABLED=1
# Statically link against musl so the binary runs on a minimal runtime image.
RUN go build -ldflags '-s -w -linkmode external -extldflags "-static"' -o /taskapi .

# ---- Runtime stage ----
FROM alpine:3.20

# SQLite writes to a data directory; keep the DB on a dedicated path so it can
# be backed by a named volume.
RUN adduser -D -H app && mkdir -p /data && chown app /data
WORKDIR /data

COPY --from=build /taskapi /usr/local/bin/taskapi

USER app
EXPOSE 8080

# The API creates/uses tasks.db in the working directory (/data).
ENTRYPOINT ["taskapi"]
