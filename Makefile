.PHONY: help build up down logs test lint format clean

# Default target
help:
	@echo "Available commands:"
	@echo "  build     - Build Docker images"
	@echo "  up        - Start all services"
	@echo "  down      - Stop all services"
	@echo "  logs      - Show logs"
	@echo "  test      - Run tests"
	@echo "  lint      - Run linting"
	@echo "  format    - Format code"
	@echo "  clean     - Clean up containers and volumes"
	@echo "  seed      - Seed admin user"
	@echo "  benchmark - Run performance benchmarks"

# Docker commands
build:
	docker compose build

up:
	docker compose up -d

down:
	docker compose down

logs:
	docker compose logs -f

# Development commands
test:
	docker compose exec api pytest

test-cov:
	docker compose exec api pytest --cov=app --cov-report=html

lint:
	docker compose exec api flake8 app tests scripts
	docker compose exec api isort --check-only app tests scripts

format:
	docker compose exec api black app tests scripts
	docker compose exec api isort app tests scripts

# Database commands
seed:
	curl -X POST http://localhost:8000/auth/seed

# Performance testing
benchmark:
	docker compose exec api python scripts/n_plus_one_queries.py
	docker compose exec api python scripts/pagination_comparison.py
	docker compose exec api python scripts/indexing_performance.py
	docker compose exec api python scripts/bulk_operations.py

# Cleanup
clean:
	docker compose down -v
	docker system prune -f
