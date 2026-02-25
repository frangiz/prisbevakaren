.PHONY: all check format format-check install test test-unit test-e2e test-integration type-check

check:
	uv run ruff check src tests

format:
	uv run ruff format src tests

format-check:
	uv run ruff format --check src tests

install:
	uv sync

test: test-unit
	@echo "Running unit tests only. To run integration tests, use 'make test-integration'"

test-unit:
	uv run pytest --cov=src --cov-report=html --cov-report=term-missing tests/ --ignore=tests/test_integration.py --ignore=tests/test_e2e.py

test-e2e:
	uv run pytest tests/test_e2e.py -v

test-integration:
	@echo "Running integration tests..."
	./run_integration_tests.sh

type-check:
	uv run mypy --config-file mypy.ini src tests

all: test-unit format check type-check