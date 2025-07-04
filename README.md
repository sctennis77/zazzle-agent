# Zazzle Agent 🤖

> **AI-Powered Product Generation from Reddit Trends**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com/)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)](https://www.docker.com/)

Zazzle Agent is an intelligent automation system that discovers trending content on Reddit and automatically generates unique products for sale on Zazzle. Using AI-powered content analysis and image generation, it creates market-ready products with affiliate links in minutes.

## ✨ Features

- **🤖 AI-Powered Content Analysis**: Uses GPT models to analyze Reddit posts and generate product ideas
- **🎨 Automated Image Generation**: Creates unique product images using DALL-E 3
- **🛍️ Zazzle Integration**: Automatically creates products with affiliate links
- **📊 Multi-Subreddit Support**: Monitors multiple subreddits for trending content
- **🔄 Automated Pipeline**: Runs continuously to discover and create products
- **📱 Modern Web Interface**: React frontend for monitoring and management
- **🐳 Docker Ready**: Complete containerized deployment
- **📈 Usage Tracking**: Comprehensive OpenAI API usage monitoring
- **🛡️ Error Handling**: Robust error handling and retry mechanisms
- **💳 Donation System**: Accepts donations via Stripe to support the project

## 🚀 Quick Start

### Prerequisites

- Docker and Docker Compose
- OpenAI API key
- Reddit API credentials
- Zazzle affiliate ID
- Stripe account (for donation features)

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/zazzle-agent.git
cd zazzle-agent
```

### 2. Set Up Environment

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
IMGUR_CLIENT_ID=your_imgur_client_id
IMGUR_CLIENT_SECRET=your_imgur_client_secret
STRIPE_SECRET_KEY=your_stripe_secret_key
STRIPE_PUBLISHABLE_KEY=your_stripe_publishable_key
STRIPE_WEBHOOK_SECRET=your_stripe_webhook_secret
```

### 3. Deploy with Docker

```bash
# Start all services
make deploy

# Check status
make status
```

### 4. Access the Application

- **Frontend**: http://localhost:5173
- **API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs

## 🏗️ Architecture

Zazzle Agent is built as a microservices architecture with the following components:

### Core Services

- **API Service** (`app/api.py`): FastAPI backend serving product data and management endpoints
- **Pipeline Service** (`app/pipeline.py`): Main automation pipeline for product generation
- **Interaction Service** (`app/interaction_scheduler.py`): Handles Reddit interactions and engagement
- **Frontend** (`frontend/`): React-based web interface for monitoring and management
- **Database**: SQLite database with Alembic migrations

### Key Components

- **Reddit Agent** (`app/agents/reddit_agent.py`): Discovers and analyzes trending Reddit content
- **Content Generator** (`app/content_generator.py`): Uses AI to generate product ideas and descriptions
- **Image Generator** (`app/image_generator.py`): Creates product images using DALL-E 3
- **Zazzle Product Designer** (`app/zazzle_product_designer.py`): Integrates with Zazzle API
- **Affiliate Linker** (`app/affiliate_linker.py`): Generates affiliate links for products

## 📊 API Endpoints

### Products
- `GET /api/generated_products` - List all generated products
- `GET /api/generated_products/{product_id}` - Get specific product details

### Health & Status
- `GET /health` - Service health check
- `GET /api/status` - System status and metrics

### Pipeline Management
- `POST /api/pipeline/run` - Manually trigger pipeline run
- `GET /api/pipeline/status` - Current pipeline status

## 🛠️ Development

### Local Development Setup

```bash
# Install Python dependencies
poetry install

# Install frontend dependencies
cd frontend && npm install

# Run database migrations
alembic upgrade head

# Start development servers
make dev
```

### Testing

```bash
# Run all tests
make test

# Run specific test categories
pytest tests/test_pipeline.py
pytest tests/test_api.py
pytest tests/test_reddit_agent.py
```

### Code Quality

```bash
# Format code
make format

# Lint code
make lint

# Type checking
mypy app/
```

## 📦 Deployment

### Docker Deployment

```bash
# Production deployment
make deploy

# Quick deployment (no cache)
make deploy-clean

# Stop all services
make stop-all

# View logs
make show-logs
```

### Kubernetes Deployment

```bash
# Deploy to Kubernetes
make k8s-deploy

# Check status
make k8s-status

# View logs
make k8s-logs
```

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `OPENAI_API_KEY` | OpenAI API key for GPT and DALL-E | Yes |
| `REDDIT_CLIENT_ID` | Reddit API client ID | Yes |
| `REDDIT_CLIENT_SECRET` | Reddit API client secret | Yes |
| `REDDIT_USER_AGENT` | Reddit API user agent | Yes |
| `ZAZZLE_AFFILIATE_ID` | Zazzle affiliate ID | Yes |
| `IMGUR_CLIENT_ID` | Imgur client ID | No |
| `IMGUR_CLIENT_SECRET` | Imgur client secret | No |
| `STRIPE_SECRET_KEY` | Stripe secret key | No |
| `STRIPE_PUBLISHABLE_KEY` | Stripe publishable key | No |
| `STRIPE_WEBHOOK_SECRET` | Stripe webhook secret | No |
| `OPENAI_IDEA_MODEL` | GPT model for idea generation (default: gpt-3.5-turbo) | No |
| `DATABASE_URL` | Database connection string | No |

## 📈 Monitoring & Management

### Health Monitoring

```bash
# Check system health
make health-check

# View service status
make status

# Monitor logs
make show-logs
```

### Database Management

```bash
# Backup database
make backup-db

# Restore database
make restore-db

# List backups
make list-backups
```

### Pipeline Management

```bash
# Run pipeline manually
make run-pipeline

# Check pipeline status
make deployment-status

# View pipeline logs
make show-logs-pipeline
```

## 🔧 Configuration

### Subreddit Configuration

Edit `app/products_config.template.json` to configure which subreddits to monitor:

```json
{
  "subreddits": [
    "golf",
    "interiordesign", 
    "digitalart",
    "baking",
    "hiking"
  ],
  "post_filters": {
    "min_score": 100,
    "max_age_hours": 24,
    "prefer_text_posts": true
  }
}
```

### Pipeline Configuration

The pipeline runs automatically every 6 hours and can be configured in the pipeline scheduler:

- **Product Generation**: Every 6 hours
- **Reddit Interactions**: Every 2 hours
- **Error Retries**: 3 attempts with exponential backoff
- **Rate Limiting**: Respects OpenAI and Reddit API limits

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

**Made with ❤️ by the Zazzle Agent Team**

*Transform Reddit trends into profitable products with AI-powered automation.*

## Dual Implementation: Legacy vs Task-Based Product Generation

This codebase now supports two independent implementations for finding trending Reddit posts and generating products:

### 1. Legacy Implementation
- **Method:** `RedditAgent._find_trending_post`
- **Pipeline:** `Pipeline.run_pipeline`
- **Testing:** Legacy tests in `tests/test_reddit_agent.py` (e.g., `test_find_trending_post`, `test_find_reddit_post_skips_processed`)
- **Usage:** Used by the original pipeline and API endpoints for random or legacy product generation.

### 2. Task-Based Implementation
- **Method:** `RedditAgent._find_trending_post_for_task`
- **Pipeline:** `Pipeline.run_task_pipeline_specific`
- **Testing:** Task-based tests in `tests/test_reddit_agent.py` (e.g., `test_find_trending_post_for_task_simple`, `test_get_product_info_for_task_simple`)
- **Usage:** Used by the new task queue, task runner, and event-driven product generation.

**Both implementations are fully tested and can be maintained or refactored independently.**

### How to Run Tests
- To run all tests: `make test`
- To run only Reddit agent tests: `make test-pattern tests/test_reddit_agent.py`
- To run only pipeline tests: `make test-pattern tests/test_pipeline.py`

---

For more details, see the docstrings in `app/agents/reddit_agent.py` and `app/pipeline.py`.

## Creating a Donation via API for an Existing Post

To create a donation (support or commission) for an existing Reddit post, use the following API endpoint:

```
POST /api/donations/create-checkout-session
```

### Request Body Example (Support Donation)
```json
{
  "amount_usd": "5.00",
  "subreddit": "hiking",
  "donation_type": "support",
  "post_id": "<REDDIT_POST_ID>",
  "customer_email": "your@email.com",
  "customer_name": "Your Name",
  "reddit_username": "your_reddit_username",
  "is_anonymous": false,
  "message": "Test support"
}
```

### Request Body Example (Commission Donation)
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
  "commission_message": "Create a beautiful product from an amazing hiking post!"
}
```

- `donation_type` must be either `support` or `commission`.
- For support donations, `message` is used. For commission donations, use `commission_message`.
- `post_id` is required for both types when donating to an existing post.

### Response
A successful request returns a Stripe Checkout session URL for payment.

---

## Progress Update (2025-06-27)

**Today's UI improvements:**
- The Product Detail modal now always displays a "Commissioned by" section at the top, showing commission donor info and message.
- A "Sponsored by" section appears beneath if there are any support donations, listing all sponsors and their messages.
- Fallback logic for fake sponsors has been removed for clarity and accuracy.
- The UI is now more consistent and visually clear for both commission and support donations.

**Screenshot:**

![Product Detail Modal with Commissioned and Sponsored Sections](frontend/docs/assets/progress_2025_06_27.png)
