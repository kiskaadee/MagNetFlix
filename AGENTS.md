# Project Guidelines & Safety Rules for AI Agents

## 1. Mission & Authority

**MagNetFlix** is a self-hosted, automated media acquisition pipeline built around **FastAPI (BFF) + gRPC (Worker) + UV Workspaces + SQLite3 WAL + Transmission + Traefik/Authelia SSO**.
- **Architecture Documentation** (`docs/architecture.md`), **Roadmap** (`docs/roadmap.md`), and **Deployment Specifications** (`docs/deployment.md`) define the authoritative design.
- **Implementation autonomy ≠ Architectural autonomy.** Do not replace technologies, dependencies, or storage strategies without explicit approval.

---

## 2. Working Tree Authority & Safety (MANDATORY)

The working tree represents the user's active work.
1. **Inspect First:** Run `git status` and read target files before modifying anything.
2. **Never Overwrite Blindly:** Use available file-reading tools. Preserve user comments, links, and conventions. Prefer surgical edits over wholesale overwrites.
3. **No Destructive Git Commands:** Never run `reset --hard`, `clean -fd`, `restore`, `checkout`, `stash`, `rebase`, or `amend` without explicit permission.
4. **Final Diff Verification:** Before completing work, run `git status` and `git diff` to verify that no unrelated user changes were modified or discarded. Distinguish user changes from agent changes in completion reports.

---

## 3. Architecture & Component Contracts (Progressive Triggers)

- **Read `docs/architecture.md`** before modifying API contracts, changing gRPC/Protobuf definitions, or crossing BFF/Worker/Transmission boundaries.
- **Read `docs/deployment.md`** before altering networking, Traefik routing, Authelia SSO middleware, or Docker volume bindings.
- **Stop and Ask:** If an implementation conflicts with documentation or an ambiguous requirement materially affects architecture, stop and ask the user rather than guessing or silently changing the design.
- **No Speculative Robustness:** Do not add unrequested fallback layers, complex generic abstractions, or future-proofing bloat.

---

## 4. Operational Invariants

### 4.1 Persistence & Audit (SQLite3 WAL)
- Database must operate in **WAL mode** (`PRAGMA journal_mode=WAL;`) with foreign keys enabled (`PRAGMA foreign_keys=ON;`) and `PRAGMA synchronous=NORMAL;`.
- Use SQLAlchemy's async interface via `aiosqlite`.
- Do not create ad-hoc connections outside the application session/engine lifecycle.
- Store database strictly on local volume mounts (`/data/magnetflix.sqlite3`). Never place SQLite on network shares (NFS/SMB).
- All schema changes must be managed through Alembic migrations.

### 4.2 Tooling, Dependencies & Protobuf
- **Python Workspaces:** Use `uv` at the workspace root. Never manually edit `uv.lock` (run `uv lock`). Never use raw `pip`.
- **Protobuf & Code Generation:**
  - Define proto contracts strictly in `proto/magnetflix/v1/`.
  - Regenerate stubs using `uv run buf generate` (or `make generate`).
  - Every proto service, RPC, message, and field **must** include descriptive `//` comments.
- **Code Quality:** All code must pass `uv run ruff check .` and `uv run pyright`.

### 4.3 Pipeline Safety & File-System Invariants
- **Isolated Staging:** Downloads must be confined to an isolated temporary scratch path (e.g., `/data/staging/<job_id>`).
- **File Whitelist Sanitization:**
  - Whitelist: Video (`.mkv`, `.mp4`, `.avi`, `.webm`) and Subtitles (`.srt`, `.vtt`, `.sub`, `.ass`).
  - Quarantine / Reject: Executables, binaries, scripts, or archives (`.exe`, `.bat`, `.cmd`, `.sh`, `.scr`, `.vbs`, `.lnk`, `.iso`, `.zip`, `.rar`).
- Clean up staging directories immediately after successful file relocation or upon terminal failure.

---

## 5. Verification & Completion

Every task must be verified before declaring completion:
1. Run linters, formatters, and type checks: `uv run ruff check .` and `uv run pyright`.
2. Run test suites when tests are present: `uv run pytest`.
3. Verify protobuf stubs compile cleanly when `.proto` files are touched: `uv run buf generate`.
4. Report: (1) What changed, (2) Files modified/created, (3) Verification performed, (4) Unverified areas/risks.
