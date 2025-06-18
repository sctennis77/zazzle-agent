VENV_NAME=zam
PYTHON=python3
PIP=pip3

.PHONY: help test venv install run run-full run-test-voting clean docker-build docker-run scrape run-generate-image test-pattern run-api stop-api frontend-dev frontend-build frontend-preview frontend-install frontend-lint frontend-clean alembic-init alembic-revision alembic-upgrade alembic-downgrade check-db check-pipeline-db get-last-run run-pipeline-debug run-pipeline-dry-run run-pipeline-single run-pipeline-batch monitor-pipeline logs-tail logs-clear backup-db restore-db reset-db health-check test-interaction-agent create-test-db full_from_fresh_env dev_setup start-services stop-services restart-services status docker-build-all docker-run-local docker-stop-local docker-logs docker-clean k8s-deploy k8s-status k8s-logs k8s-delete deploy-production

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
	@echo "  make run-api      - Start the FastAPI server"
	@echo "  make stop-api     - Stop the FastAPI server"
	@echo "  make frontend-dev - Start the frontend development server"
	@echo "  make test-interaction-agent - Test the Reddit interaction agent"
	@echo "  make create-test-db - Create test database with sample data"
	@echo ""
	@echo "Complete Environment Setup:"
	@echo "  make full_from_fresh_env - Complete fresh setup with cleanup, install, test, and service startup"
	@echo "  make dev_setup          - Quick development setup preserving existing environment"
	@echo "  make start-services     - Start API and frontend services"
	@echo "  make stop-services      - Stop all services"
	@echo "  make restart-services   - Restart all services"
	@echo "  make status             - Check system health and service status"
	@echo ""
	@echo "Docker Commands:"
	@echo "  make docker-build-all   - Build all Docker images (API, Frontend, Pipeline, Interaction)"
	@echo "  make docker-run-local   - Start all services with Docker Compose"
	@echo "  make docker-stop-local  - Stop Docker Compose services"
	@echo "  make docker-logs        - Show Docker Compose logs"
	@echo "  make docker-clean       - Clean up Docker resources"
	@echo ""
	@echo "Kubernetes Commands:"
	@echo "  make k8s-deploy         - Deploy to Kubernetes cluster"
	@echo "  make k8s-status         - Check Kubernetes deployment status"
	@echo "  make k8s-logs           - Show Kubernetes logs"
	@echo "  make k8s-delete         - Delete Kubernetes deployment"
	@echo "  make deploy-production  - Complete production deployment (test, build, deploy)"
	@echo ""
	@echo "For more information, see docs/DEPLOYMENT_GUIDE.md"

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

test-interaction-agent:
	@echo "Testing Reddit interaction agent..."
	. $(VENV_NAME)/bin/activate && $(PYTHON) test_interaction_agent.py

create-test-db:
	@echo "Creating test database with sample data..."
	. $(VENV_NAME)/bin/activate && python3 scripts/create_test_db.py

# =====================
# Complete Fresh Environment Setup
# =====================

full_from_fresh_env:
	@echo "🚀 Starting complete fresh environment setup..."
	@echo "=================================================="
	@echo "Step 1: Stopping existing services..."
	@make stop-api
	@pkill -f "npm run dev" || true
	@echo "✅ Services stopped"
	@echo ""
	@echo "Step 2: Cleaning environment..."
	@make clean
	@echo "✅ Environment cleaned"
	@echo ""
	@echo "Step 3: Installing dependencies..."
	@make install
	@echo "✅ Dependencies installed"
	@echo ""
	@echo "Step 4: Running full test suite..."
	@make test
	@echo "✅ Tests completed"
	@echo ""
	@echo "Step 5: Testing interaction agent..."
	@make test-interaction-agent
	@echo "✅ Interaction agent tested"
	@echo ""
	@echo "Step 6: Starting API server (background)..."
	@make run-api &
	@echo "⏳ Waiting for API to start..."
	@sleep 10
	@echo "✅ API server started"
	@echo ""
	@echo "Step 7: Starting frontend (background)..."
	@cd frontend && npm run dev &
	@echo "⏳ Waiting for frontend to start..."
	@sleep 5
	@echo "✅ Frontend started"
	@echo ""
	@echo "Step 8: Verifying services..."
	@echo "🔍 Checking API health..."
	@curl -s http://localhost:8000/api/generated_products > /dev/null && echo "✅ API responding" || echo "⚠️  API may still be starting"
	@echo "🔍 Checking frontend..."
	@curl -s http://localhost:5173 > /dev/null && echo "✅ Frontend responding" || echo "⚠️  Frontend may still be starting"
	@echo ""
	@echo "🎉 Fresh environment setup complete!"
	@echo "=================================================="
	@echo "📊 Services Status:"
	@echo "   • API Server: http://localhost:8000"
	@echo "   • Frontend: http://localhost:5173"
	@echo "   • Database: zazzle_pipeline.db"
	@echo ""
	@echo "🔧 Available commands:"
	@echo "   • make run-full - Run the complete pipeline"
	@echo "   • make test - Run tests"
	@echo "   • make stop-api - Stop API server"
	@echo "   • make frontend-dev - Start frontend dev server"
	@echo "   • make test-interaction-agent - Test interaction agent"
	@echo ""
	@echo "📝 Next steps:"
	@echo "   1. Open http://localhost:5173 in your browser"
	@echo "   2. Run 'make run-full' to generate a new product"
	@echo "   3. Use the interaction agent to engage with products"
	@echo ""

# =====================
# Quick Development Setup (without full cleanup)
# =====================

dev_setup:
	@echo "⚡ Quick development setup..."
	@echo "=================================================="
	@echo "Step 1: Installing dependencies (if needed)..."
	@if [ ! -d "$(VENV_NAME)" ]; then \
		echo "Creating virtual environment..."; \
		make install; \
	else \
		echo "Virtual environment already exists"; \
	fi
	@echo ""
	@echo "Step 2: Running tests..."
	@make test
	@echo "✅ Tests completed"
	@echo ""
	@echo "Step 3: Starting services..."
	@make run-api &
	@cd frontend && npm run dev &
	@echo "⏳ Services starting..."
	@sleep 5
	@echo "✅ Services started"
	@echo ""
	@echo "🎉 Development setup complete!"
	@echo "   • API: http://localhost:8000"
	@echo "   • Frontend: http://localhost:5173"

# =====================
# Service Management
# =====================

start-services:
	@echo "🚀 Starting all services..."
	@make run-api &
	@cd frontend && npm run dev &
	@echo "⏳ Services starting..."
	@sleep 5
	@echo "✅ All services started"
	@echo "   • API: http://localhost:8000"
	@echo "   • Frontend: http://localhost:5173"

stop-services:
	@echo "🛑 Stopping all services..."
	@make stop-api
	@pkill -f "npm run dev" || true
	@echo "✅ All services stopped"

restart-services:
	@echo "🔄 Restarting all services..."
	@make stop-services
	@sleep 2
	@make start-services

# =====================
# Health Check and Status
# =====================

status:
	@echo "📊 System Status Check"
	@echo "=================================================="
	@echo "🔍 Checking API server..."
	@if curl -s http://localhost:8000/api/generated_products > /dev/null; then \
		echo "✅ API Server: RUNNING (http://localhost:8000)"; \
	else \
		echo "❌ API Server: NOT RUNNING"; \
	fi
	@echo ""
	@echo "🔍 Checking frontend..."
	@if curl -s http://localhost:5173 > /dev/null; then \
		echo "✅ Frontend: RUNNING (http://localhost:5173)"; \
	else \
		echo "❌ Frontend: NOT RUNNING"; \
	fi
	@echo ""
	@echo "🔍 Checking database..."
	@if [ -f "zazzle_pipeline.db" ]; then \
		echo "✅ Database: EXISTS (zazzle_pipeline.db)"; \
		ls -lh zazzle_pipeline.db; \
	else \
		echo "❌ Database: NOT FOUND"; \
	fi
	@echo ""
	@echo "🔍 Checking virtual environment..."
	@if [ -d "$(VENV_NAME)" ]; then \
		echo "✅ Virtual Environment: EXISTS ($(VENV_NAME))"; \
	else \
		echo "❌ Virtual Environment: NOT FOUND"; \
	fi
	@echo ""
	@echo "🔍 Checking frontend dependencies..."
	@if [ -d "frontend/node_modules" ]; then \
		echo "✅ Frontend Dependencies: INSTALLED"; \
	else \
		echo "❌ Frontend Dependencies: NOT INSTALLED"; \
	fi

# =====================
# Docker Commands
# =====================

docker-build-all:
	@echo "🐳 Building all Docker images..."
	@docker build -f Dockerfile.api -t zazzle-agent/api:latest .
	@docker build -f Dockerfile.frontend -t zazzle-agent/frontend:latest .
	@docker build -f Dockerfile.pipeline -t zazzle-agent/pipeline:latest .
	@docker build -f Dockerfile.interaction -t zazzle-agent/interaction:latest .
	@echo "✅ All Docker images built successfully"

docker-run-local:
	@echo "🚀 Starting Zazzle Agent with Docker Compose..."
	@docker-compose up -d
	@echo "✅ Services started. Check http://localhost:5173 for frontend"
	@echo "📊 API available at http://localhost:8000"

docker-stop-local:
	@echo "🛑 Stopping Docker Compose services..."
	@docker-compose down
	@echo "✅ Services stopped"

docker-logs:
	@echo "📋 Showing Docker Compose logs..."
	@docker-compose logs -f

docker-clean:
	@echo "🧹 Cleaning up Docker resources..."
	@docker-compose down -v
	@docker system prune -f
	@echo "✅ Docker cleanup completed"

# =====================
# Kubernetes Commands
# =====================

k8s-deploy:
	@echo "🚀 Deploying to Kubernetes..."
	@kubectl apply -f k8s/namespace.yaml
	@kubectl apply -f k8s/configmap.yaml
	@kubectl apply -f k8s/secrets.yaml
	@kubectl apply -f k8s/persistent-volume.yaml
	@kubectl apply -f k8s/api-deployment.yaml
	@kubectl apply -f k8s/frontend-deployment.yaml
	@kubectl apply -f k8s/pipeline-deployment.yaml
	@kubectl apply -f k8s/interaction-deployment.yaml
	@kubectl apply -f k8s/ingress.yaml
	@echo "✅ Kubernetes deployment completed"

k8s-status:
	@echo "📊 Kubernetes deployment status:"
	@kubectl get pods -n zazzle-agent
	@echo ""
	@echo "🌐 Services:"
	@kubectl get services -n zazzle-agent
	@echo ""
	@echo "🔗 Ingress:"
	@kubectl get ingress -n zazzle-agent

k8s-logs:
	@echo "📋 Showing Kubernetes logs..."
	@kubectl logs -f deployment/zazzle-agent-api -n zazzle-agent

k8s-delete:
	@echo "🗑️ Deleting Kubernetes deployment..."
	@kubectl delete namespace zazzle-agent
	@echo "✅ Kubernetes deployment deleted"

# =====================
# Production Deployment
# =====================

deploy-production:
	@echo "🚀 Starting production deployment..."
	@echo "Step 1: Running tests..."
	@make test
	@echo "Step 2: Building Docker images..."
	@make docker-build-all
	@echo "Step 3: Deploying to Kubernetes..."
	@make k8s-deploy
	@echo "Step 4: Checking deployment status..."
	@make k8s-status
	@echo "✅ Production deployment completed!"

%::
	@: 