# 🌟 MagNetFlix — Overview

**MagNetFlix** is a self-hosted, automated media acquisition pipeline. It bridges the gap between web-based movie requests and structured, verified media storage in a secure, audited environment.

---

## 🎯 The Problem & Mission

When self-hosting a media server (Jellyfin/Plex):
1. Adding movies manually requires downloading torrents, monitoring client progress, manually checking for malicious/garbage files, and renaming folders to match IMDb/TMDB conventions.
2. In multi-user setups, tracking who requested what and keeping track of download failures is difficult without a dedicated audit log.

**MagNetFlix** solves this with an end-to-end automated workflow:
- **Input**: A simple web form protected by **pluggable reverse-proxy / OIDC SSO** accepting an **IMDb ID** and a **Magnet URI**.
- **Processing**: A background **gRPC worker** handles downloading via Transmission into a sandboxed staging directory.
- **Safety**: Recursively scans staging payloads, ignoring benign clutter while hard-failing jobs containing dangerous executables, archives, symlinks, or path traversal.
- **Organization**: Resolves official TMDB metadata for the IMDb ID at ingestion, verifies movie tokens post-download, and atomically places renamed media files into your library structure.
- **Observability**: Live status tracking and persistent audit logs.

---

## 🎬 User Workflow

```mermaid
sequenceDiagram
    autonumber
    actor User as Authenticated User
    participant Proxy as Reverse Proxy (SSO Protected)
    participant BFF as FastAPI (BFF Gateway)
    participant Worker as gRPC Pipeline Worker
    participant Engine as Transmission Daemon
    participant Media as Jellyfin / Plex Library

    User->>Proxy: GET https://<MAGNETFLIX_HOST>
    Proxy->>User: Renders MagNetFlix Web Form
    User->>Proxy: Submit form (magnet URI + IMDb ID: tt1375666)
    Proxy->>BFF: POST /api/v1/downloads (includes AUTH_HEADER_USER header)
    BFF->>Worker: gRPC SubmitDownload(magnet, imdb_id, user)
    Worker->>Worker: Resolve TMDB title/year (Stage 1)
    Worker-->>BFF: Acknowledged (Job ID: job-42)
    BFF-->>User: Enqueued! Showing live progress
    Worker->>Engine: Start torrent download in /data/staging/job-42
    Engine-->>Worker: Download Completed
    Worker->>Worker: Run Two-Tier Security Scan (Hard-fail .exe/.bat)
    Worker->>Worker: Verify cached TMDB title/year tokens & rename files
    Worker->>Media: Atomic swap to /media/movies/Inception (2010) [imdbid-tt1375666]/
    Worker-->>BFF: Status: COMPLETED
    BFF-->>User: Notification: Movie ready in library!
```
