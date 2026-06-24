# syntax=docker/dockerfile:1

# ---- Build stage ----
# CGO is required by github.com/mattn/go-sqlite3, so we need gcc + musl-dev.
FROM golang:1.22-alpine AS build

RUN apk add --no-cache gcc musl-dev

WORKDIR /src

# Cache module downloads.
COPY go.mod go.sum ./
RUN go mod download

# Build the statically linked binary.
COPY main.go ./
ENV CGO_ENABLED=1 GOOS=linux
RUN go build -ldflags '-s -w -extldflags "-static"' -o /out/taskapi .

# ---- Runtime stage ----
FROM alpine:3.20

# wget (busybox) is used by the compose healthcheck.
RUN addgroup -S app && adduser -S app -G app

# /data holds the SQLite database and is backed by a named volume.
RUN mkdir -p /data && chown app:app /data
VOLUME ["/data"]

COPY --from=build /out/taskapi /usr/local/bin/taskapi

USER app
WORKDIR /data

EXPOSE 8080

ENTRYPOINT ["/usr/local/bin/taskapi"]
