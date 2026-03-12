.PHONY: test lint fmt check install dev clean

## Development

install: ## Install in development mode
	pip install -e ".[dev,all]"

dev: install ## Alias for install

## Quality

test: ## Run all tests
	pytest tests/ -v --tb=short

test-cov: ## Run tests with coverage report
	pytest tests/ -v --tb=short --cov=mcp_maker --cov-report=term-missing

lint: ## Run linter
	ruff check src/ tests/

fmt: ## Auto-format code
	ruff format src/ tests/

check: lint test ## Run lint + tests (CI equivalent)

## Utilities

clean: ## Remove build artifacts
	rm -rf build/ dist/ *.egg-info src/*.egg-info .pytest_cache .ruff_cache .mypy_cache htmlcov .coverage
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

.DEFAULT_GOAL := help
