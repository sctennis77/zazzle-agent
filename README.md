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
git clone https://github.com/yourusername/clouvel.git
cd clouvel

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
clouvel/
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

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **OpenAI** for GPT and DALL-E APIs
- **Reddit** for their comprehensive API
- **Stripe** for secure payment processing
- **Zazzle** for print-on-demand services
- **FastAPI** for the excellent web framework
- **React** team for the modern UI framework

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/yourusername/clouvel/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/clouvel/discussions)
- **Documentation**: [Wiki](https://github.com/yourusername/clouvel/wiki)

---

**Transform Reddit trends into custom products with AI-powered automation.**

Built with ❤️ by the Clouvel team.