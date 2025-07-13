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
	@echo "🛡️  Running comprehensive safety validation..."
	@echo "Checking abstraction patterns..."
	@poetry run python scripts/safety/validate_abstractions.py
	@echo "Checking reference validation..."
	@poetry run python scripts/safety/check_references.py
	@echo "Scanning for concrete references..."
	@poetry run python scripts/safety/scan_concrete_refs.py
	@echo "Validating safety scores..."
	@poetry run python scripts/safety/validate_safety_scores.py

security-scan: ## Run security scanning tools
	@echo "🔍 Running security scans..."
	@poetry run bandit -r src/ -f json -o safety-reports/bandit-report.json
	@poetry run safety check --json --output safety-reports/safety-report.json
	@poetry run semgrep --config=auto src/ --json --output=safety-reports/semgrep-report.json

secrets-scan: ## Scan for leaked secrets
	@echo "🔐 Scanning for secrets..."
	@poetry run detect-secrets scan --all-files --baseline .secrets.baseline
	@poetry run python-secrets-scanner src/

safety-full: security-scan secrets-scan safety-check ## Run all safety and security checks
	@echo "✅ Full safety validation complete"

pre-commit-install: ## Install pre-commit hooks with safety validation
	@poetry run pre-commit install
	@echo "🔗 Pre-commit hooks installed with safety validation"

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

abstraction-test: ## Test abstraction framework
	@echo "🧪 Testing abstraction framework..."
	@poetry run python -c "from src.core.abstraction.concrete_engine import ConcreteAbstractionEngine; print('✅ Abstraction framework ready')"
	@poetry run python -c "from src.core.validation.memory_validator import MemoryValidationPipeline; print('✅ Validation pipeline ready')"
	@poetry run python -c "from src.core.metrics.safety_metrics import SafetyMetricsCollector; print('✅ Safety metrics ready')"

safety-reports: ## Create safety reports directory
	@mkdir -p safety-reports

clean: ## Clean up generated files
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf .coverage htmlcov .pytest_cache .mypy_cache safety-reports/
	rm -rf .safety-cache/ .abstraction/

clean-safety: ## Clean safety-specific cache files
	rm -rf .safety-cache/ .abstraction/ abstraction-cache/
	rm -f reference-detection.log safety-validation.log concrete-references.log abstraction-quality.log