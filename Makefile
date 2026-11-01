.PHONY: generate test lint format check

generate:
	nix develop --command buf generate

test:
	uv run pytest

lint:
	uv run ruff check .

format:
	uv run ruff format .

check: lint
	uv run pyright
