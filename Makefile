VENV_NAME=zam
PYTHON=python3
PIP=pip3

.PHONY: help test venv install run run-full run-test-voting clean docker-build docker-run scrape run-generate-image test-pattern run-api stop-api frontend-dev frontend-build frontend-preview frontend-install frontend-lint frontend-clean alembic-init alembic-revision alembic-upgrade alembic-downgrade check-db check-pipeline-db get-last-run run-pipeline-debug run-pipeline-dry-run run-pipeline-single run-pipeline-batch monitor-pipeline logs-tail logs-clear backup-db restore-db reset-db health-check

help:
	@echo "Available targets:"
	@echo "  make venv         - Create a Python virtual environment"
	@echo "  make install      - Install dependencies into venv"
	@echo "  make test         - Run the test suite with coverage"
	@echo "  make test-pattern <test_path> - Run a specific test suite or file. Example: make test-pattern tests/test_file.py"
	@echo "  make run-full     - Run the complete product generation pipeline"
	@echo "  make run-full SUBREDDIT=<subreddit> - Run pipeline with specific subreddit (e.g., SUBREDDIT=golf)"
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
	@echo ""
	@echo "Database & Monitoring:"
	@echo "  make check-db         - Check database contents and pipeline runs"
	@echo "  make check-pipeline-db - Check pipeline database status"
	@echo "  make get-last-run     - Get details of the last pipeline run"
	@echo "  make backup-db        - Create a backup of the database"
	@echo "  make restore-db       - Restore database from backup"
	@echo "  make reset-db         - Reset database (WARNING: deletes all data)"
	@echo "  make health-check     - Check system health and dependencies"
	@echo ""
	@echo "Pipeline Management:"
	@echo "  make run-pipeline-debug    - Run pipeline with debug logging"
	@echo "  make run-pipeline-dry-run  - Run pipeline without creating products (dry run)"
	@echo "  make run-pipeline-single   - Run pipeline for a single product"
	@echo "  make run-pipeline-batch    - Run pipeline for multiple products"
	@echo "  make monitor-pipeline      - Monitor pipeline status in real-time"
	@echo ""
	@echo "Logging & Debugging:"
	@echo "  make logs-tail        - Tail the application logs"
	@echo "  make logs-clear       - Clear application logs"

venv:
	$(PYTHON) -m venv $(VENV_NAME)

install: venv
	. $(VENV_NAME)/bin/activate && $(PIP) install --upgrade pip && $(PIP) install -r requirements.txt

test:
	. $(VENV_NAME)/bin/activate && TESTING=true $(PYTHON) -m pytest tests/ --cov=app

test-pattern:
	@if [ -z "$(filter-out $@,$(MAKECMDGOALS))" ]; then \
		echo "Error: Please specify a test path. Usage: make test-pattern <test_path>"; \
		echo "Example: make test-pattern tests/test_file.py"; \
		exit 1; \
	fi
	. $(VENV_NAME)/bin/activate && TESTING=true $(PYTHON) -m pytest $(filter-out $@,$(MAKECMDGOALS)) --cov=app

run-full:
	source .env && . $(VENV_NAME)/bin/activate && $(PYTHON) -m app.main --mode full --model "$(MODEL)" $(if $(SUBREDDIT),--subreddit $(SUBREDDIT),)

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

# Database & Monitoring targets

check-db:
	@echo "Checking database contents..."
	. $(VENV_NAME)/bin/activate && python3 -m scripts.check_db

check-pipeline-db:
	@echo "Checking pipeline database status..."
	. $(VENV_NAME)/bin/activate && python3 -m scripts.check_pipeline_db

get-last-run:
	@echo "Getting last pipeline run details..."
	. $(VENV_NAME)/bin/activate && python3 -m scripts.get_last_run

backup-db:
	@echo "Creating database backup..."
	@if [ -f zazzle_pipeline.db ]; then \
		cp zazzle_pipeline.db zazzle_pipeline.db.backup.$$(date +%Y%m%d_%H%M%S); \
		echo "Database backed up to zazzle_pipeline.db.backup.$$(date +%Y%m%d_%H%M%S)"; \
	else \
		echo "No database file found to backup"; \
	fi

restore-db:
	@echo "Available backups:"
	@ls -la zazzle_pipeline.db.backup.* 2>/dev/null || echo "No backups found"
	@echo ""
	@echo "To restore, run: cp zazzle_pipeline.db.backup.<timestamp> zazzle_pipeline.db"

reset-db:
	@echo "WARNING: This will delete all data in the database!"
	@read -p "Are you sure? Type 'yes' to confirm: " confirm; \
	if [ "$$confirm" = "yes" ]; then \
		rm -f zazzle_pipeline.db; \
		echo "Database reset. Run 'make alembic-upgrade' to recreate tables."; \
	else \
		echo "Database reset cancelled."; \
	fi

health-check:
	@echo "Running comprehensive health check..."
	. $(VENV_NAME)/bin/activate && python3 -m scripts.health_check

# Pipeline Management targets

run-pipeline-debug:
	@echo "Running pipeline with debug logging..."
	source .env && . $(VENV_NAME)/bin/activate && LOG_LEVEL=DEBUG $(PYTHON) -m app.main --mode full --model "$(MODEL)" $(if $(SUBREDDIT),--subreddit $(SUBREDDIT),)

run-pipeline-dry-run:
	@echo "Running pipeline in dry-run mode (no products created)..."
	source .env && . $(VENV_NAME)/bin/activate && DRY_RUN=true $(PYTHON) -m app.main --mode full --model "$(MODEL)" $(if $(SUBREDDIT),--subreddit $(SUBREDDIT),)

run-pipeline-single:
	@echo "Running pipeline for single product..."
	source .env && . $(VENV_NAME)/bin/activate && SINGLE_PRODUCT=true $(PYTHON) -m app.main --mode full --model "$(MODEL)" $(if $(SUBREDDIT),--subreddit $(SUBREDDIT),)

run-pipeline-batch:
	@echo "Running pipeline for batch processing..."
	source .env && . $(VENV_NAME)/bin/activate && BATCH_SIZE=5 $(PYTHON) -m app.main --mode full --model "$(MODEL)" $(if $(SUBREDDIT),--subreddit $(SUBREDDIT),)

monitor-pipeline:
	@echo "Starting pipeline monitor..."
	. $(VENV_NAME)/bin/activate && python3 -m scripts.pipeline_monitor

# Logging & Debugging targets

logs-tail:
	@echo "Tailing application logs..."
	@if [ -f app.log ]; then \
		tail -f app.log; \
	else \
		echo "No log file found. Run the application to generate logs."; \
	fi

logs-clear:
	@echo "Clearing application logs..."
	@rm -f app.log
	@rm -f *.log
	@echo "Logs cleared"

%::
	@: 