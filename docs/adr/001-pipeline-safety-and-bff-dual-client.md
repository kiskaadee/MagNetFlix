---
type: decision
status: accepted
project: MagNetFlix
date: 2026-10-13
tags: [architecture, security, storage, bff, grpc, api, webextension]
---

# ADR 001: Pipeline Safety, Storage Boundaries, and BFF Dual-Client Architecture

## Context and Problem Statement

MagNetFlix automates media acquisition from user submission to structured library organization for Jellyfin and Plex. During architectural audit and alignment with an existing browser extension proof-of-concept (`magnetflix-extension`), several critical design questions and operational hazards were identified:

1. **Client & API Alignment**: How should public users interact with the system? Should the web portal and browser extension require separate backends or conflicting API contracts?
2. **Security & Ingress Boundary**: How can torrent downloading be offered to authenticated home users without exposing the underlying Transmission daemon or internal disk structures to the public network?
3. **Cross-Volume Storage Integrity**: Downloads occur on fast scratch disks (`/data/staging`), while final libraries live on large storage pools (`/media/movies`). Moving files across filesystem boundaries cannot be done via atomic filesystem links (`EXDEV`). How do we prevent media servers from indexing 30GB media files while they are still being copied?
4. **Metadata Authority**: Should metadata matching rely on web scraping (IMDb HTML scraping) or structured API integration (TMDB)?
5. **Daemon Lifecycle & Path Alignment**: How do we prevent container volume path translation errors and eliminate ghost torrent sessions in Transmission daemon state?

## Decision Drivers

* **Minimal Attack Surface**: Zero public exposure of torrent engines, RPC ports, or staging filesystems.
* **Ingestion Atomicity**: Guarantee that Jellyfin/Plex will never detect, lock, or play a partially transferred file.
* **Deterministic Metadata Verification**: Authoritative title/year verification without fragility to HTML changes or IP rate-limiting.
* **Client Versatility with Zero Divergence**: Unified support for both a self-hosted Web UI and a companion browser WebExtension without managing divergent APIs or CORS holes.
* **Resource Hygiene**: Guaranteed reclamation of disk space and torrent session memory on terminal success or failure.

## Considered Options

* **Option 1: Direct Exposed Torrent Client with Script Hooks**: Expose Transmission's Web UI directly via reverse proxy and rely on `torrent-done-script.sh` bash scripts for post-processing.
* **Option 2: Monolithic FastAPI Application**: Run HTTP endpoints, in-process BitTorrent client (`libtorrent`), and media processing inside a single Python process.
* **Option 3: Decoupled FastAPI BFF + Private gRPC Pipeline Worker + Isolated Transmission Daemon (Dual-Client Compatible)**:
  * FastAPI acts as a Backend-for-Frontend (BFF), serving the web UI directly on `addmovie.roadtotech.me` behind Traefik/Authelia SSO, and providing dual API route bindings.
  * Worker runs as a private gRPC service coordinating an isolated Transmission daemon over an internal Docker bridge.
  * Filesystem operations enforce a two-stage copy-and-swap on the target volume.

## Decision Outcome

Chosen option: **Option 3**, because it provides complete physical separation between the public ingress tier and the torrent/filesystem execution tier while supporting both the browser extension and the web UI through a single API surface.

---

### Summary of Architectural Commitments

#### 1. Dual-Client BFF Gateway & Web UI Hosting
* The FastAPI BFF directly serves the public web UI (adapted from the standalone `app.html` design) as a single-origin application behind Traefik and Authelia forward-auth.
* The BFF simultaneously acts as the API backend for the companion browser extension (`magnetflix-extension`).
* To support both clients without friction:
  * Dual route bindings are established: `POST /api/v1/downloads` (canonical) and `POST /download` (extension alias).
  * Inbound Pydantic schemas accept both naming conventions via validation aliases: `magnet` / `magnet_uri` and `imdbid` / `imdb_id`.
* The BFF extracts authenticated user identity strictly from the Traefik `Remote-User` header. In local development or extension contexts lacking SSO headers, a deterministic fallback (`local_user`) is applied.

#### 2. Engine & Network Isolation (Defense-in-Depth)
* Transmission daemon and gRPC Worker run strictly on a private, internal Docker bridge (`magnetflix_internal`).
* Neither Transmission's web interface nor its RPC port (9091) is exposed to the host or internet.
* Transmission is controllable exclusively through the Worker's `transmission-rpc` client wrapper.

#### 3. Storage Boundary: Two-Stage Atomic Relocation
* Because scratch staging (`/data/staging`) and destination libraries (`/media/movies`) reside on separate storage mounts, file moves across devices require a copy-and-delete.
* To prevent media servers from indexing in-flight transfers:
  1. **Transfer Stage**: Media and subtitle files are copied from `/data/staging/<job_id>/` to `/media/movies/.staging_<job_id>/` using Python's `shutil.copy2`.
  2. **Atomic Swap Stage**: Once copying is complete and size is verified, `os.replace` atomically renames `/media/movies/.staging_<job_id>/` to the canonical destination directory `/media/movies/<Title> (<Year>) [imdbid-<IMDbID>]/`.
* Because the staging folder and final directory reside on the **same target filesystem**, `os.replace` is an instant, atomic metadata pointer update.

#### 4. Container Path Alignment
* Transmission and Worker mount the staging directory to the identical absolute path (`/data/staging`). This eliminates container path translation logic when dispatching RPC download commands.

#### 5. Authoritative Metadata Verification via TMDB API
* Media verification uses the official **The Movie Database (TMDB) API** (`/find/{imdb_id}?external_source=imdb_id`) via `httpx`.
* Scraping libraries (Cinemagoer) are rejected to eliminate fragile HTML parsing and IP blocking.
* Verified movie titles and release years must have positive normalized token overlap with the torrent payload name before organizing; zero overlap aborts the job to `FAILED`.

#### 6. Lifecycle Cleanup & Timeout Guarantees
* When a job reaches a terminal state (`COMPLETED` or `FAILED`):
  * The scratch directory `/data/staging/<job_id>/` is purged immediately.
  * The torrent session is removed from Transmission daemon via RPC `remove_torrent(id, delete_data=True)` to prevent memory leaks and tracker retention.
* If a torrent makes zero progress (0 bytes downloaded or unretrieved magnet metadata) for 15 consecutive minutes, the job transitions to `FAILED` with reason `"Download stalled: no seeds or metadata timeout"`.

---

## Pros and Cons of the Options

### Option 1: Direct Exposed Torrent Client with Script Hooks
* Good, because minimal initial code is needed.
* Bad, because exposes Transmission's attack surface to the internet; error handling in post-processing bash scripts is brittle and lacks transaction safety or audit logs.

### Option 2: Monolithic FastAPI Application
* Good, because single process to deploy.
* Bad, because CPU/disk I/O from torrent piece verification blocks Python async event loops; web vulnerabilities directly expose filesystem permissions; crashing the API kills ongoing torrent swarms.

### Option 3: Decoupled BFF + Private Worker + Two-Stage Relocation (Adopted)
* Good, because complete isolation of untrusted network traffic from disk-writing engines; unified API serves both web UI and extension; atomic move eliminates race conditions with Jellyfin/Plex.
* Bad, because cross-volume copying temporarily doubles disk usage during the `ORGANIZING` phase; requires an external TMDB API key.

---

## Consequences

### Positive Consequences
* Media library scanners (Jellyfin/Plex) never lock or ingest corrupted, partially written files.
* Single-origin web UI eliminates CORS configuration for standard users, while Pydantic aliases maintain 100% backward compatibility with the browser extension.
* Transmission daemon is entirely insulated from public network access.
* Staging directories and Transmission sessions are cleanly reclaimed on both success and failure.

### Negative Consequences & Accepted Trade-offs
* Requires storage capacity on `/media/movies` to accommodate temporary copy staging (`.staging_<job_id>`) for the largest single feature film before atomic swap.
* Worker requires outbound internet access to query TMDB API over HTTPS.

---

## More Information

* **Canonical Architecture**: [`docs/architecture.md`](../architecture.md)
* **Deployment & Networking Spec**: [`docs/deployment.md`](../deployment.md)
* **Browser Extension Reference**: Companion extension proof-of-concept located at `magnetflix-extension`.
