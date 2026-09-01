# 🎬 MagNetFlix

> Automated, secure movie fetching and library organization pipeline via gRPC, Transmission, and Traefik/Authelia SSO.

---

## 📖 Table of Contents

- [Overview](docs/overview.md) - Project mission, key features, and user workflow.
- [Architecture](docs/architecture.md) - System design, BFF pattern, gRPC contracts, and data flow.
- [Development Rules & Agent Guidelines](AGENTS.md) - Coding standards, monorepo conventions, and toolchain rules.
- [Roadmap](docs/roadmap.md) - Milestone-by-milestone development plan.
- [Deployment Guide](docs/deployment.md) - Docker Compose, Traefik integration, and Authelia SSO setup.

---

## ⚡ Quick Start

```bash
# Enter hermetic dev shell (Nix)
nix develop

# Or install dependencies with uv workspace
uv sync

# Generate protobuf stubs
make generate

# Start full local stack with docker compose
docker compose up -d
```

---

## 📁 Repository Structure

```text
.
├── AGENTS.md                  # Development guidelines & rules for AI/human contributors
├── Makefile                   # High-level build & generation commands
├── README.md                  # Project landing page
├── buf.gen.yaml               # Buf remote plugin generation config
├── buf.yaml                   # Buf module definition
├── docker-compose.yml         # Local development & production compose stack
├── docs/                      # Detailed system documentation
│   ├── architecture.md        # Architecture & component interactions
│   ├── deployment.md          # Traefik & Authelia deployment guide
│   ├── overview.md            # Feature overview & workflow
│   └── roadmap.md             # Development milestones
├── proto/                     # Protocol Buffer definitions
│   └── magnetflix/v1/
│       └── pipeline.proto
└── services/
    ├── bff/                   # FastAPI Web Gateway / HTML Form / Authelia SSO
    │   ├── Dockerfile
    │   ├── pyproject.toml
    │   └── src/bff/
    └── worker/                # gRPC Pipeline Worker & Transmission Coordinator
        ├── Dockerfile
        ├── alembic/
        ├── pyproject.toml
        └── src/worker/
```
