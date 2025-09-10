# Clouvel 🤖

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-19-blue.svg)](https://react.dev/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.6-blue.svg)](https://www.typescriptlang.org/)

**AI-Powered Product Generation Platform**

Clouvel is an intelligent automation platform that transforms trending Reddit content into custom products through AI-powered analysis and generation. Users can commission unique products from viral posts, with real-time progress tracking and automated creation through Zazzle's print-on-demand service.

🌐 **Live Demo**: [clouvel.ai](https://clouvel.ai)

## ✨ Features

### 🤖 AI-Powered Product Generation
- **Reddit Content Discovery**: Scans trending posts across 50+ subreddits
- **GPT Content Analysis**: Analyzes posts to generate creative product ideas
- **DALL-E 3 Image Generation**: Creates custom artwork with HD quality options
- **Automated Product Creation**: Seamlessly integrates with Zazzle's print-on-demand platform

### 💰 Commission System
- **Stripe Payment Processing**: Secure checkout with multiple payment methods
- **Tiered Donations**: Bronze ($5) to Diamond ($100) with quality upgrades
- **Real-Time Progress**: WebSocket updates during commission processing
- **Automatic Refunds**: Built-in refund system for failed commissions

### 🏗️ Multi-Agent Architecture
- **Reddit Agent**: Core product generation engine
- **Community Agent**: Manages r/clouvel community with AI personality
- **Promoter Agent**: Discovers and promotes opportunities across subreddits

### 📊 Real-Time Features
- **Live Progress Tracking**: Step-by-step commission updates
- **WebSocket Communication**: Real-time frontend updates
- **Task Dashboard**: Monitor all running processes
- **Health Monitoring**: Comprehensive system status checks

## 🚀 Quick Start

### Prerequisites

- Python 3.12 with Poetry
- Node.js 18+ with npm
- Redis server
- Required API keys:
  - OpenAI API key
  - Reddit API credentials
  - Stripe account
  - Zazzle affiliate ID

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/zazzle-agent.git
cd zazzle-agent

# Install dependencies
make install-deps

# Set up environment variables
cp env.example .env
# Edit .env with your API keys

# Initialize database
make setup-fresh-db

# Start development servers
make run-api          # Backend (port 8000)
make frontend-dev     # Frontend (port 5173)
```

### Docker Deployment

```bash
# Deploy complete application
make deploy

# Check system health
make health-check

# View logs
make show-logs
```

## 🏗️ Architecture

### Core Components

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   React Frontend │    │   FastAPI API   │    │   AI Agents     │
│   (TypeScript)   │◄──►│   (Python)      │◄──►│   (Multi-Agent) │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                        │                        │
         │                        │                        │
         ▼                        ▼                        ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   WebSocket     │    │   SQLite/       │    │   Redis Pub/Sub │
│   Real-time     │    │   PostgreSQL    │    │   Messaging     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### Technology Stack

#### Backend
- **FastAPI** - Modern async web framework
- **SQLAlchemy 2.0** - ORM with SQLite/PostgreSQL support
- **Redis** - Caching and pub/sub messaging
- **WebSockets** - Real-time communication
- **Pydantic** - Data validation and serialization

#### Frontend
- **React 19** - Modern UI framework
- **TypeScript** - Type-safe JavaScript
- **Vite** - Fast build tool
- **Tailwind CSS 4** - Utility-first styling
- **React Router** - Client-side routing

#### AI/ML Services
- **OpenAI API** - GPT models for content analysis
- **DALL-E 3** - AI image generation
- **Reddit API (PRAW)** - Content discovery
- **Stripe API** - Payment processing
- **Zazzle API** - Product creation

## 🔧 Development

### Essential Commands

```bash
# Development
make run-api              # Start FastAPI server
make frontend-dev         # Start React dev server
make setup-fresh-db       # Initialize clean database

# Testing
make test                 # Run test suite with coverage
make test-commission-flow # End-to-end commission testing
make test-pattern <path>  # Run specific tests

# Code Quality
make format              # Format code with black/isort
make lint                # Lint with flake8
make type-check          # Type checking with mypy

# Agents
make run-promoter-agent  # Start promoter agent
make run-community-agent # Start community agent

# Database
make alembic-upgrade     # Apply migrations
make backup-db           # Create database backup
make check-db            # Inspect database contents
```

### Project Structure

```
zazzle-agent/
├── app/                          # Backend application
│   ├── agents/                   # AI agents
│   │   ├── reddit_agent.py       # Core product generation
│   │   ├── clouvel_community_agent.py # Community management
│   │   └── clouvel_promoter_agent.py  # Promotion engine
│   ├── api.py                    # FastAPI routes and WebSocket
│   ├── commission_worker.py      # Commission processing
│   ├── task_manager.py           # Task orchestration
│   ├── websocket_manager.py      # Real-time updates
│   ├── db/                       # Database layer
│   │   ├── models.py             # SQLAlchemy models
│   │   ├── mappers.py            # Data transformation
│   │   └── database.py           # Connection management
│   └── services/                 # Business services
│       ├── stripe_service.py     # Payment processing
│       └── commission_validator.py # Validation logic
├── frontend/                     # React application
│   ├── src/
│   │   ├── components/           # React components
│   │   │   ├── ProductGrid/      # Product display
│   │   │   ├── Fundraising/      # Donation system
│   │   │   └── common/           # Shared components
│   │   ├── App.tsx              # Main application
│   │   └── index.tsx            # Entry point
│   ├── package.json             # Dependencies
│   └── tailwind.config.js       # Styling configuration
├── tests/                       # Test suite
├── alembic/                     # Database migrations
├── docker-compose.yml           # Container orchestration
├── Makefile                     # Development commands
└── pyproject.toml               # Python dependencies
```

## 🧪 Testing

The project includes comprehensive testing coverage:

```bash
# Run all tests
make test

# Run specific test categories
make test-pattern tests/test_api.py
make test-pattern tests/test_agents/
make test-pattern tests/test_commission_worker.py

# End-to-end commission testing
make test-commission-flow SUBREDDIT=golf AMOUNT=25
```

### Test Coverage
- **API Endpoints**: Request/response validation
- **Agent Behavior**: Reddit discovery and product generation
- **Commission Workflow**: Payment to product delivery
- **Database Operations**: CRUD operations and migrations
- **WebSocket Communication**: Real-time updates
- **Error Handling**: Failure scenarios and recovery

## 📊 API Reference

### Core Endpoints

```http
# Products
GET /api/generated_products           # List all products
GET /api/generated_products/{id}      # Get specific product

# Commissions
POST /api/donations/create-checkout-session  # Create payment session
POST /api/commissions/validate               # Validate commission request

# Real-time
WS /ws                               # WebSocket connection

# System
GET /health                          # Health check
GET /api/status                      # System status
```

### Commission Request

```json
{
  "amount_usd": "25.00",
  "subreddit": "hiking",
  "donation_type": "commission",
  "post_id": "reddit_post_id",
  "customer_email": "user@example.com",
  "customer_name": "John Doe",
  "reddit_username": "johnhiker",
  "is_anonymous": false,
  "commission_message": "Create a beautiful hiking-themed product!"
}
```

## 🚀 Deployment

### Environment Variables

```bash
# Required
OPENAI_API_KEY=your_openai_api_key
REDDIT_CLIENT_ID=your_reddit_client_id
REDDIT_CLIENT_SECRET=your_reddit_client_secret
REDDIT_USER_AGENT=your_reddit_user_agent
ZAZZLE_AFFILIATE_ID=your_zazzle_affiliate_id
STRIPE_SECRET_KEY=your_stripe_secret_key
STRIPE_PUBLISHABLE_KEY=your_stripe_publishable_key
STRIPE_WEBHOOK_SECRET=your_stripe_webhook_secret
REDIS_URL=redis://localhost:6379

# Optional
OPENAI_IDEA_MODEL=gpt-4o-mini
DATABASE_URL=sqlite:///./data/zazzle_pipeline.db
```

### Docker Deployment

```bash
# Deploy with Docker Compose
make deploy

# Monitor health
make health-check

# View logs
make show-logs

# Database backup
make backup-db
```

### Railway Deployment

The application is production-ready for Railway deployment:

```bash
# Deploy to Railway
railway login
railway init
railway up
```

## 🤝 Contributing

We welcome contributions! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests (`make test`)
5. Format code (`make format`)
6. Commit changes (`git commit -m 'Add amazing feature'`)
7. Push to branch (`git push origin feature/amazing-feature`)
8. Open a Pull Request

### Code Style

- Follow PEP 8 for Python code
- Use TypeScript for all frontend code
- Write comprehensive tests for new features
- Use type hints throughout Python code
- Follow existing patterns and conventions

## 📈 Monitoring

### Health Checks

```bash
# System health
make health-check

# Deployment status
make deployment-status

# Database health
make check-db

# View logs
make show-logs
```

### Performance Monitoring

- **OpenAI Usage Tracking**: Monitor API costs and usage
- **Redis Performance**: Track pub/sub message throughput
- **Database Metrics**: Query performance and connection health
- **WebSocket Connections**: Active connection monitoring

## 🔒 Security

- **API Key Security**: All sensitive keys stored in environment variables
- **Stripe Integration**: PCI-compliant payment processing
- **CORS Configuration**: Proper cross-origin resource sharing
- **Input Validation**: Comprehensive request validation with Pydantic
- **SQL Injection Prevention**: Parameterized queries with SQLAlchemy

## 📄 License

This project is licensed under the MIT License.

## 🙏 Acknowledgments

- **OpenAI** for GPT and DALL-E APIs
- **Reddit** for their comprehensive API
- **Stripe** for secure payment processing
- **Zazzle** for print-on-demand services
- **FastAPI** for the excellent web framework
- **React** team for the modern UI framework

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/yourusername/zazzle-agent/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/zazzle-agent/discussions)
- **Documentation**: [Wiki](https://github.com/yourusername/zazzle-agent/wiki)

---

**Transform Reddit trends into custom products with AI-powered automation.**

Built with ❤️ by the Clouvel team.

## 🐛 Defect Recaps

### Database Connection Pool Exhaustion and Performance Issues
**Date:** January 2025

#### Summary
A critical performance issue was discovered where the product grid would load initially but subsequent navigation to the fundraising page would fail or take excessive time to load. Returning to the product grid after visiting the fundraising page also resulted in significant delays, indicating backend resource contention.

#### Root Cause Analysis
The issue stemmed from multiple interconnected problems in the data layer:

1. **N+1 Query Pattern**: The `/api/generated_products/{id}/donations` endpoint was making individual database queries for each product when loading donation data, causing exponential growth in database connections as the number of products increased.

2. **Connection Pool Exhaustion**: The default SQLite connection pool settings (5 connections with 10 overflow) were insufficient for handling the burst of concurrent requests from the frontend, especially when loading donation data for multiple products simultaneously.

3. **Frontend Request Pattern**: The React frontend was making individual API calls for each product's donation data as components mounted, creating a thundering herd effect that overwhelmed the backend's connection pool.

4. **Session Management Issues**: Improper session handling in SQLAlchemy was causing connections to remain open longer than necessary, further exacerbating the pool exhaustion.

#### Solution Path

1. **Initial Investigation** (commits bd4b0e9-03260b1): Identified N+1 query issue in the fundraising page and attempted to optimize individual queries with eager loading.

2. **Connection Pool Configuration** (commit 52ee6b6): Added configurable database connection pool settings, increasing pool size to 20 with 40 overflow connections.

3. **Rate Limiting Attempts** (commits ce4d98b-f5564af): Implemented aggressive rate limiting and throttling on the frontend to reduce concurrent API calls, but this only partially mitigated the issue.

4. **Caching and Error Handling** (commits 9f78e83-b61974d): Added response caching and improved error handling to prevent connection failures from cascading.

5. **Frontend State Management** (commits ec114b4-347012a): Attempted to prevent duplicate API calls by managing loaded state across components, with mixed success.

6. **Final Solution - Bulk Endpoint** (commits ef08177-f09222a): Implemented a single `/api/generated_products/bulk_donations` endpoint that fetches all donation data in one optimized query, eliminating the N+1 pattern entirely.

#### Final Implementation

The solution that was initially suggested but deferred was ultimately the correct approach:
- Created a bulk donations endpoint that returns all product donation data in a single, optimized database query
- Modified the frontend to make one bulk request instead of individual requests per product
- Removed complex state management and rate limiting code that was no longer necessary
- Result: Page load times reduced from 10-30 seconds to under 1 second

#### Lessons Learned

1. **API Design**: When dealing with list views that require related data, always prefer bulk endpoints over individual resource endpoints to prevent N+1 patterns.

2. **Connection Pool Sizing**: Default connection pool settings are often insufficient for production workloads. Monitor and adjust based on actual usage patterns.

3. **Frontend-Backend Contract**: The API should guide the frontend toward efficient data access patterns. If the frontend needs to make many individual requests, consider if the API design could be improved.

4. **Performance Testing**: Load testing with realistic data volumes would have caught this issue earlier in development.

5. **Simple Solutions First**: The bulk endpoint approach was simpler and more effective than trying to optimize the existing pattern with caching, rate limiting, and connection pool tuning.