BACKEND_PYTHON := ./backend/.venv/bin/python
BACKEND_RUFF := ./backend/.venv/bin/ruff
BACKEND_MYPY := ./backend/.venv/bin/mypy
FRONTEND_NEXT := node ./node_modules/next/dist/bin/next

.PHONY: backend-install backend-test backend-lint backend-typecheck frontend-install frontend-build frontend-lint clean

backend-install:
	cd backend && python3 -m venv .venv && ./.venv/bin/python -m pip install -e ".[dev]"

backend-test:
	cd backend && ./.venv/bin/python -m pytest

backend-lint:
	cd backend && ./.venv/bin/ruff check app tests

backend-typecheck:
	cd backend && ./.venv/bin/mypy app

frontend-install:
	cd frontend && npm install

frontend-build:
	cd frontend && $(FRONTEND_NEXT) build

frontend-lint:
	cd frontend && node ./node_modules/eslint/bin/eslint.js app components lib scripts --ext .ts,.tsx --max-warnings=0

clean:
	rm -rf .pytest_cache .venv
	rm -rf backend/.pytest_cache backend/.ruff_cache frontend/.next
	find backend -type d -name __pycache__ -prune -exec rm -rf {} +
