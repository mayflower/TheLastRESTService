.PHONY: dev install run test lint

install:
	uv sync --dev

dev:
	uv run uvicorn app.main:app --reload

run:
	uv run uvicorn app.main:app --host 0.0.0.0 --port 8080

lint:
	@echo "lint target pending tooling setup"

test:
	uv run pytest
