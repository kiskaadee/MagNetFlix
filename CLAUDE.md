# Claude Code Specialized Directives — MagNetFlix

## Progressive Context Loading
- Do not load external rule files for simple localized code edits.
- Always inspect `git status` and verify existing files on disk before creating or scaffolding new files.
- Read `AGENTS.md` before making changes affecting database schema, package dependencies, Git state, or cross-component contracts.
- Read `docs/architecture.md` before modifying API routes, gRPC definitions, or worker state machines.
- Read `docs/deployment.md` before changing Dockerfiles, Compose services, or Traefik/Authelia configs.

## Build & Tool Execution Commands
- **Workspace Sync:** `uv sync` (Never use raw `pip`)
- **Workspace Lock:** `uv lock`
- **Protobuf Generation:** `uv run buf generate` (or `make generate`)
- **BFF Dev Server:** `uv run --package magnetflix-bff uvicorn bff.main:app --reload --port 8000`
- **Worker Dev Server:** `uv run --package magnetflix-worker python -m worker.main`
- **Database Migrations:** `uv run --package magnetflix-worker alembic upgrade head`
- **Lint & Format:** `uv run ruff check .` and `uv run ruff format .`
- **Type Checking:** `uv run pyright`
- **Test Suite:** `uv run pytest`

## Auto-Approve Verification Safeguards
- **Permitted Read Operations:** `git status`, `git diff`, `ls`, `cat`, file viewers.
- **Restricted Write Operations:** Multi-service architectural refactors or dependency migrations require direct user confirmation (`/plan` first).
- **Destructive Commands Prohibited:** Never execute `git reset`, `git clean`, `git restore`, or `git checkout` on uncommitted files without explicit permission.
