# Zazzle Agent Deployment Automation (Slim Production)

## Overview

This document outlines the **essential deployment automation** for the Zazzle Agent, focusing only on critical infrastructure for a slim, production-ready application.

## 🚀 Critical Infrastructure

### **Essential Components Only**
1. **Environment Setup** - Required for deployment
2. **Health Monitoring** - Required for reliability
3. **Database Backup** - Required for data safety
4. **Basic Deployment** - Required for operation

## 🚀 Quick Start (Production)

### First-Time Setup
```bash
# 1. Setup environment
make setup-prod

# 2. Deploy application
make deploy

# 3. Verify deployment
make health-check

# 4. Create database backup
make backup-db
```

### Daily Operations
```bash
# Check system health
make health-check

# View logs
make show-logs

# Run pipeline manually
make run-pipeline

# Backup database
make backup-db
```

## 🔧 Critical Environment Setup

### Script: `scripts/setup-environment.sh`

**Purpose**: Essential environment setup and validation

**Critical Features**:
- ✅ Creates `.env` file from template
- ✅ Validates required environment variables
- ✅ Tests API connections (OpenAI, Reddit)
- ✅ Sets up production environment

**Usage**:
```bash
# Production setup (essential)
./scripts/setup-environment.sh --production

# Quick setup (skip API tests)
./scripts/setup-environment.sh --skip-tests
```

**Make Commands**:
```bash
make setup-prod   # Production environment (CRITICAL)
make setup-quick  # Quick setup (CRITICAL)
```

## 🏥 Essential Health Monitoring

### Script: `scripts/health-monitor.sh`

**Purpose**: Critical system health monitoring

**Essential Features**:
- ✅ Docker service status monitoring
- ✅ API endpoint health checks
- ✅ Database connectivity verification
- ✅ Environment variable validation

**Usage**:
```bash
# Essential health check
./scripts/health-monitor.sh --quick

# Health check with logs (for troubleshooting)
./scripts/health-monitor.sh --logs
```

**Make Commands**:
```bash
make health-check     # Essential health check (CRITICAL)
make health-logs      # Health check with logs (CRITICAL)
```

## 💾 Critical Backup (Database Only)

### Script: `scripts/backup-restore.sh`

**Purpose**: Database backup and restore (essential for data safety)

**Critical Features**:
- ✅ Database-only backup (lightweight)
- ✅ Safe restore operations
- ✅ Basic backup management

**Usage**:
```bash
# Create database backup (CRITICAL)
./scripts/backup-restore.sh backup-db

# List database backups
./scripts/backup-restore.sh list

# Restore database (CRITICAL)
./scripts/backup-restore.sh restore-db database_backup_20241201_120000.db
```

**Make Commands**:
```bash
make backup-db                 # Database backup (CRITICAL)
make restore-db DB=file.db     # Database restore (CRITICAL)
```

## 🚀 Essential Deployment Commands

### Core Deployment
```bash
# Deploy from scratch (CRITICAL)
make deploy

# Deploy with clean images (when needed)
make deploy-clean

# Quick deployment (skip pipeline)
make deploy-quick
```

### Essential Status Commands
```bash
# Show deployment status (CRITICAL)
make deployment-status

# Validate deployment (CRITICAL)
make validate-deployment

# Show logs (CRITICAL)
make show-logs
```

### Pipeline Control
```bash
# Run pipeline manually (CRITICAL)
make run-pipeline
```

## 🗄️ Essential Database Operations

### Database Commands
```bash
# Check database (CRITICAL)
make check-db

# Backup database (CRITICAL)
make backup-db

# Restore database (CRITICAL)
make restore-db DB=file.db
```

## 📚 Essential Workflows

### Production Deployment
```bash
# 1. Setup environment
make setup-prod

# 2. Deploy application
make deploy

# 3. Verify deployment
make health-check

# 4. Backup database
make backup-db
```

### Daily Operations
```bash
# Check system health
make health-check

# View logs if needed
make show-logs

# Run pipeline if needed
make run-pipeline

# Backup database
make backup-db
```

### Troubleshooting
```bash
# Check health with logs
make health-logs

# View specific service logs
make show-logs-api
make show-logs-pipeline
```

## 🚨 Emergency Procedures

### Quick Recovery
```bash
# Stop all services
docker-compose down

# Restart services
docker-compose up -d

# Check health
make health-check
```

### Database Recovery
```bash
# Restore database from backup
make restore-db DB=database_backup_20241201_120000.db
```

## 📋 Critical Best Practices

### 1. Environment Management
- Use `make setup-prod` for production setup
- Validate environment variables before deployment
- Test API connections during setup

### 2. Deployment
- Use `make deploy` for initial deployment
- Use `make deploy-clean` when changing dependencies
- Always verify with `make health-check`

### 3. Monitoring
- Run `make health-check` regularly
- Monitor logs with `make show-logs`
- Check database connectivity

### 4. Backup Strategy
- Use `make backup-db` for database backups
- Test database restoration regularly
- Keep multiple database backups

### 5. Troubleshooting
- Use `make health-logs` for systematic troubleshooting
- Check logs with `make show-logs`
- Verify health with `make health-check`

## 🔒 Essential Security

### Environment Variables
- Never commit `.env` files to version control
- Use `env.example` as a template
- Validate all required variables during setup

### Backup Security
- Store database backups securely
- Test backup restoration regularly
- Keep backups in multiple locations

## 🎯 What's NOT Included (For Slim Deployment)

### Removed for Simplicity
- ❌ Full application backups (heavy, not essential)
- ❌ Resource usage monitoring (nice-to-have)
- ❌ Complex maintenance procedures
- ❌ System reset functionality
- ❌ Backup statistics and rotation
- ❌ Comprehensive diagnosis tools
- ❌ Kubernetes deployment (Docker Compose is sufficient)
- ❌ Advanced monitoring features

### Why These Are Removed
- **Full backups**: Database backup is sufficient for data safety
- **Resource monitoring**: Docker health checks are adequate
- **Complex maintenance**: Basic operations are sufficient
- **System reset**: Manual Docker commands are simpler
- **Kubernetes**: Docker Compose is lighter and sufficient

## 📞 Essential Support

### Getting Help
1. Run `make health-check` for basic status
2. Check logs with `make show-logs`
3. Verify environment with `make setup-prod --skip-tests`

### Common Issues
1. **Environment Issues**: Use `make setup-prod` to reinitialize
2. **Service Failures**: Check logs and restart services
3. **Database Issues**: Use `make backup-db` and `make restore-db`
4. **Deployment Issues**: Use `make deploy-clean`

## Conclusion

This **slim deployment automation** provides:

- ✅ **Essential environment setup** for production
- ✅ **Critical health monitoring** for reliability
- ✅ **Database backup and restore** for data safety
- ✅ **Basic deployment automation** for operation
- ✅ **Minimal overhead** for maximum efficiency

The system focuses only on **critical infrastructure** needed for a production deployment, removing unnecessary complexity while maintaining reliability and data safety. 