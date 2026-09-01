.PHONY: generate test lint format check

generate:
	uv run buf generate

lint:
	uv run ruff check .

format:
	uv run ruff format .

check: lint
	uv run pyright
