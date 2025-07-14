# Clouvel 🤖

> **AI-Powered Product Generation from Reddit Trends**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com/)
[![Railway](https://img.shields.io/badge/Railway-Deployed-purple.svg)](https://railway.app/)

Clouvel is an intelligent automation platform that discovers trending content on Reddit and generates commissioned products through AI-powered content analysis and image generation. Users can commission custom products from trending Reddit posts, supporting creators through our donation system.

## ✨ Features

- **💡 Commission-Based Product Generation**: Users can commission custom products from trending Reddit posts
- **🤖 AI-Powered Content Analysis**: Uses GPT models to analyze Reddit posts and generate product ideas
- **🎨 Automated Image Generation**: Creates unique product images using DALL-E 3
- **🛍️ Zazzle Integration**: Automatically creates products with affiliate links
- **💳 Stripe Payment Processing**: Secure donation and commission system
- **📊 Real-Time Progress Updates**: WebSocket-powered live updates during product creation
- **📱 Modern Web Interface**: React TypeScript frontend with product grid and commission tracking
- **🚂 Railway Deployment**: Cloud-native deployment on Railway platform
- **📈 Usage Tracking**: Comprehensive OpenAI API usage monitoring and cost management
- **🛡️ Robust Task Management**: Queue-based processing with error handling and retries

## 🚀 Quick Start

### Live Application

Visit **[clouvel.ai](https://clouvel.ai)** to use the application immediately - no setup required!

### Local Development

#### Prerequisites

- Python 3.12 with Poetry
- Node.js 18+ with npm
- OpenAI API key
- Reddit API credentials  
- Stripe account (for commission features)

#### 1. Clone the Repository

```bash
git clone https://github.com/sctennis77/zazzle-agent.git
cd zazzle-agent
```

#### 2. Set Up Environment

```bash
# Copy environment template
cp env.example .env

# Edit with your API keys
nano .env
```

Required environment variables:
```env
OPENAI_API_KEY=your_openai_api_key
REDDIT_CLIENT_ID=your_reddit_client_id
REDDIT_CLIENT_SECRET=your_reddit_client_secret
REDDIT_USER_AGENT=your_reddit_user_agent
ZAZZLE_AFFILIATE_ID=your_zazzle_affiliate_id
STRIPE_SECRET_KEY=your_stripe_secret_key
STRIPE_PUBLISHABLE_KEY=your_stripe_publishable_key
STRIPE_WEBHOOK_SECRET=your_stripe_webhook_secret
```

#### 3. Install Dependencies

```bash
# Install Python dependencies
make install-deps

# Install frontend dependencies  
cd frontend && npm install && cd ..
```

#### 4. Start Development Servers

```bash
# Start API server (port 8000)
make run-api

# In another terminal, start frontend (port 5173)
make frontend-dev
```

#### 5. Access the Application

- **Frontend**: http://localhost:5173
- **API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs

## 🏗️ Architecture

Clouvel is built as a modern microservices architecture deployed on Railway:

### Core Services

- **API Service** (`app/api.py`): FastAPI backend with commission endpoints, real-time WebSocket updates, and Stripe integration
- **Commission Worker** (`app/commission_worker.py`): Processes commissioned product generation tasks
- **Task Manager** (`app/task_manager.py`): Queue-based task processing with retry logic and progress tracking
- **Frontend** (`frontend/`): React TypeScript interface with product grid, commission modals, and real-time progress
- **Database**: PostgreSQL with SQLAlchemy ORM and Alembic migrations (deployed on Railway)

### Key Components

- **Reddit Agent** (`app/agents/reddit_agent.py`): Discovers and analyzes trending Reddit content for commissioned products
- **Content Generator** (`app/content_generator.py`): Uses GPT models to generate product ideas and descriptions
- **Image Generator** (`app/async_image_generator.py`): Creates product images using DALL-E 3 with async processing
- **Zazzle Product Designer** (`app/zazzle_product_designer.py`): Integrates with Zazzle API for product creation
- **Stripe Service** (`app/services/stripe_service.py`): Handles secure payment processing for commissions
- **WebSocket Manager** (`app/websocket_manager.py`): Real-time progress updates to frontend clients

## 📊 API Endpoints

### Products & Commissions
- `GET /api/generated_products` - List all generated products with commission details
- `GET /api/generated_products/{product_id}` - Get specific product details
- `POST /api/donations/create-checkout-session` - Create commission payment session
- `POST /api/commissions/validate` - Validate commission request before payment

### Real-Time Updates
- `WS /ws` - WebSocket connection for real-time commission progress updates

### Health & Status  
- `GET /health` - Service health check
- `GET /api/status` - System status and task queue metrics

### Task Management
- `GET /api/tasks` - List current tasks in queue
- `POST /api/tasks/commission` - Create new commission task

## 🛠️ Development

### Local Development Setup

```bash
# Install Python dependencies
make install-deps

# Install frontend dependencies
cd frontend && npm install && cd ..

# Setup fresh database with migrations
make setup-fresh-db

# Start development servers
make run-api          # API server (port 8000)
make frontend-dev     # Frontend dev server (port 5173)
```

### Testing

```bash
# Run all tests with coverage
make test

# Run specific test files
make test-pattern tests/test_api.py
make test-pattern tests/test_reddit_agent.py

# Test commission workflow end-to-end
make test-commission-flow SUBREDDIT=golf AMOUNT=25
```

### Code Quality

```bash
# Format code with black and isort
make format

# Lint code with flake8
make lint

# Type checking with mypy
make type-check
```

## 📦 Deployment

### Railway Deployment (Production)

Clouvel is deployed on Railway with automatic GitHub integration:

```bash
# Deploy using Railway CLI
./scripts/deploy-railway.sh

# Monitor deployment
railway logs --service api
railway logs --service frontend

# Check service status
railway status
```

**Live Application**: [clouvel.ai](https://clouvel.ai)

### Local Docker Deployment

```bash
# Start all services with Docker Compose
make deploy

# Check deployment status
make deployment-status

# View logs
make show-logs

# Health check
make health-check
```

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `OPENAI_API_KEY` | OpenAI API key for GPT and DALL-E | Yes |
| `REDDIT_CLIENT_ID` | Reddit API client ID | Yes |
| `REDDIT_CLIENT_SECRET` | Reddit API client secret | Yes |
| `REDDIT_USER_AGENT` | Reddit API user agent | Yes |
| `ZAZZLE_AFFILIATE_ID` | Zazzle affiliate ID | Yes |
| `STRIPE_SECRET_KEY` | Stripe secret key for commission processing | Yes |
| `STRIPE_PUBLISHABLE_KEY` | Stripe publishable key for frontend | Yes |
| `STRIPE_WEBHOOK_SECRET` | Stripe webhook secret for payment events | Yes |
| `DATABASE_URL` | PostgreSQL connection string (Railway provides) | Yes |
| `REDIS_URL` | Redis connection string (Railway provides) | Yes |
| `OPENAI_IDEA_MODEL` | GPT model for idea generation (default: gpt-4o-mini) | No |

## 📈 Monitoring & Management

### Health Monitoring

```bash
# Essential health check
make health-check

# Deployment status check
make deployment-status

# View all service logs
make show-logs

# View specific service logs
make show-logs-api
```

### Database Management

```bash
# Create database backup
make backup-db

# Restore from backup
make restore-db DB=backup_filename.db

# List available backups
make backup-list

# Check database contents
make check-db
```

### Commission System Management

```bash
# Test commission workflow
make test-commission-flow SUBREDDIT=golf AMOUNT=25

# View task queue status
make show-task-queue

# Clean up stuck tasks
make cleanup-stuck-tasks
```

## 🔧 Configuration

### Commission System

Clouvel operates on a commission-based model where users pay to generate products from trending Reddit posts:

- **Commission Tiers**: $25 (standard), $50 (premium), $100 (deluxe)
- **Processing**: Queue-based with real-time progress updates
- **Payment**: Secure Stripe checkout with webhook confirmation
- **Products**: Automatically posted to relevant subreddits with affiliate links

### Subreddit Support

Currently supports trending posts from popular subreddits:
- golf, hiking, baking, interiordesign, digitalart
- Posts are filtered by engagement and content quality
- Custom subreddit requests can be added via configuration

### Task Queue Configuration

- **Retry Logic**: 3 attempts with exponential backoff
- **Rate Limiting**: Respects OpenAI and Reddit API limits  
- **Progress Tracking**: Real-time WebSocket updates to frontend
- **Error Handling**: Comprehensive logging and failure recovery

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guidelines](CONTRIBUTING.md) for details.

### Development Workflow

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Code Style

- Follow PEP 8 for Python code
- Use type hints throughout
- Write comprehensive tests
- Update documentation for new features

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **OpenAI** for GPT and DALL-E APIs
- **Reddit** for their API
- **Zazzle** for their affiliate program
- **FastAPI** for the excellent web framework
- **React** for the frontend framework

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/yourusername/zazzle-agent/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/zazzle-agent/discussions)
- **Documentation**: [Wiki](https://github.com/yourusername/zazzle-agent/wiki)

## 🗺️ Roadmap

- [ ] Support for additional e-commerce platforms
- [ ] Advanced product customization options
- [ ] Machine learning for trend prediction
- [ ] Social media integration
- [ ] Advanced analytics dashboard
- [ ] Multi-language support

## 💳 Donation System

The Zazzle Agent includes a fully integrated donation system powered by Stripe:

### Features
- ✅ Secure payment processing with Stripe
- ✅ Anonymous donation option
- ✅ Custom donation messages
- ✅ Real-time payment status updates
- ✅ Database tracking of all donations
- ✅ Webhook integration for payment events

### Current State
- Basic donation modal implemented
- Stripe payment processing working
- Database storage for donations

### Next Steps: UI/UX Improvements

#### 1. Enhanced Payment Modal
**Planned Enhancements:**
- Modern, branded design matching the app theme
- Multiple payment method support (cards, Apple Pay, Google Pay)
- Real-time payment status indicators
- Better error handling and user feedback
- Mobile-optimized responsive design

#### 2. Fundraising Goal Bar
**Features to Add:**
- Visual progress bar showing donation goal progress
- Current total raised vs. target amount
- Recent donors list (with privacy controls)
- Goal milestones and achievements
- Social sharing capabilities

#### 3. Donation Analytics Dashboard
- Real-time donation tracking
- Donor insights and trends
- Goal progress analytics
- Export capabilities for accounting

---

**Made with ❤️ by the Clouvel Team**

*Transform Reddit trends into commissioned products with AI-powered automation.*

## How Clouvel Works

### Commission Workflow

1. **Browse Products**: Users view the product grid showing generated items from trending Reddit posts
2. **Commission Request**: Users select a product and choose a commission tier ($25, $50, or $100)
3. **Secure Payment**: Stripe checkout processes the payment securely
4. **Task Queue**: Commission is added to the processing queue with real-time progress tracking
5. **AI Generation**: Reddit content is analyzed, product ideas generated, and images created using DALL-E 3
6. **Product Creation**: Zazzle products are automatically created with affiliate links
7. **Completion**: Users receive their commissioned product with purchase links

### Technical Implementation

- **Task-Based Processing**: All product generation uses a queue-based system with retry logic
- **Real-Time Updates**: WebSocket connections provide live progress updates during commission processing  
- **Secure Payments**: Stripe handles all payment processing with webhook confirmation
- **AI Integration**: OpenAI GPT models analyze Reddit content and DALL-E 3 generates product images
- **Automated Publishing**: Products are automatically posted to relevant subreddits with affiliate tracking

## Commission API Reference

### Create Commission Checkout Session

Create a commission payment session for an existing Reddit post:

```
POST /api/donations/create-checkout-session
```

### Request Body Example
```json
{
  "amount_usd": "25.00",
  "subreddit": "hiking", 
  "donation_type": "commission",
  "post_id": "<REDDIT_POST_ID>",
  "customer_email": "your@email.com",
  "customer_name": "Your Name",
  "reddit_username": "your_reddit_username",
  "is_anonymous": false,
  "commission_message": "Create a beautiful product from this hiking post!"
}
```

### Commission Tiers
- `$25` - Standard commission (basic product generation)
- `$50` - Premium commission (enhanced quality and options)
- `$100` - Deluxe commission (premium features and priority processing)

### Response
Returns a Stripe Checkout session URL for secure payment processing.

---

## Recent Updates

### Railway Deployment (2025)
- ✅ Successfully deployed on Railway platform at [clouvel.ai](https://clouvel.ai)
- ✅ PostgreSQL and Redis integration with Railway plugins
- ✅ Automatic GitHub deployment pipeline
- ✅ Custom domain configuration with SSL
- ✅ Commission workflow fully operational in production

### Commission System Enhancements
- ✅ Real-time progress tracking via WebSocket connections
- ✅ Queue-based task processing with retry logic
- ✅ Secure Stripe payment integration with webhook confirmation
- ✅ Product detail modals with commission and sponsor information
- ✅ Mobile-responsive design for commission flow
