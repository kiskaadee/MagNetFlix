.PHONY: generate test lint format check

generate:
	@if command -v buf >/dev/null 2>&1; then \
		buf generate; \
	else \
		nix develop --command buf generate; \
	fi

test:
	uv run pytest

lint:
	uv run ruff check .

format:
	uv run ruff format .

check: lint
	uv run pyright
