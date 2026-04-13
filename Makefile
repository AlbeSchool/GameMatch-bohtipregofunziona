.PHONY: help install dev test format lint clean docker-build docker-run

help:
	@echo "🎮 GameMatch — Available Commands"
	@echo ""
	@echo "Setup:"
	@echo "  make install        Install dependencies"
	@echo "  make dev            Run development server"
	@echo ""
	@echo "Quality:"
	@echo "  make format         Format code with black"
	@echo "  make lint           Lint code with flake8"
	@echo "  make test           Run tests with pytest"
	@echo ""
	@echo "Docker:"
	@echo "  make docker-build   Build Docker images"
	@echo "  make docker-run     Run containers with docker-compose"
	@echo "  make docker-down    Stop containers"
	@echo ""
	@echo "Cleanup:"
	@echo "  make clean          Remove cache and build files"

install:
	pip install -r requirements.txt

dev:
	uvicorn app.main:app --reload --port 8000

format:
	black app/

lint:
	flake8 app/ --max-line-length=100

test:
	pytest

docker-build:
	docker-compose build

docker-run:
	docker-compose up -d

docker-down:
	docker-compose down

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache/
	rm -rf htmlcov/
	rm -rf dist/
	rm -rf build/
	rm -rf *.egg-info/

db-init:
	alembic upgrade head

db-migrate:
	alembic revision --autogenerate
