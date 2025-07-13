.PHONY: help install dev-install test lint format safety-check run-api clean docker-up docker-down

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-20s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install: ## Install production dependencies
	poetry install --no-dev

dev-install: ## Install all dependencies including dev
	poetry install
	pre-commit install

test: ## Run tests with coverage
	poetry run pytest

test-safety: ## Run safety validation tests
	poetry run pytest tests/safety/ -v

lint: ## Run linting checks
	poetry run flake8 src tests
	poetry run mypy src
	poetry run black --check src tests
	poetry run isort --check-only src tests

format: ## Format code
	poetry run black src tests
	poetry run isort src tests

safety-check: ## Validate safety requirements
	@echo "Checking abstraction patterns..."
	@poetry run python scripts/safety/validate_abstractions.py
	@echo "Checking reference validation..."
	@poetry run python scripts/safety/check_references.py

run-api: ## Run the API server
	poetry run uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

docker-up: ## Start Docker services
	docker-compose up -d

docker-down: ## Stop Docker services
	docker-compose down

db-migrate: ## Run database migrations
	./scripts/database/migrate.sh

db-reset: ## Reset database (WARNING: destroys data)
	./scripts/database/reset.sh

clean: ## Clean up generated files
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf .coverage htmlcov .pytest_cache .mypy_cache