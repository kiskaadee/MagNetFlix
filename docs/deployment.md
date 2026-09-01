# 🚀 MagNetFlix — Deployment & Traefik Integration

This guide details how **MagNetFlix** integrates into the home server stack at `/home/kiskaadee/Deployments/` with **Traefik Reverse Proxy** and **Authelia SSO**.

---

## 🐳 Docker Compose Architecture

MagNetFlix runs as a multi-container stack attached to the shared `traefik_network`:

```yaml
services:
  # 1. FastAPI Web Gateway & Form UI
  bff:
    build:
      context: .
      dockerfile: services/bff/Dockerfile
    restart: unless-stopped
    environment:
      - GRPC_WORKER_HOST=worker:50051
      - APP_ENV=production
    networks:
      - traefik_network
      - magnetflix_internal
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.magnetflix.rule=Host(`addmovie.arch-services.mywire.org`)"
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
      - DATABASE_URL=sqlite:////data/magnetflix.sqlite3
      - STAGING_DIR=/data/staging
      - MEDIA_DIR=/media/movies
    volumes:
      - ./data:/data
      - /mnt/storage/media/movies:/media/movies
    networks:
      - magnetflix_internal

  # 3. Transmission Torrent Daemon
  transmission:
    image: lscr.io/linuxserver/transmission:latest
    restart: unless-stopped
    environment:
      - PUID=1000
      - PGID=1000
      - TZ=America/Chicago
    volumes:
      - ./config/transmission:/config
      - ./data/staging:/downloads
    networks:
      - magnetflix_internal

networks:
  traefik_network:
    external: true
  magnetflix_internal:
    driver: bridge
```

---

## 🔐 Authelia SSO Integration

When a user visits `addmovie.arch-services.mywire.org`:
1. Traefik triggers the `authelia@docker` forward-auth middleware.
2. If unauthenticated, Authelia redirects the user to the login portal.
3. Upon authentication, Authelia injects headers into the forwarded request:
   - `Remote-User`: Username of the logged-in user.
   - `Remote-Email`: Email address.
   - `Remote-Groups`: Group memberships (e.g. `admins`, `family`).
4. FastAPI extracts `request.headers.get("Remote-User")` and passes it to the gRPC worker for audit logging.

---

## 📂 Storage Volumes Configuration

| Mount Path | Type | Purpose |
| :--- | :--- | :--- |
| `/data/magnetflix.sqlite3` | Persistent Volume | SQLite DB with WAL mode for jobs and audit log. |
| `/data/staging` | Fast Scratch Disk | Staging folder where Transmission downloads files. |
| `/media/movies` | Media Storage | Final target destination mounted to Jellyfin/Plex. |
