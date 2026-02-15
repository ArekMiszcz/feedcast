.PHONY: install install-dev fetch generate podcast test lint format clean help

# Default target
help:
	@echo "RSS Podcast Generator - Available commands:"
	@echo ""
	@echo "  make install      Install package"
	@echo "  make install-dev  Install with dev dependencies"
	@echo "  make fetch        Fetch RSS articles"
	@echo "  make generate     Generate podcast from articles"
	@echo "  make podcast      Full pipeline: fetch + generate"
	@echo "  make test         Run tests"
	@echo "  make lint         Run linter"
	@echo "  make format       Format code"
	@echo "  make clean        Remove generated files"
	@echo ""

# Installation
install:
	pip install -e .

install-dev:
	pip install -e ".[dev]"

install-tts:
	pip install torch --index-url https://download.pytorch.org/whl/cu121
	pip install -e ".[tts]"

# Main commands
fetch:
	rss-podcast fetch --days 7

generate:
	rss-podcast generate --script-only

generate-audio:
	rss-podcast generate

podcast:
	rss-podcast pipeline

podcast-en:
	rss-podcast pipeline --language en

# Development
test:
	pytest -v

test-cov:
	pytest -v --cov=src/rss_podcast --cov-report=html

lint:
	ruff check src tests

format:
	ruff format src tests
	ruff check --fix src tests

# Utilities
list-feeds:
	rss-podcast list-feeds

clean:
	rm -rf output/articles/*.json
	rm -rf output/podcasts/*.json
	rm -rf output/podcasts/*.txt
	rm -rf output/podcasts/*.wav
	rm -rf .pytest_cache
	rm -rf htmlcov
	rm -rf .ruff_cache
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

clean-all: clean
	rm -rf *.egg-info
	rm -rf build
	rm -rf dist
