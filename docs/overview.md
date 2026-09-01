# 🌟 MagNetFlix — Overview

**MagNetFlix** is a self-hosted, automated media acquisition pipeline. It bridges the gap between web-based movie requests and structured, verified media storage in a secure, audited environment.

---

## 🎯 The Problem & Mission

When self-hosting a media server (Jellyfin/Plex):
1. Adding movies manually requires downloading torrents, monitoring client progress, manually checking for malicious/garbage files, and renaming folders to match IMDb/TMDB conventions.
2. In multi-user setups, tracking who requested what and keeping track of download failures is difficult without a dedicated audit log.

**MagNetFlix** solves this with an end-to-end automated workflow:
- **Input**: A simple web form protected by **Authelia SSO** accepting an **IMDb ID** and a **Magnet URI**.
- **Processing**: A background **gRPC worker** handles downloading via Transmission into a sandboxed staging directory.
- **Safety**: Recursively scans and purges all non-media/dangerous executable files.
- **Organization**: Fetches official metadata for the IMDb ID, verifies movie details, and places renamed media files into your library structure.
- **Observability**: Live status tracking and persistent audit logs.

---

## 🎬 User Workflow

```mermaid
sequenceDiagram
    autonumber
    actor User as Authenticated User
    participant Traefik as Traefik (SSO Protected)
    participant BFF as FastAPI (BFF Gateway)
    participant Worker as gRPC Pipeline Worker
    participant Engine as Transmission Daemon
    participant Media as Jellyfin / Plex Library

    User->>Traefik: GET addmovie.arch-services.mywire.org
    Traefik->>User: Renders MagNetFlix Web Form
    User->>Traefik: Submit form (magnet URI + IMDb ID: tt1375666)
    Traefik->>BFF: POST /api/v1/downloads (includes Remote-User header)
    BFF->>Worker: gRPC SubmitDownload(magnet, imdb_id, user)
    Worker-->>BFF: Acknowledged (Job ID: job-42)
    BFF-->>User: Enqueued! Showing live progress
    Worker->>Engine: Start torrent download in /tmp/staging/job-42
    Engine-->>Worker: Download Completed
    Worker->>Worker: Run Security Whitelist Scan (Purge .exe/.bat)
    Worker->>Worker: Verify IMDb metadata & rename files
    Worker->>Media: Move to /media/movies/Inception (2010) [imdbid-tt1375666]/
    Worker-->>BFF: Status: COMPLETED
    BFF-->>User: Notification: Movie ready in library!
```
