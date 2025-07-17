# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Essential Development Commands

### Testing & Quality
- `make test` - Run test suite with coverage
- `make test-pattern <test_path>` - Run specific test file/pattern
- `make format` - Format code with black and isort
- `make lint` - Lint code with flake8
- `make type-check` - Run mypy type checking

### Development Setup
- `make install-deps` - Install dependencies with Poetry
- `make setup-dev` - Setup development environment
- `make setup-fresh-db` - Create fresh database with migrations
- `make run-api` - Start FastAPI development server (port 8000)
- `make frontend-dev` - Start React frontend (port 5173)

### Production Deployment
- `make deploy` - Deploy complete application with Docker Compose
- `make health-check` - Essential health monitoring
- `make backup-db` - Create database backup
- `make show-logs` - View all service logs
- `make deployment-status` - Check deployment status

### Database Management
- `make alembic-upgrade` - Apply database migrations
- `make check-db` - Check database contents
- `make reset-db` - Reset database (DANGEROUS - deletes all data)

## Architecture Overview

### Core Services
- **API Service** (`app/api.py`): FastAPI backend with product endpoints, donation system, and WebSocket support
- **Reddit Agent** (`app/agents/reddit_agent.py`): Discovers trending Reddit content and generates product ideas
- **Commission Worker** (`app/commission_worker.py`): Processes commissioned product generation tasks
- **Task Manager** (`app/task_manager.py`): Manages async product generation pipeline
- **Frontend** (`frontend/`): React TypeScript application with product grid and donation modals

### Data Layer
- **Database**: SQLite with SQLAlchemy ORM and Alembic migrations
- **Models** (`app/db/models.py`): Core entities including ProductInfo, RedditPost, Donation, PipelineTask
- **Mappers** (`app/db/mappers.py`): Convert between domain models and database entities

### Key Integrations
- **OpenAI**: GPT for content analysis, DALL-E 3 for image generation
- **Reddit API**: PRAW client for post discovery and interaction
- **Stripe**: Payment processing for donations and commissions
- **Zazzle**: Product creation and affiliate link generation
- **WebSocket**: Real-time progress updates for frontend

### Product Generation Pipeline
1. **Discovery**: Reddit Agent finds trending posts matching criteria
2. **Analysis**: OpenAI analyzes post content and generates product ideas
3. **Creation**: DALL-E generates product images, Zazzle creates products
4. **Publishing**: Products published to subreddits with affiliate links
5. **Tracking**: Progress updates via WebSocket to frontend

### Commission-Based Architecture
The application uses a task-based commission system:
- **Commission Processing**: `TaskManager` → `CommissionWorker` → `RedditAgent._find_trending_post_for_task`
- **Real-time Updates**: WebSocket connections provide live progress tracking
- **Payment Integration**: Stripe checkout with webhook confirmation triggers task creation

## Development Practices

### Environment Variables
- Use `.env` file for local development (copy from `env.example`)
- Environment controls OpenAI model selection via `OPENAI_IDEA_MODEL`
- Minimize API costs by avoiding full pipeline runs during development

### Production Environment
- **Backend URL**: https://backend-api-production-a9e0.up.railway.app
- **Admin Secret**: [Ask user for admin secret when needed]

### Code Style
- Python 3.12 with Poetry dependency management
- FastAPI for API endpoints with Pydantic validation
- SQLAlchemy for database operations
- TypeScript React frontend with Tailwind CSS
- Follow existing patterns for new components

### Testing Strategy
- Comprehensive test suite covering agents, API, database, and integrations
- Mock external APIs (OpenAI, Reddit, Stripe) for unit tests
- End-to-end commission workflow testing with `make test-commission-flow`
- Database migration tests for schema changes

### Key Configuration Files
- `.cursorrules`: Development best practices and OpenAI model switching instructions
- `pyproject.toml`: Poetry dependencies and tool configuration
- `Makefile`: Comprehensive command reference for all operations
- `docker-compose.yml`: Multi-service containerized deployment

## AI Interaction Guidelines
- Only ask for permission to perform actions if it is absolutely necessary
- Manage context intelligently, including clearing it if no longer needed
- Compact context as appropriate to maintain efficiency