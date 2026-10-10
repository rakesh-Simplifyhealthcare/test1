.PHONY: install dev lint format typecheck test migrate run

install:
	pip install -e ".[dev]"

dev: install
	pre-commit install

lint:
	ruff check .

format:
	ruff format .

typecheck:
	mypy app

test:
	pytest -v

migrate:
	alembic upgrade head

run:
	uvicorn app.main:app --reload
