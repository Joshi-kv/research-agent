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

# Render (and other restricted platforms) drops ALL Linux capabilities at
# container start. The official Caddy image ships the binary with a file
# capability (`setcap cap_net_bind_service=+ep`), which then can't be granted
# at exec time -> `exec /usr/bin/caddy: operation not permitted` -> exit 255.
# Removing the file capability fixes this: since we bind to Render's high
# $PORT (unprivileged), Caddy never needs CAP_NET_BIND_SERVICE.
RUN setcap -r /usr/bin/caddy || true

# Caddy runtime env is injected by the platform (Render/Lambda identical
# interface). Caddyfile uses {$PORT} and {$BACKEND_UPSTREAM} placeholders.
COPY Caddyfile /etc/caddy/Caddyfile
COPY --from=builder /app/dist /usr/share/caddy

# Caddy needs to write its data dir; housekeeping as non-root is built in.
EXPOSE 80

CMD ["caddy", "run", "--config", "/etc/caddy/Caddyfile", "--adapter", "caddyfile"]
