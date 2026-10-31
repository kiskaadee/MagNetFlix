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
      - AUTH_ENABLED=true
      - AUTH_HEADER_USER=Remote-User
      - AUTH_HEADER_EMAIL=Remote-Email
      - TMDB_API_KEY=${TMDB_API_KEY}
    networks:
      - traefik_network
      - magnetflix_internal
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.magnetflix.rule=Host(`addmovie.roadtotech.me`)"
      - "traefik.http.routers.magnetflix.entrypoints=websecure"
      - "traefik.http.routers.magnetflix.tls.certresolver=letsencrypt"
      - "traefik.http.routers.magnetflix.middlewares=authelia@docker"
      - "traefik.http.services.magnetflix.loadbalancer.server.port=8000"

  # 2. gRPC Pipeline Worker & Mover
  worker:
    build:
      context: .
      dockerfile: services/worker/Dockerfile
    restart: unless-stopped
    environment:
      - TRANSMISSION_HOST=transmission
      - TRANSMISSION_PORT=9091
      - DATABASE_URL=sqlite+aiosqlite:////data/magnetflix.sqlite3
      - STAGING_DIR=/data/staging
      - MEDIA_DIR=/media/movies
      - TMDB_API_KEY=${TMDB_API_KEY}
    volumes:
      - ./data:/data
      - /mnt/storage/media/movies:/media/movies
    networks:
      - magnetflix_internal

  # 3. Isolated Transmission Torrent Daemon
  transmission:
    image: lscr.io/linuxserver/transmission:latest
    restart: unless-stopped
    environment:
      - PUID=1000
      - PGID=1000
      - TZ=America/Chicago
    volumes:
      - ./config/transmission:/config
      - ./data/staging:/data/staging
    networks:
      - magnetflix_internal

networks:
  traefik_network:
    external: true
  magnetflix_internal:
    driver: bridge
```

---

## 🔐 Pluggable SSO / Reverse Proxy Identity Adapter (`DEC-8`)

MagNetFlix does not couple its internal application logic to any specific identity provider. Instead, the FastAPI BFF operates an **Identity Adapter** extracting authenticated identity from upstream gateway headers:

| Environment Variable | Default | Purpose |
| :--- | :--- | :--- |
| `AUTH_ENABLED` | `true` | If `false`, identity falls back to `local_user` for offline testing or standalone development. |
| `AUTH_HEADER_USER` | `Remote-User` | Name of the incoming HTTP header containing the verified username (e.g. Authelia, Authentik `X-authentik-username`, or OAuth2-Proxy `X-Forwarded-User`). |
| `AUTH_HEADER_EMAIL` | `Remote-Email` | Name of the HTTP header containing the user's verified email address. |

### Upstream Authentication Workflow
1. Client sends request to `addmovie.roadtotech.me`.
2. Reverse proxy executes forward-auth against the identity provider (Authelia, Authentik, etc.).
3. If valid, the proxy injects the configured identity header (`Remote-User`) and forwards the request to the BFF on `traefik_network`.
4. BFF extracts the verified identity and forwards it across the private gRPC boundary to the Worker for persistent audit logging.

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
