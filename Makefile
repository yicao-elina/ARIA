.PHONY: install install-dev test lint benchmark clean

install:
	pip install -e .

install-dev:
	pip install -e ".[dev]"

install-all:
	pip install -e ".[all]"

test:
	python -m pytest tests/ -v

test-cov:
	python -m pytest tests/ -v --cov=aria --cov-report=html

lint:
	ruff check aria/ tests/
	mypy aria/ --ignore-missing-imports

format:
	ruff format aria/ tests/

benchmark:
	python scripts/run_benchmark.py --model qwen2:7b --task forward
	python scripts/run_benchmark.py --model qwen2:7b --task inverse

clean:
	rm -rf build/ dist/ *.egg-info htmlcov/ .coverage
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete