.PHONY: install test lint run

install:
	cd backend && pip install -e ".[dev]"

test:
	cd backend && pytest

lint:
	cd backend && ruff check .

run:
	cd backend && uvicorn skillforge.api.app:app --reload --port 8000
