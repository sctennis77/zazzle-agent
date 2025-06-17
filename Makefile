VENV_NAME=zam
PYTHON=python3
PIP=pip3

.PHONY: help test venv install run run-full run-test-voting clean docker-build docker-run scrape run-generate-image test-pattern run-api stop-api frontend-dev frontend-build frontend-preview frontend-install frontend-lint frontend-clean alembic-init alembic-revision alembic-upgrade alembic-downgrade

help:
	@echo "Available targets:"
	@echo "  make venv         - Create a Python virtual environment"
	@echo "  make install      - Install dependencies into venv"
	@echo "  make test         - Run the test suite with coverage"
	@echo "  make test-pattern - Run a specific test suite or file. Usage: TEST_PATH=tests/test_file.py make test-pattern"
	@echo "  make run-full     - Run the complete product generation pipeline"
	@echo "  make clean        - Remove venv and outputs"
	@echo "  make docker-build - Build Docker image (tests must pass first)"
	@echo "  make docker-run   - Run Docker container"
	@echo "  make scrape       - Run only the scraping part of the program"
	@echo "  make run-generate-image IMAGE_PROMPT=\"<prompt>\" MODEL=<dall-e-2|dall-e-3> - Generate an image with DALL-E and upload to Imgur"
	@echo "  make run-api      - Run the API server"
	@echo "  make stop-api     - Stop the API server"
	@echo "  make frontend-dev      # Start dev server at http://localhost:5173 (or next available port)"
	@echo "  make frontend-build    # Build production bundle"
	@echo "  make frontend-preview  # Preview production build"
	@echo "  make frontend-install  # Install dependencies"
	@echo "  make frontend-lint     # Lint code"
	@echo "  make frontend-clean    # Remove node_modules, .vite, and dist"
	@echo "  make alembic-init     - Initialize Alembic for database migrations"
	@echo "  make alembic-revision - Generate a new Alembic migration revision"
	@echo "  make alembic-upgrade  - Upgrade the database to the latest migration"
	@echo "  make alembic-downgrade - Downgrade the database to the previous migration"

venv:
	$(PYTHON) -m venv $(VENV_NAME)

install: venv
	. $(VENV_NAME)/bin/activate && $(PIP) install --upgrade pip && $(PIP) install -r requirements.txt

test:
	. $(VENV_NAME)/bin/activate && $(PYTHON) -m pytest tests/ --cov=app

test-pattern:
	@if [ -z "$(TEST_PATH)" ]; then \
	  echo "Error: TEST_PATH is not set. Usage: TEST_PATH=tests/test_file.py make test-pattern"; \
	  exit 1; \
	fi
	. $(VENV_NAME)/bin/activate && $(PYTHON) -m pytest $(TEST_PATH) --cov=app

run-full:
	source .env && . $(VENV_NAME)/bin/activate && $(PYTHON) -m app.main --mode full --model "$(MODEL)"

run-generate-image:
	source .env && . $(VENV_NAME)/bin/activate && $(PYTHON) -m app.main --mode image --prompt "$(IMAGE_PROMPT)" --model "$(MODEL)"

clean:
	rm -rf $(VENV_NAME) outputs/ .coverage

# Docker targets

docker-build: test
	docker build -t zazzle-affiliate-agent .

docker-run:
	docker run -v $(PWD)/outputs:/app/outputs zazzle-affiliate-agent 

scrape:
	. $(VENV_NAME)/bin/activate && $(PYTHON) -m app.product_scraper 

run-api:
	@echo "Stopping any existing API instances..."
	@if lsof -ti :8000 > /dev/null; then \
	  echo "Killing process(es) using port 8000:"; \
	  lsof -i :8000; \
	  lsof -ti :8000 | xargs kill -9; \
	fi
	@echo "Waiting for port 8000 to be released..."
	@while lsof -i :8000 > /dev/null; do sleep 1; done
	@echo "Starting API server..."
	. $(VENV_NAME)/bin/activate && $(PYTHON) -m app.api

stop-api:
	@echo "Stopping API server..."
	@if lsof -ti :8000 > /dev/null; then \
	  echo "Killing process(es) using port 8000:"; \
	  lsof -i :8000; \
	  lsof -ti :8000 | xargs kill -9; \
	fi
	@echo "Waiting for port 8000 to be released..."
	@while lsof -i :8000 > /dev/null; do sleep 1; done 

# =====================
# Frontend (React) targets
# =====================

# Start the React development server (hot reload, for local development)
frontend-dev:
	cd frontend && npm run dev

# Build the React frontend for production (outputs to frontend/dist)
frontend-build:
	cd frontend && npm run build

# Preview the production build locally (serves frontend/dist)
frontend-preview:
	cd frontend && npm run preview

# Install frontend dependencies
frontend-install:
	cd frontend && npm install

# Lint the frontend code
frontend-lint:
	cd frontend && npm run lint

# Clean frontend node_modules and cache
frontend-clean:
	rm -rf frontend/node_modules frontend/.vite frontend/dist

# Usage:
#   make frontend-dev      # Start dev server at http://localhost:5173 (or next available port)
#   make frontend-build    # Build production bundle
#   make frontend-preview  # Preview production build
#   make frontend-install  # Install dependencies
#   make frontend-lint     # Lint code
#   make frontend-clean    # Remove node_modules, .vite, and dist 

# Alembic commands
alembic-init:
	@echo "Initializing Alembic for database migrations."
	alembic init alembic

alembic-revision:
	@echo "Generating a new Alembic migration revision."
	alembic revision --autogenerate -m "add comment_summary to RedditPost and remove CommentSummary table"

alembic-upgrade:
	@echo "Upgrading the database to the latest migration."
	alembic upgrade head

alembic-downgrade:
	@echo "Downgrading the database to the previous migration."
	alembic downgrade -1 