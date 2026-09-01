# syntax=docker/dockerfile:1

# ---- Build stage ----
FROM node:20-alpine AS builder

WORKDIR /app

COPY package*.json ./
# Use a lockfile-derived install for reproducible builds
RUN npm ci

COPY . .

ARG VITE_API_URL
ENV VITE_API_URL=$VITE_API_URL

RUN npm run build

# ---- Runtime stage (Caddy) ----
FROM caddy:2-alpine

# Caddy runtime env is injected by the platform (Render/Lambda identical
# interface). Caddyfile uses {$PORT} and {$BACKEND_UPSTREAM} placeholders.
COPY Caddyfile /etc/caddy/Caddyfile
COPY --from=builder /app/dist /usr/share/caddy

# Caddy needs to write its data dir; housekeeping as non-root is built in.
EXPOSE 80

CMD ["caddy", "run", "--config", "/etc/caddy/Caddyfile", "--adapter", "caddyfile"]
