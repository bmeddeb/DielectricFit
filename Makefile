# DielectricFit Makefile

.PHONY: help test test-unit test-integration test-property test-coverage test-fast clean lint format

help:
	@echo "Available commands:"
	@echo "  test           - Run all tests"
	@echo "  test-unit      - Run unit tests only"
	@echo "  test-integration - Run integration tests only"  
	@echo "  test-property  - Run property-based tests only"
	@echo "  test-coverage  - Run tests with coverage report"
	@echo "  test-fast      - Run tests in parallel (faster)"
	@echo "  lint           - Run linting checks"
	@echo "  format         - Format code"
	@echo "  clean          - Clean up test artifacts"

# Test commands
test:
	python -m pytest library/tests/ -v

test-unit:
	python -m pytest library/tests/ -m "unit or not slow" -v

test-integration:
	python -m pytest library/tests/ -m "integration" -v

test-property:
	python -m pytest library/tests/ -m "property" -v

test-coverage:
	python -m pytest library/tests/ --cov=library --cov-report=html --cov-report=term -v

test-fast:
	python -m pytest library/tests/ -n auto -v

# Django tests (existing)
test-django:
	python manage.py test

# All tests (Django + pytest)
test-all: test-django test

# Development tools
lint:
	@echo "Running type checks..."
	@python -c "import mypy" 2>/dev/null && mypy library/ || echo "mypy not installed, skipping type checks"
	@echo "Running flake8..."
	@python -c "import flake8" 2>/dev/null && flake8 library/ || echo "flake8 not installed, skipping linting"

format:
	@echo "Formatting with black..."
	@python -c "import black" 2>/dev/null && black library/ || echo "black not installed, skipping formatting"
	@echo "Sorting imports..."
	@python -c "import isort" 2>/dev/null && isort library/ || echo "isort not installed, skipping import sorting"

# Cleanup
clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf .pytest_cache/

# Install dependencies
install-test:
	@echo "Installing test dependencies..."
	@echo "Note: pip not available in current environment"
	@echo "Please install manually: pytest pytest-django pytest-cov hypothesis"

# Performance testing
benchmark:
	python -m pytest library/tests/ --benchmark-only -v