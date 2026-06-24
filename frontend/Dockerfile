# syntax=docker/dockerfile:1

# ---- Build stage ----
FROM node:20-alpine AS build

WORKDIR /app

# Install dependencies (use npm install since no lockfile is committed).
COPY package.json ./
RUN npm install

# Build the production SPA bundle into /app/dist.
COPY . .
RUN npm run build

# ---- Runtime stage ----
FROM nginx:1.27-alpine

# nginx serves the static SPA and proxies /api to the Go backend.
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
