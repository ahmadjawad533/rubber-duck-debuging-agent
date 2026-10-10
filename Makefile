.PHONY: help install test test-backend test-frontend build sam-build sam-deploy clean

help:
	@echo "Rubber Duck - Developer Commands:"
	@echo "  make install         Install backend and frontend dependencies"
	@echo "  make test            Run all backend and frontend unit tests"
	@echo "  make test-backend    Run pytest for Lambda backend"
	@echo "  make test-frontend   Run Vitest for React frontend"
	@echo "  make build           Build production frontend assets"
	@echo "  make sam-build       Build AWS SAM template"
	@echo "  make sam-deploy      Deploy backend with AWS SAM"
	@echo "  make clean           Remove build artifacts and caches"

install:
	python3 -m venv .venv
	. .venv/bin/activate && pip install -r backend/requirements.txt
	cd frontend && npm install

test: test-backend test-frontend

test-backend:
	. .venv/bin/activate && PYTHONPATH=backend:. pytest backend/tests/ -v

test-frontend:
	cd frontend && npm test

build:
	cd frontend && npm run build

sam-build:
	cd backend && sam build

sam-deploy:
	cd backend && sam deploy --guided

clean:
	rm -rf frontend/dist frontend/node_modules/.vite .pytest_cache backend/.aws-sam
