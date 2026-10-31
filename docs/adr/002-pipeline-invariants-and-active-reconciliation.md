---
type: decision
status: accepted
project: MagNetFlix
date: 2026-10-29
tags: [architecture, security, storage, metadata, recovery, concurrency, sso, bff]
---

# ADR 002: Pipeline Invariants, Two-Stage Metadata, and Active Reconciliation

## Context and Problem Statement

Following the initial architectural baseline established in [ADR 001](001-pipeline-safety-and-bff-dual-client.md) and the implementation of the SQLite WAL engine, an interactive architectural review identified critical engineering gaps across several core subsystems:

1. **Protobuf Packaging & Build Reproducibility (`GAP-1`)**: The stubs emitted by `buf` produced `ModuleNotFoundError: No module named 'magnetflix'` when imported due to nested package output paths, and generated stubs were excluded from git and static type checks.
2. **Active-Job Concurrency (`GAP-2`)**: Concurrent submissions for the same movie could race past application-level checks and insert duplicate active downloads due to the absence of a database-level uniqueness constraint.
3. **Sanitizer Boundary Policy (`GAP-3`)**: A documented contradiction existed between *purging* non-media files versus *aborting* the entire job if non-allowlisted files exist. Because ~95% of real-world torrents contain `.nfo` or `.txt` clutter, strict rejection causes widespread false-positive failures, while pure whitelisting ignores symlink/executable hazards.
4. **Metadata Resolution Timing (`GAP-5`)**: Fetching TMDB metadata only after download completion leaves the UI live dashboard blank during 30–60 minute downloads and wastes tens of gigabytes of bandwidth on invalid IMDb IDs.
5. **Subtitle Relocation Collisions (`GAP-4`)**: Hardcoding target subtitles to `<Title> (<Year>).en.srt` corrupts non-SRT formats (`.ass`, `.vtt`) and causes silent overwrite collisions when multiple tracks exist.
6. **Crash Recovery & Daemon State (`GAP-6`)**: Simply marking SQLite rows as `FAILED` on worker restart leaves orphaned torrent sessions actively downloading in the Transmission container and abandons scratch disks.
7. **Async Concurrency & Blocking I/O (`GAP-7`)**: Calling multi-gigabyte `shutil.copy2` transfers or synchronous `transmission-rpc` requests directly on Python's async event loop freezes gRPC RPCs and SSE streaming connections.
8. **Pluggable SSO & Search Boundaries (`GAP-8`)**: Hardcoding Authelia headers tightly coupled MagNetFlix to specific homelab infrastructure, and client-side scraping of undocumented IMDb endpoints created browser CORS and fragility risks.

---

## Decision Outcome & Invariants

### 1. Dedicated Workspace Contracts Package (`DEC-1`)
- Stubs are generated once into a shared workspace package `services/contracts` (`module-name = "magnetflix"`).
- Both `worker` and `bff` depend on `magnetflix-contracts` via `{ workspace = true }`, allowing native `from magnetflix.v1 import pipeline_pb2, pipeline_pb2_grpc` imports.
- Generated stubs and `docs/api_spec.md` are committed to Git, enabling reproducible offline test and Docker builds.

### 2. Database Partial Unique Index & Info-Hash Column (`DEC-2`)
- Add an indexed column `info_hash` to `download_jobs`.
- Add a partial unique index in SQLite:
  ```sql
  CREATE UNIQUE INDEX uq_download_jobs_active_imdb_id
  ON download_jobs (imdb_id)
  WHERE state NOT IN ('COMPLETED', 'FAILED');
  ```
- Guaranteed engine-level deduplication: concurrent duplicate submissions fail with `IntegrityError`, mapped cleanly to `grpc.StatusCode.ALREADY_EXISTS`.

### 3. Two-Tier Sanitization Policy (`DEC-3`)
- **Tier 1 (Hard Security Rejection)**: Immediate job abort to `FAILED` if the payload contains symbolic links (`os.path.islink`), hard links (`st_nlink > 1`), path traversal (`..`), special device nodes, or dangerous extensions (`.exe`, `.bat`, `.cmd`, `.sh`, `.scr`, `.vbs`, `.ps1`, `.lnk`, `.iso`, `.zip`, `.rar`, `.7z`).
- **Tier 2 (Allowlist Extraction & Safe Discard)**: Extract allowlisted video (`.mkv`, `.mp4`, `.avi`, `.webm`) and subtitles (`.srt`, `.vtt`, `.sub`, `.ass`). Safely ignore benign clutter (`.nfo`, `.txt`, `.jpg`, `.sfv`). Discard samples (`< 100MB` or `"sample"`). Select the single largest remaining video file as the feature film.

### 4. Two-Stage Metadata Lifecycle (`DEC-4`)
- **Stage 1 (Early Ingestion)**: Query TMDB API `/find/{imdb_id}?external_source=imdb_id` at job submission/queueing time. Verify valid movie entity type; persist `title` and `year` to SQLite immediately. Live UI and SSE streams display movie metadata from second 1.
- **Stage 2 (Post-Download Token Check)**: Compare cached `(title, year)` tokens against primary video filename completely offline from SQLite without external network dependencies.

### 5. Multi-Track Subtitle Preservation & Two-Stage Atomic Swap (`DEC-5`)
- Retain native subtitle extensions (`.srt`, `.vtt`, `.ass`).
- Parse language and forced tags from filenames; append disambiguation indices (`<Title> (<Year>).en.1.srt`) when multiple subtitles share tags to prevent overwrites.
- Copy verified files across storage boundaries to `/media/movies/.staging_<job_id>/`. Pre-check destination existence, then atomically swap via `os.replace`.

### 6. Active Reconciliation & Stalled Timeout (`DEC-6`)
- On worker startup, query all non-terminal SQLite jobs: transition state to `FAILED`, actively call Transmission RPC `remove_torrent(info_hash, delete_data=True)`, and purge scratch directories `/data/staging/<job_id>/` and `/media/movies/.staging_<job_id>/`.
- Monitor swarm progress during `DOWNLOADING`: auto-fail jobs with 0 progress for 15 consecutive minutes.

### 7. Thread Offloading & In-Memory SSE Fan-Out (`DEC-7`)
- Dispatch all blocking disk copies (`shutil.copy2`), synchronous RPC calls (`transmission-rpc`), and directory scans to a bounded `ThreadPoolExecutor(max_workers=4)`.
- Database sessions are strictly short-lived (committed and closed before long I/O).
- Broadcast progress and state change events via an internal `asyncio.Queue` pub/sub broker to connected gRPC/SSE streams.

### 8. Pluggable Identity Adapter & Server-Side Search (`DEC-8`)
- FastAPI BFF middleware reads identity headers via configurable environment variables (`AUTH_ENABLED`, `AUTH_HEADER_USER`, `AUTH_HEADER_EMAIL`) with a safe dev fallback (`local_user`).
- Expose `GET /api/v1/movies/search?q=...` proxying TMDB movie search server-side to eliminate CORS issues and undocumented third-party scraping.
- Mount dual route bindings (`POST /api/v1/downloads` and `POST /download`) with Pydantic aliases (`magnet`/`magnet_uri`, `imdbid`/`imdb_id`).

---

## Consequences

### Positive Consequences
- Guarantees 100% reproducible builds and eliminates `ModuleNotFoundError` across all environments.
- Protects the host and media library from malicious torrent payloads, path traversal, and partial writes.
- Eliminates zombie torrents and leaked staging disk space across container restarts.
- Maintains responsive gRPC and SSE streaming performance during multi-gigabyte disk transfers.
- Decouples MagNetFlix from specific reverse proxy or identity provider implementations.

### Accepted Tradeoffs & Operational Costs
- Requires outbound TMDB API key access on both BFF (for movie search) and Worker (for metadata resolution).
- Requires temporary disk space on `/media/movies` to hold `.staging_<job_id>/` during cross-volume copying.
