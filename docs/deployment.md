# 🚀 MagNetFlix — Deployment & Runtime Topology

This guide details the container deployment architecture, storage boundaries, and reverse proxy / SSO integration for **MagNetFlix**.

---

## 🐳 Docker Compose Architecture

MagNetFlix runs as an isolated multi-container stack connected to an internal service bridge, with public ingress routed through a reverse proxy (e.g. Traefik, Nginx, or Caddy) supporting forward-auth or OIDC proxy headers.

```yaml
services:
  # 1. FastAPI Web Gateway & BFF Dashboard
  bff:
    build:
      context: .
      dockerfile: services/bff/Dockerfile
    restart: unless-stopped
    environment:
      - GRPC_WORKER_HOST=worker:50051
      - APP_ENV=production
      - AUTH_ENABLED=${AUTH_ENABLED:-true}
      - AUTH_HEADER_USER=${AUTH_HEADER_USER:-Remote-User}
      - CORS_ALLOWED_ORIGINS=${CORS_ALLOWED_ORIGINS:-}
      - TMDB_API_KEY=${TMDB_API_KEY}
    networks:
      - proxy_network
      - magnetflix_internal
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.magnetflix.rule=Host(`${MAGNETFLIX_HOST}`)"
      - "traefik.http.routers.magnetflix.entrypoints=websecure"
      - "traefik.http.routers.magnetflix.tls.certresolver=${TRAEFIK_CERTRESOLVER:-letsencrypt}"
      - "traefik.http.routers.magnetflix.middlewares=${TRAEFIK_AUTH_MIDDLEWARE}"
      - "traefik.http.services.magnetflix.loadbalancer.server.port=8000"

  # 2. gRPC Pipeline Worker & Mover
  worker:
    build:
      context: .
      dockerfile: services/worker/Dockerfile
    restart: unless-stopped
    user: "${PUID:-1000}:${PGID:-1000}"
    depends_on:
      transmission:
        condition: service_healthy
    environment:
      - TRANSMISSION_HOST=transmission
      - TRANSMISSION_PORT=9091
      - DATABASE_URL=sqlite+aiosqlite:////data/magnetflix.sqlite3
      - STAGING_DIR=/data/staging
      - MEDIA_DIR=/media/movies
      - TMDB_API_KEY=${TMDB_API_KEY}
    volumes:
      - ${MAGNETFLIX_DATA_DIR:-./data}:/data
      - ${MAGNETFLIX_MEDIA_DIR:-./media/movies}:/media/movies
    networks:
      - magnetflix_internal

  # 3. Isolated Transmission Torrent Daemon
  transmission:
    image: lscr.io/linuxserver/transmission:latest
    restart: unless-stopped
    environment:
      - PUID=${PUID:-1000}
      - PGID=${PGID:-1000}
      - TZ=${TZ:-UTC}
    healthcheck:
      test: ["CMD-SHELL", "curl -sf http://localhost:9091/transmission/rpc >/dev/null || [ $$? -eq 22 ]"]
      interval: 10s
      timeout: 5s
      retries: 5
    volumes:
      - ${TRANSMISSION_CONFIG_DIR:-./config/transmission}:/config
      - ${MAGNETFLIX_DATA_DIR:-./data}/staging:/data/staging
    networks:
      - magnetflix_internal

networks:
  proxy_network:
    external: true
  magnetflix_internal:
    driver: bridge
```

> **Reverse Proxy Portability:** The Traefik labels above use environment variables (`MAGNETFLIX_HOST`, `TRAEFIK_AUTH_MIDDLEWARE`) so any deployment (homelab or VPS) can configure its own domain and SSO middleware without patching compose files. Users running Nginx or Caddy forward-auth can omit the `traefik.*` labels and expose `bff:8000` on `proxy_network`.

---

## 🔐 Pluggable SSO / Reverse Proxy Identity Adapter (`DEC-8`)

MagNetFlix does not couple its internal application logic to any specific identity provider or domain. Instead, the FastAPI BFF operates a fail-closed **Identity Adapter** extracting authenticated identity from upstream gateway headers:

| Environment Variable | Default | Purpose |
| :--- | :--- | :--- |
| `AUTH_ENABLED` | `true` | When `true`, requests missing a non-empty `AUTH_HEADER_USER` fail closed with `401 Unauthorized`. Set to `false` only for offline/local development (`local_user`). |
| `AUTH_HEADER_USER` | `Remote-User` | Name of the incoming HTTP header containing the verified username (e.g., `Remote-User` for Authelia/Caddy, `X-authentik-username` for Authentik, or `X-Forwarded-User` for OAuth2-Proxy). |
| `CORS_ALLOWED_ORIGINS` | `""` | Optional comma-separated origins permitted for browser extension requests across custom domains. |

### Upstream Authentication Workflow
1. Client (Web UI or browser extension) sends a request to the configured `${MAGNETFLIX_HOST}` endpoint.
2. Reverse proxy executes forward-auth or OIDC session validation against the chosen identity provider (OAuth2-Proxy, Authentik, Authelia, etc.).
3. If valid, the proxy injects the configured identity header (`AUTH_HEADER_USER`) and forwards the request to the BFF on `proxy_network`.
4. BFF enforces `AUTH_ENABLED` (returning `401` if enabled and header is absent) and forwards the verified username across the private gRPC boundary to the Worker for persistent audit logging.

---

## 📂 Storage Volume Invariants

| Container Mount | Host Target | Filesystem Type | Purpose |
| :--- | :--- | :--- | :--- |
| `/data/magnetflix.sqlite3` | Local persistent disk (`./data`) | Local SQLite (WAL Mode) | Job audit logs and pipeline state machine records. **Never place on NFS/SMB network shares.** |
| `/data/staging` | Fast scratch disk (`./data/staging`) | Fast local storage | Transmission scratch directory where torrent pieces land. Shared strictly between `worker` and `transmission`. |
| `/media/movies` | Media storage pool (`/mnt/storage/...`) | Media pool (ZFS/ext4) | Final Jellyfin/Plex target directory and temporary cross-volume staging (`.staging_<job_id>`). |

### Cross-Volume Publication & Atomic Swap (`DEC-5`)
Because `/data/staging` and `/media/movies` reside on distinct filesystems, cross-volume transfers cannot use filesystem hard-links (`EXDEV` error):
1. Files are copied across volumes to `/media/movies/.staging_<job_id>/` using `shutil.copy2`.
2. Once transfer and file sizes are verified, `os.replace` executes an instant atomic directory rename on the **same target filesystem** from `.staging_<job_id>/` to `/media/movies/<Title> (<Year>) [imdbid-<IMDbID>]/`.
3. Jellyfin and Plex library watchers will never detect, lock, or index partially transferred media files.
