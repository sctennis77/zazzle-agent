VENV_NAME=zam
PYTHON=python3
PIP=pip3
POETRY=poetry

.PHONY: help test venv install run run-full run-test-voting clean docker-build docker-run scrape run-generate-image test-pattern run-api stop-api frontend-dev frontend-build frontend-preview frontend-install frontend-lint frontend-clean alembic-init alembic-revision alembic-upgrade alembic-downgrade check-db check-pipeline-db get-last-run run-pipeline-debug run-pipeline-dry-run run-pipeline-single run-pipeline-batch monitor-pipeline logs-tail logs-clear backup-db restore-db reset-db health-check test-interaction-agent create-test-db full_from_fresh_env dev_setup start-services stop-services restart-services status docker-build-all docker-run-local docker-stop-local docker-logs docker-clean k8s-deploy k8s-status k8s-logs k8s-delete deploy-production format lint type-check install-poetry install-deps export-requirements deploy deploy-clean deploy-quick validate-deployment deployment-status run-pipeline show-logs show-logs-api show-logs-pipeline show-logs-frontend setup-dev setup-prod setup-quick health-check health-logs backup-db restore-db check-db cleanup restart

help:
	@echo "Available targets:"
	@echo ""
	@echo "🚀 CRITICAL - Production Deployment:"
	@echo "  make setup-prod     - Setup production environment (CRITICAL)"
	@echo "  make deploy         - Deploy from scratch (CRITICAL)"
	@echo "  make deploy-clean   - Deploy with clean images"
	@echo "  make deploy-quick   - Quick deployment (skip pipeline)"
	@echo ""
	@echo "🏥 CRITICAL - Health Monitoring:"
	@echo "  make health-check   - Essential health check (CRITICAL)"
	@echo "  make health-logs    - Health check with logs (CRITICAL)"
	@echo "  make deployment-status - Show deployment status (CRITICAL)"
	@echo "  make validate-deployment - Validate deployment (CRITICAL)"
	@echo ""
	@echo "💾 CRITICAL - Database Safety:"
	@echo "  make backup-db      - Database backup (CRITICAL)"
	@echo "  make backup-list    - List available backups (ESSENTIAL)"
	@echo "  make restore-db DB=file.db - Database restore (CRITICAL)"
	@echo "  make check-db       - Check database (CRITICAL)"
	@echo ""
	@echo "📊 CRITICAL - Operations:"
	@echo "  make show-logs      - Show all logs (CRITICAL)"
	@echo "  make show-logs-api  - Show API logs"
	@echo "  make show-logs-pipeline - Show pipeline logs"
	@echo "  make run-pipeline   - Run pipeline manually (CRITICAL)"
	@echo ""
	@echo "🔧 CRITICAL - Maintenance:"
	@echo "  make cleanup        - Quick cleanup (ESSENTIAL)"
	@echo "  make restart        - Emergency restart (CRITICAL)"
	@echo ""
	@echo "🔧 Development (Optional):"
	@echo "  make setup-dev      - Setup development environment"
	@echo "  make setup-quick    - Quick setup (skip API tests)"
	@echo "  make install-deps   - Install dependencies"
	@echo "  make test           - Run test suite"
	@echo "  make format         - Format code"
	@echo "  make lint           - Lint code"
	@echo ""
	@echo "💡 Quick Start (Production):"
	@echo "  1. make setup-prod  # Setup environment"
	@echo "  2. make deploy      # Deploy application"
	@echo "  3. make health-check # Verify deployment"
	@echo "  4. make backup-db   # Create database backup"
	@echo ""
	@echo "🆘 Emergency Procedures:"
	@echo "  make restart        # Restart all services"
	@echo "  make cleanup        # Clean up Docker resources"
	@echo "  make health-logs    # Check health with logs"

# =====================
# Development Setup
# =====================

install-poetry:
	@echo "Installing Poetry..."
	curl -sSL https://install.python-poetry.org | python3 -
	@echo "Please add Poetry to your PATH: export PATH=\"/Users/samuelclark/.local/bin:\$$PATH\""

install-deps:
	@echo "Installing dependencies with Poetry..."
	$(POETRY) install

format:
	@echo "Formatting code with black and isort..."
	$(POETRY) run black .
	$(POETRY) run isort .

lint:
	@echo "Linting code with flake8..."
	$(POETRY) run flake8 app/ tests/

type-check:
	@echo "Running type checking with mypy..."
	$(POETRY) run mypy app/

# Legacy venv target for backward compatibility
venv:
	@echo "This project now uses Poetry. Run 'make install-deps' instead."

# Legacy install target for backward compatibility
install: install-deps

test:
	$(POETRY) run pytest tests/ --cov=app

test-pattern:
	@if [ -z "$(filter-out $@,$(MAKECMDGOALS))" ]; then \
		echo "Error: Please specify a test path. Usage: make test-pattern <test_path>"; \
		echo "Example: make test-pattern tests/test_file.py"; \
		exit 1; \
	fi
	$(POETRY) run pytest $(filter-out $@,$(MAKECMDGOALS)) --cov=app

# =====================
# Core Application Commands
# =====================

run-full:
	source .env && $(POETRY) run python -m app.main --mode full --model "$(MODEL)" $(if $(SUBREDDIT),--subreddit $(SUBREDDIT),)

run-generate-image:
	source .env && $(POETRY) run python -m app.main --mode image --prompt "$(IMAGE_PROMPT)" --model "$(MODEL)"

clean:
	$(POETRY) cache clear --all pypi
	rm -rf outputs/ .coverage
	@echo "(DB is preserved)"

# =====================
# Docker Commands
# =====================

docker-build: test
	docker build -t zazzle-affiliate-agent .

docker-run:
	docker run -v $(PWD)/outputs:/app/outputs zazzle-affiliate-agent 

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
# API Management
# =====================

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
	$(POETRY) run python -m app.api

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
# Task Runner Management
# =====================

run-task-runner:
	@echo "Starting Task Runner service..."
	$(POETRY) run python -m app.task_runner

run-task-runner-once:
	@echo "Running Task Runner once..."
	$(POETRY) run python -c "import asyncio; from app.task_runner import TaskRunner; asyncio.run(TaskRunner().run_once())"

add-front-task:
	@echo "Adding front page task to queue..."
	$(POETRY) run python -c "from app.db.database import SessionLocal; from app.task_queue import TaskQueue; session = SessionLocal(); queue = TaskQueue(session); task = queue.add_front_task(); print(f'Added front page task {task.id}'); session.close()"

show-task-queue:
	@echo "Showing task queue status..."
	$(POETRY) run python -c "from app.db.database import SessionLocal; from app.task_queue import TaskQueue; session = SessionLocal(); queue = TaskQueue(session); status = queue.get_queue_status(); import json; print(json.dumps(status, indent=2)); session.close()"

cleanup-stuck-tasks:
	@echo "Cleaning up stuck tasks..."
	$(POETRY) run python -c "from app.db.database import SessionLocal; from app.task_queue import TaskQueue; session = SessionLocal(); queue = TaskQueue(session); cleaned = queue.cleanup_stuck_tasks(); print(f'Cleaned up {cleaned} stuck tasks'); session.close()"

# =====================
# Frontend (React) targets
# =====================

frontend-dev:
	cd frontend && npm run dev

frontend-build:
	cd frontend && npm run build

frontend-preview:
	cd frontend && npm run preview

frontend-install:
	cd frontend && npm install

frontend-lint:
	cd frontend && npm run lint

frontend-clean:
	rm -rf frontend/node_modules frontend/.vite frontend/dist

# =====================
# Database Management
# =====================

alembic-init:
	@echo "Initializing Alembic for database migrations."
	$(POETRY) run alembic init alembic

alembic-revision:
	@echo "Generating a new Alembic migration revision."
	$(POETRY) run alembic revision --autogenerate -m "add comment_summary to RedditPost and remove CommentSummary table"

alembic-upgrade:
	@echo "Upgrading the database to the latest migration."
	$(POETRY) run alembic upgrade head

alembic-downgrade:
	@echo "Downgrading the database to the previous migration."
	$(POETRY) run alembic downgrade -1 

check-db:
	@echo "Checking database contents..."
	$(POETRY) run python3 -m scripts.check_db

check-pipeline-db:
	@echo "Checking pipeline database status..."
	$(POETRY) run python3 -m scripts.check_pipeline_db

get-last-run:
	@echo "Getting last pipeline run details..."
	$(POETRY) run python3 -m scripts.get_last_run

backup-db:
	@echo "💾 Creating database backup..."
	@./scripts/backup-restore.sh backup-db

restore-db:
	@echo "💾 Restoring database..."
	@if [ -z "$(DB)" ]; then \
		echo "❌ No database file specified. Usage: make restore-db DB=filename.db"; \
		echo ""; \
		echo "Available database backups:"; \
		./scripts/backup-restore.sh restore-db; \
		exit 1; \
	fi
	@./scripts/backup-restore.sh restore-db $(DB)

backup-list:
	@echo "💾 Listing available backups..."
	@./scripts/backup-restore.sh list

# DANGEROUS: Only use these if you want to clear all data in the main database!
reset-db:
	@echo "WARNING: This will delete all data in the database!"
	@read -p "Are you sure? Type 'yes' to confirm: " confirm; \
	if [ "$$confirm" = "yes" ]; then \
		rm -f data/zazzle_pipeline.db; \
		echo "Database reset. Run 'make alembic-upgrade' to recreate tables."; \
	else \
		echo "Database reset cancelled."; \
	fi

# Alias for reset-db
fresh-db: reset-db

# =====================
# Pipeline Management
# =====================

run-pipeline-debug:
	@echo "Running pipeline with debug logging..."
	source .env && $(POETRY) run python -m app.main --mode full --model "$(MODEL)" $(if $(SUBREDDIT),--subreddit $(SUBREDDIT),)

run-pipeline-dry-run:
	@echo "Running pipeline in dry-run mode (no products created)..."
	source .env && $(POETRY) run python -m app.main --mode full --model "$(MODEL)" $(if $(SUBREDDIT),--subreddit $(SUBREDDIT),)

run-pipeline-single:
	@echo "Running pipeline for single product..."
	source .env && $(POETRY) run python -m app.main --mode full --model "$(MODEL)" $(if $(SUBREDDIT),--subreddit $(SUBREDDIT),)

run-pipeline-batch:
	@echo "Running pipeline for batch processing..."
	source .env && $(POETRY) run python -m app.main --mode full --model "$(MODEL)" $(if $(SUBREDDIT),--subreddit $(SUBREDDIT),)

run-pipeline:
	@echo "🚀 Running pipeline manually..."
	@docker-compose exec -T pipeline python app/main.py --mode full

monitor-pipeline:
	@echo "Starting pipeline monitor..."
	$(POETRY) run python3 -m scripts.pipeline_monitor

# =====================
# Logging & Debugging
# =====================

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

show-logs:
	@echo "📋 Showing logs for all services..."
	@docker-compose logs -f

show-logs-api:
	@echo "📋 Showing API logs..."
	@docker-compose logs -f api

show-logs-pipeline:
	@echo "📋 Showing pipeline logs..."
	@docker-compose logs -f pipeline

show-logs-frontend:
	@echo "📋 Showing frontend logs..."
	@docker-compose logs -f frontend

# =====================
# Testing & Development
# =====================

test-interaction-agent:
	@echo "Testing Reddit interaction agent..."
	$(POETRY) run python test_interaction_agent.py

create-test-db:
	@echo "Creating test database with sample data..."
	$(POETRY) run python3 scripts/create_test_db.py

scrape:
	$(POETRY) run python -m app.product_scraper 

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
	@if [ -f "data/zazzle_pipeline.db" ]; then \
		echo "✅ Database: EXISTS (data/zazzle_pipeline.db)"; \
		ls -lh data/zazzle_pipeline.db; \
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

health-check:
	@echo "🏥 Running essential health check..."
	@./scripts/health-monitor.sh --quick

health-logs:
	@echo "🏥 Running health check with logs..."
	@./scripts/health-monitor.sh --logs

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

# =====================
# Environment Setup
# =====================

setup-prod:
	@echo "🔧 Setting up production environment..."
	@./scripts/setup-environment.sh --production

setup-dev:
	@echo "🔧 Setting up development environment..."
	@./scripts/setup-environment.sh

setup-quick:
	@echo "🔧 Quick environment setup (skipping API tests)..."
	@./scripts/setup-environment.sh --skip-tests

# =====================
# Deployment Commands
# =====================

deploy:
	@echo "🚀 Deploying Zazzle Agent from scratch..."
	@if [ ! -f .env ]; then \
		echo "❌ .env file not found. Please create one with required environment variables."; \
		echo "See .env.example for required variables."; \
		echo ""; \
		echo "Run this first to set up your environment:"; \
		echo "  make setup-prod"; \
		exit 1; \
	fi
	@./deploy.sh

deploy-clean:
	@echo "🚀 Deploying Zazzle Agent with clean images..."
	@if [ ! -f .env ]; then \
		echo "❌ .env file not found. Please create one with required environment variables."; \
		echo "See .env.example for required variables."; \
		echo ""; \
		echo "Run this first to set up your environment:"; \
		echo "  make setup-prod"; \
		exit 1; \
	fi
	@./deploy.sh --clean-images

deploy-quick:
	@echo "🚀 Quick deployment (skipping initial pipeline)..."
	@if [ ! -f .env ]; then \
		echo "❌ .env file not found. Please create one with required environment variables."; \
		echo "See .env.example for required variables."; \
		echo ""; \
		echo "Run this first to set up your environment:"; \
		echo "  make setup-prod"; \
		exit 1; \
	fi
	@./deploy.sh --skip-pipeline

validate-deployment:
	@echo "🔍 Validating deployment..."
	@echo "Checking API health..."
	@curl -f -s http://localhost:8000/health > /dev/null && echo "✅ API is healthy" || echo "❌ API health check failed"
	@echo "Checking frontend..."
	@curl -f -s http://localhost:5173 > /dev/null && echo "✅ Frontend is accessible" || echo "❌ Frontend check failed"
	@echo "Checking database..."
	@docker-compose exec -T database sqlite3 /app/data/zazzle_pipeline.db "SELECT COUNT(*) FROM reddit_posts;" 2>/dev/null && echo "✅ Database is accessible" || echo "❌ Database check failed"

deployment-status:
	@echo "📊 Deployment Status"
	@echo "==================="
	@docker-compose ps
	@echo ""
	@echo "🔗 Service URLs:"
	@echo "  • Frontend: http://localhost:5173"
	@echo "  • API: http://localhost:8000"
	@echo "  • API Docs: http://localhost:8000/docs"
	@echo ""
	@echo "📋 Recent logs:"
	@docker-compose logs --tail=10

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
	@echo "✅ Environment cleaned (DB is preserved)"
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
	@echo "🎉 Fresh environment setup complete! (DB is preserved)"
	@echo "=================================================="
	@echo "📊 Services Status:"
	@echo "   • API Server: http://localhost:8000"
	@echo "   • Frontend: http://localhost:5173"
	@echo "   • Database: data/zazzle_pipeline.db (preserved)"
	@echo ""
	@echo "🔧 Available commands:"
	@echo "   • make run-full - Run the complete pipeline"
	@echo "   • make test - Run tests"
	@echo "   • make stop-api - Stop API server"
	@echo "   • make frontend-dev - Start frontend dev server"
	@echo "   • make test-interaction-agent - Test interaction agent"
	@echo "   • make reset-db - DANGEROUS: Delete all data in the main database"
	@echo ""
	@echo "📝 Next steps:"
	@echo "   1. Open http://localhost:5173 in your browser"
	@echo "   2. Run 'make run-full' to generate a new product"
	@echo "   3. Use the interaction agent to engage with products"
	@echo ""

# =====================
# Quick Development Setup
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
# Maintenance
# =====================

cleanup:
	@echo "🧹 Quick cleanup..."
	@echo "Cleaning Docker resources..."
	@docker system prune -f
	@echo "✅ Cleanup completed"

restart:
	@echo "🔄 Restarting all services..."
	@docker-compose restart
	@echo "✅ Services restarted"

# =====================
# Dependencies
# =====================

export-requirements:
	poetry run pip freeze > requirements.txt

# =====================
# Subreddit Tier Management
# =====================

create-subreddit-tiers:
	@if [ -z "$(SUBREDDIT)" ]; then \
		echo "Error: Please specify SUBREDDIT"; \
		echo "Usage: make create-subreddit-tiers SUBREDDIT=funny"; \
		exit 1; \
	fi
	@echo "Creating subreddit tiers for $(SUBREDDIT)..."
	$(POETRY) run python -c "from app.db.database import SessionLocal; from app.subreddit_tier_service import SubredditTierService; from decimal import Decimal; session = SessionLocal(); service = SubredditTierService(session); tiers = service.create_subreddit_tiers('$(SUBREDDIT)', [{'level': 1, 'min_total_donation': Decimal('100')}, {'level': 2, 'min_total_donation': Decimal('500')}, {'level': 3, 'min_total_donation': Decimal('1000')}]); print(f'Created {len(tiers)} tiers for $(SUBREDDIT)'); session.close()"

create-fundraising-goal:
	@if [ -z "$(SUBREDDIT)" ] || [ -z "$(GOAL_AMOUNT)" ]; then \
		echo "Error: Please specify SUBREDDIT and GOAL_AMOUNT"; \
		echo "Usage: make create-fundraising-goal SUBREDDIT=funny GOAL_AMOUNT=500"; \
		exit 1; \
	fi
	@echo "Creating fundraising goal for $(SUBREDDIT): $$(GOAL_AMOUNT)..."
	$(POETRY) run python -c "from app.db.database import SessionLocal; from app.subreddit_tier_service import SubredditTierService; from decimal import Decimal; session = SessionLocal(); service = SubredditTierService(session); goal = service.create_fundraising_goal('$(SUBREDDIT)', Decimal('$(GOAL_AMOUNT)')); print(f'Created goal {goal.id} for $(SUBREDDIT): $$(GOAL_AMOUNT)'); session.close()"

show-subreddit-stats:
	@if [ -z "$(SUBREDDIT)" ]; then \
		echo "Error: Please specify SUBREDDIT"; \
		echo "Usage: make show-subreddit-stats SUBREDDIT=funny"; \
		exit 1; \
	fi
	@echo "Showing stats for $(SUBREDDIT)..."
	$(POETRY) run python -c "from app.db.database import SessionLocal; from app.subreddit_tier_service import SubredditTierService; session = SessionLocal(); service = SubredditTierService(session); stats = service.get_subreddit_stats('$(SUBREDDIT)'); import json; print(json.dumps(stats, indent=2)); session.close()"

check-subreddit-tiers:
	@if [ -z "$(SUBREDDIT)" ]; then \
		echo "Error: Please specify SUBREDDIT"; \
		echo "Usage: make check-subreddit-tiers SUBREDDIT=funny"; \
		exit 1; \
	fi
	@echo "Checking tiers for $(SUBREDDIT)..."
	$(POETRY) run python -c "from app.db.database import SessionLocal; from app.subreddit_tier_service import SubredditTierService; session = SessionLocal(); service = SubredditTierService(session); completed = service.check_and_update_tiers('$(SUBREDDIT)'); print(f'Completed {len(completed)} tiers for $(SUBREDDIT)'); session.close()"

add-subreddit-task:
	@if [ -z "$(SUBREDDIT)" ]; then \
		echo "Error: Please specify SUBREDDIT"; \
		echo "Usage: make add-subreddit-task SUBREDDIT=funny"; \
		exit 1; \
	fi
	@echo "Adding subreddit task to queue..."
	$(POETRY) run python -c "from app.db.database import SessionLocal; from app.task_queue import TaskQueue; session = SessionLocal(); queue = TaskQueue(session); task = queue.add_subreddit_task('$(SUBREDDIT)'); print(f'Added subreddit task {task.id} for r/$(SUBREDDIT)'); session.close()"

%::
	@: 