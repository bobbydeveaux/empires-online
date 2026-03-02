# Nginx WebSocket Proxy Configuration

## Overview

The Nginx reverse proxy (`frontend/nginx.conf`) serves the React SPA and proxies both REST API and WebSocket requests to the FastAPI backend. WebSocket connections require special handling because they use the HTTP Upgrade mechanism to switch from HTTP to the WebSocket protocol.

## Configuration

### Location Blocks

| Path | Purpose | Backend Target |
|------|---------|----------------|
| `/api/` | REST API requests | `http://backend:8000/api/` |
| `/ws/` | WebSocket connections | `http://backend:8000/ws/` |
| `/` | React SPA (client-side routing) | Static files |
| `/static/` | Static assets with cache headers | Static files |

### WebSocket-Specific Directives

The `/ws/` location block includes directives required for WebSocket proxying:

- **`proxy_http_version 1.1`** - WebSocket requires HTTP/1.1 (HTTP/1.0 does not support the Upgrade mechanism).
- **`proxy_set_header Upgrade $http_upgrade`** - Forwards the client's `Upgrade: websocket` header to the backend.
- **`proxy_set_header Connection $connection_upgrade`** - Sets `Connection: upgrade` when the Upgrade header is present, derived from the `map` directive.
- **`proxy_read_timeout 86400s`** - 24-hour timeout prevents Nginx from closing idle WebSocket connections. Default (60s) would kill game sessions prematurely.
- **`proxy_send_timeout 86400s`** - Matching send timeout for backend-to-client messages.

### The `map` Directive

```nginx
map $http_upgrade $connection_upgrade {
    default upgrade;
    ''      close;
}
```

This maps the incoming `Upgrade` header value to the appropriate `Connection` header value:
- When `Upgrade` header is present (WebSocket request) -> `Connection: upgrade`
- When `Upgrade` header is absent (regular HTTP) -> `Connection: close`

## How It Works

1. Client sends an HTTP request to `ws://host:3000/ws/{game_id}?token=JWT` with `Upgrade: websocket` header
2. Nginx matches the `/ws/` location block
3. The `map` directive sets `Connection: upgrade` based on the `Upgrade` header
4. Nginx forwards the request to `http://backend:8000/ws/{game_id}` with the Upgrade and Connection headers
5. The FastAPI backend accepts the WebSocket upgrade
6. Nginx maintains the bidirectional connection with 24-hour timeouts

## CI Validation

The `validate-nginx` job in `.github/workflows/ci.yml` runs `nginx -t` via Docker on every push and PR to catch syntax errors early:

```yaml
validate-nginx:
  runs-on: ubuntu-latest
  steps:
  - uses: actions/checkout@v3
  - name: Validate Nginx configuration syntax
    run: |
      docker run --rm \
        -v ${{ github.workspace }}/frontend/nginx.conf:/etc/nginx/conf.d/default.conf:ro \
        nginx:alpine nginx -t
```

## Troubleshooting

**WebSocket connections fail with HTTP 400:**
Verify the `map` directive is at the `http` context level (outside the `server` block) and the `Upgrade`/`Connection` headers are set in the `/ws/` location.

**Connections drop after 60 seconds:**
Check that `proxy_read_timeout` and `proxy_send_timeout` are set to a value longer than the expected connection duration (default is 60s).

**WebSocket works directly but not through Nginx:**
Ensure `proxy_http_version 1.1` is set. HTTP/1.0 does not support the Upgrade mechanism.
