# 🎬 MagNetFlix

> Self-hosted, automated media acquisition and library organization pipeline built with **FastAPI (BFF)**, **gRPC**, **SQLite WAL**, **Transmission RPC**, and **pluggable SSO/OIDC authentication**.

---

## 📖 Table of Contents

- [Overview](docs/overview.md) — Mission, user workflow, and features.
- [Architecture](docs/architecture.md) — System design, state machine, security boundaries, and storage invariants.
- [Reconciled Roadmap](docs/roadmap.md) — Dependency-ordered implementation milestones.
- [Deployment Guide](docs/deployment.md) — Docker Compose topology, volume mounts, and SSO identity adapter.
- [Architecture Decision Records](docs/adr/) — Canonical records of design choices, tradeoffs, and invariants:
  - [ADR 001: Pipeline Safety, Storage Boundaries, and BFF Dual-Client Architecture](docs/adr/001-pipeline-safety-and-bff-dual-client.md)
  - [ADR 002: Pipeline Invariants, Two-Stage Metadata, and Active Reconciliation](docs/adr/002-pipeline-invariants-and-active-reconciliation.md)
- [Historical Audit Ledger](docs/history/phase-a-current-state-audit.md) — Phase A current-state audit and portfolio assessment.
- [Development Rules & Agent Guidelines](AGENTS.md) — Code quality standards, safety rules, and workspace invariants.

---

## ⚡ Quick Start

```bash
# 1. Enter hermetic dev shell (Nix)
nix develop

# 2. Or install dependencies with uv workspace
uv sync

# 3. Generate protobuf stubs & documentation
make generate

# 4. Run test suite
uv run pytest

# 5. Run static type checking and linters
make check
```

---

## 📁 Repository Structure

```text
.
├── AGENTS.md                  # Development guidelines & safety invariants
├── CLAUDE.md                  # Developer CLI commands & tool directives
├── Makefile                   # High-level build, codegen, lint, and test targets
├── README.md                  # Project landing page
├── buf.gen.yaml               # Buf code generation configuration
├── buf.yaml                   # Buf module configuration
├── docker-compose.yml         # Multi-container Compose stack specification
├── docs/                      # Authoritative architecture and operations documentation
│   ├── adr/                   # Architecture Decision Records (ADRs)
│   ├── history/               # Audit logs and review ledgers
│   ├── architecture.md        # System design, data flow, and invariants
│   ├── deployment.md          # Container topology and reverse proxy integration
│   ├── overview.md            # Feature overview & workflow
│   └── roadmap.md             # 5-Milestone implementation plan
├── proto/                     # Protocol Buffer definitions
│   └── magnetflix/v1/
│       └── pipeline.proto
├── services/
│   ├── bff/                   # FastAPI Web Gateway / HTML Form / Pluggable SSO
│   ├── contracts/             # Shared Protobuf & gRPC contracts package
│   └── worker/                # gRPC Pipeline Worker & Transmission Coordinator
└── tests/                     # Unit and integration test suites
```
