.PHONY: test test-critical test-important test-all test-coverage lint format install-dev clean

# Test commands
test-critical:
	pytest tests/critical/ -v

test-important:
	pytest tests/important/ -v

test-all:
	pytest tests/ -v

test-coverage:
	pytest tests/ --cov=. --cov-report=html --cov-report=term-missing

test-fast:
	pytest tests/critical/ tests/important/ -x --tb=short

# Development setup
install-dev:
	pip install -r requirements.txt
	pip install -r requirements-test.txt
	pre-commit install

# Code quality
lint:
	flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
	flake8 . --count --exit-zero --max-complexity=10 --max-line-length=100 --statistics

format:
	black .
	isort . --profile black

# Security
security:
	bandit -r . -x tests/
	safety check

# Cleanup
clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	rm -rf .coverage htmlcov/ .pytest_cache/

# Run all checks (pre-push)
check-all: lint security test-all
	@echo "✅ All checks passed!"

# Development workflow
dev-test: format lint test-critical
	@echo "✅ Development tests passed!"