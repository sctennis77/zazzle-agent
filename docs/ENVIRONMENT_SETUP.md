# Environment Setup Guide

This document provides comprehensive instructions for setting up the Zazzle Agent development environment using the new make commands.

## 🚀 Quick Start

### Complete Fresh Environment Setup

For a completely fresh start (recommended for new installations or when troubleshooting):

```bash
make full_from_fresh_env
```

This command performs the following steps automatically:

1. **Stop existing services** - Terminates any running API or frontend processes
2. **Clean environment** - Removes virtual environment, outputs, and coverage files
3. **Install dependencies** - Creates new virtual environment and installs all Python packages
4. **Run full test suite** - Executes all 200+ tests with coverage reporting
5. **Test interaction agent** - Verifies the Reddit interaction agent functionality
6. **Start API server** - Launches the FastAPI server in the background
7. **Start frontend** - Launches the React development server in the background
8. **Verify services** - Checks that both services are responding correctly

### Quick Development Setup

For existing installations where you just want to start services:

```bash
make dev_setup
```

This command:
- Installs dependencies only if virtual environment doesn't exist
- Runs tests to ensure everything is working
- Starts both API and frontend services

## 🔧 Service Management

### Start All Services

```bash
make start-services
```

Starts both the API server (port 8000) and frontend development server (port 5173) in the background.

### Stop All Services

```bash
make stop-services
```

Terminates all running services (API and frontend).

### Restart All Services

```bash
make restart-services
```

Stops and then starts all services (useful for applying changes).

### Check System Status

```bash
make status
```

Provides a comprehensive health check of the system:
- API server status
- Frontend server status
- Database existence and size
- Virtual environment status
- Frontend dependencies status

## 📊 System Status Output

When you run `make status`, you'll see output like this:

```
📊 System Status Check
==================================================
🔍 Checking API server...
✅ API Server: RUNNING (http://localhost:8000)

🔍 Checking frontend...
✅ Frontend: RUNNING (http://localhost:5173)

🔍 Checking database...
✅ Database: EXISTS (zazzle_pipeline.db)
-rw-r--r--@ 1 user staff 180K Jun 18 15:47 zazzle_pipeline.db

🔍 Checking virtual environment...
✅ Virtual Environment: EXISTS (zam)

🔍 Checking frontend dependencies...
✅ Frontend Dependencies: INSTALLED
```

## 🎯 Complete Workflow Example

Here's a typical development workflow using the new commands:

### 1. Initial Setup (First Time)

```bash
# Complete fresh setup
make full_from_fresh_env
```

### 2. Daily Development

```bash
# Check system status
make status

# If services aren't running, start them
make start-services

# Run the pipeline to generate a new product
make run-full

# Test the interaction agent
make test-interaction-agent
```

### 3. Troubleshooting

```bash
# If something isn't working, restart services
make restart-services

# If that doesn't work, do a complete fresh setup
make full_from_fresh_env
```

## 🔍 Available Services

After running the setup commands, you'll have access to:

- **API Server**: http://localhost:8000
  - `/api/generated_products` - List all generated products
  - `/api/health` - Health check endpoint
  - Interactive API docs at http://localhost:8000/docs

- **Frontend**: http://localhost:5173
  - React development server with hot reload
  - Product management interface
  - Interaction agent interface

## 📝 Environment Variables

Make sure you have a `.env` file with the following variables:

```env
OPENAI_API_KEY=your_openai_api_key_here
ZAZZLE_AFFILIATE_ID=your_zazzle_affiliate_id_here
REDDIT_CLIENT_ID=your_reddit_client_id_here
REDDIT_CLIENT_SECRET=your_reddit_client_secret_here
REDDIT_USER_AGENT=your_user_agent_here
IMGUR_CLIENT_ID=your_imgur_client_id_here
```

## 🧪 Testing

The setup includes comprehensive testing:

- **Unit Tests**: 200+ tests covering all components
- **Integration Tests**: End-to-end pipeline testing
- **Interaction Agent Tests**: Reddit interaction functionality
- **Coverage Reporting**: 69%+ code coverage

## 🚨 Troubleshooting

### Common Issues

1. **Port 8000 already in use**
   ```bash
   make stop-api
   # or
   make stop-services
   ```

2. **Frontend not starting**
   ```bash
   cd frontend && npm install
   make start-services
   ```

3. **Database issues**
   ```bash
   make reset-db
   make alembic-upgrade
   ```

4. **Virtual environment issues**
   ```bash
   make clean
   make install
   ```

### Getting Help

- Run `make help` to see all available commands
- Run `make status` to check system health
- Check the logs with `make logs-tail`
- Use `make health-check` for detailed dependency verification

## 📈 Performance Notes

- **API Server**: Starts in ~10 seconds
- **Frontend**: Starts in ~5 seconds
- **Full Setup**: Takes ~2-3 minutes for complete fresh installation
- **Tests**: Run in ~30 seconds
- **Pipeline**: Takes ~1-2 minutes to generate a product

## 🔄 Continuous Development

For ongoing development:

1. **Start services**: `make start-services`
2. **Make changes** to your code
3. **Run tests**: `make test`
4. **Test interaction agent**: `make test-interaction-agent`
5. **Generate products**: `make run-full`
6. **Stop services**: `make stop-services` (when done)

This workflow ensures you always have a clean, tested, and functional development environment. 