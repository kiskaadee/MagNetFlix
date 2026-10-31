# 📜 Phase A Current-State Architectural Audit & Review Ledger

This historical record captures the findings, gap analysis, and architectural reconciliation conducted during the Phase A and Phase B review of **MagNetFlix** on 2026-10-30.

---

## 1. Initial State Inventory

- **Toolchain**: `uv` workspace with `services/worker` and `services/bff`, packaged via `uv_build`. Nix hermetic devShell in `flake.nix`.
- **Database**: SQLite WAL engine in `services/worker/src/worker/db/engine.py` with strict pragmas (`journal_mode=WAL; foreign_keys=ON; synchronous=NORMAL; busy_timeout=5000`). Initial Alembic migration `234da461ab5b_create_download_jobs_table.py` created the `download_jobs` table.
- **Protobuf**: Contract defined in `proto/magnetflix/v1/pipeline.proto`.
- **Tests**: 5 unit tests in `tests/test_db.py` verifying SQLite pragmas, CRUD operations, state transitions, and idempotency queries.

---

## 2. Identified Discrepancies & Defect Register

During read-only inspection of the repository and its runtime behavior, 8 concrete architectural gaps were validated:

1. **`GAP-1` (Protobuf Package Layout & Broken Imports)**:
   - Generated stubs in `services/worker/src/worker/magnetflix/v1/pipeline_pb2_grpc.py` emitted `from magnetflix.v1 import pipeline_pb2`.
   - Importing failed with `ModuleNotFoundError: No module named 'magnetflix'`.
   - Masked because `pyproject.toml` excluded `services/**/magnetflix/` from `pyright` and `ruff`.
   - Generated stubs were gitignored, and Dockerfiles omitted `buf generate` and Alembic migration scripts.
2. **`GAP-2` (Active Job Concurrency & Idempotency)**:
   - `imdb_id` had only a non-unique index; application-level check-then-insert was vulnerable to TOCTOU races under concurrent submissions.
   - `DownloadJob` had no `info_hash` column to track BitTorrent hashes.
3. **`GAP-3` (Sanitizer Policy Contradiction)**:
   - Documentation contradicted whether to purge non-media clutter (`.nfo`, `.txt`, `.jpg`) or fail the entire job. Strict rejection failed ~95% of real torrents, while pure whitelisting allowed malicious symlinks and traversal payloads.
4. **`GAP-4` (Subtitle Selection & Relocation Collisions)**:
   - Sanitizer accepted `.srt`, `.vtt`, `.sub`, `.ass`, but relocator spec forced `<Title> (<Year>).en.srt`, corrupting non-SRT formats and overwriting multi-track subtitles.
5. **`GAP-5` (Metadata Resolution Timing)**:
   - Querying TMDB only after download left UI live dashboard titles blank during downloads and wasted gigabytes on invalid IDs.
6. **`GAP-6` (Crash Recovery & Daemon State)**:
   - Marking DB rows `FAILED` on restart left Transmission actively downloading torrents and abandoned staging disks.
7. **`GAP-7` (Async Concurrency & Blocking Disk I/O)**:
   - Synchronous `shutil.copy2` on 30GB files and synchronous `transmission-rpc` blocked Python's single async event loop, freezing gRPC and SSE streams.
8. **`GAP-8` (SSO Decoupling & Movie Search)**:
   - Hardcoded Authelia headers tightly coupled the app to specific homelab infrastructure. Prototype extension queried undocumented IMDb APIs directly from the browser.

---

## 3. Accepted Architectural Decisions Summary

| Decision ID | Area | Accepted Resolution |
| :--- | :--- | :--- |
| **`DEC-1`** | Protobuf Packaging | Dedicated `services/contracts` workspace package (`magnetflix` module); commit stubs and docs to Git; update Dockerfiles. |
| **`DEC-2`** | Database Hardening | Add SQLite partial unique index `uq_download_jobs_active_imdb_id` (`WHERE state NOT IN ('COMPLETED', 'FAILED')`) and indexed `info_hash` column. |
| **`DEC-3`** | Sanitizer Boundary | Two-tier sanitizer: hard-fail on symlinks, hard links, traversal, special files, executables/archives; ignore benign clutter; extract allowlisted media; select largest primary video. |
| **`DEC-4`** | TMDB Metadata | Two-stage lifecycle: resolve TMDB `(title, year)` early on ingestion to validate ID and populate UI; verify token overlap post-download offline from SQLite cache. |
| **`DEC-5`** | Subtitle Relocation | Multi-track format preservation: retain `.srt`/`.vtt`/`.ass` extensions, parse language/forced tags with disambiguation indices (`.en.1.srt`), safe two-stage atomic directory swap. |
| **`DEC-6`** | Crash Recovery | Active startup reconciliation sweep: auto-fail orphaned DB jobs, purge staging directories, remove torrents from Transmission via `info_hash`; enforce 15-min stall timeout. |
| **`DEC-7`** | Async Concurrency | Bounded `ThreadPoolExecutor(max_workers=4)` for blocking disk I/O and RPCs; short-lived DB sessions; in-memory `asyncio.Queue` pub/sub broadcaster for SSE. |
| **`DEC-8`** | Pluggable Auth & Search | Configurable SSO identity adapter middleware (`AUTH_HEADER_USER`); server-side TMDB search proxy (`GET /api/v1/movies/search`); dual route bindings (`POST /api/v1/downloads` & `POST /download`). |

---

## 4. Portfolio Engineering Assessment

- **Key Competencies**: Clean separation of concerns (BFF + gRPC Worker + Transmission daemon); defense-in-depth security boundary; cross-volume filesystem atomicity (`EXDEV` safe); SQLite WAL concurrency; non-blocking async architecture.
- **Scope Discipline**: Explicitly designed as a robust single-node self-hosted pipeline; BitTorrent daemon boundary respected; no speculative microservice bloat.
