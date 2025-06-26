# Zazzle Agent Deployment Automation

## Overview

This document outlines the comprehensive deployment automation system for the Zazzle Agent, including all scripts, tools, and best practices for efficient deployment and management.

## 🚀 Quick Start

### First-Time Setup
```bash
# 1. Setup environment
make setup-dev

# 2. Deploy application
make deploy

# 3. Verify deployment
make health-check

# 4. Create initial backup
make backup
```

### Daily Operations
```bash
# Check system health
make health-check

# View logs
make show-logs

# Run pipeline manually
make run-pipeline

# Create backup
make backup
```

## 🔧 Environment Setup Automation

### Script: `scripts/setup-environment.sh`

**Purpose**: Automated environment setup and validation

**Features**:
- ✅ Creates `.env` file from template
- ✅ Validates all required environment variables
- ✅ Tests API connections (OpenAI, Reddit)
- ✅ Installs dependencies (Poetry, npm)
- ✅ Sets up development or production environment

**Usage**:
```bash
# Development setup
./scripts/setup-environment.sh

# Production setup
./scripts/setup-environment.sh --production

# Quick setup (skip API tests)
./scripts/setup-environment.sh --skip-tests
```

**Make Commands**:
```bash
make setup-dev    # Development environment
make setup-prod   # Production environment
make setup-quick  # Quick setup (skip API tests)
```

## 🏥 Health Monitoring Automation

### Script: `scripts/health-monitor.sh`

**Purpose**: Comprehensive system health monitoring

**Features**:
- ✅ Docker service status monitoring
- ✅ API endpoint health checks
- ✅ Frontend accessibility verification
- ✅ Database connectivity and status
- ✅ Environment variable validation
- ✅ Pipeline status monitoring
- ✅ Resource usage tracking
- ✅ Recent logs analysis

**Usage**:
```bash
# Comprehensive health check
./scripts/health-monitor.sh

# Quick health check
./scripts/health-monitor.sh --quick

# Health check with logs
./scripts/health-monitor.sh --logs

# Health check with resource usage
./scripts/health-monitor.sh --resources

# Full health check with everything
./scripts/health-monitor.sh --logs --resources
```

**Make Commands**:
```bash
make health-check     # Comprehensive health check
make health-quick     # Quick health check
make health-logs      # Health check with logs
make health-resources # Health check with resource usage
make health-full      # Full health check with everything
```

## 💾 Backup and Restore Automation

### Script: `scripts/backup-restore.sh`

**Purpose**: Automated backup and restore operations

**Features**:
- ✅ Full application backup (with data consistency)
- ✅ Database-only backup
- ✅ Automatic backup rotation
- ✅ Safe restore operations with confirmation
- ✅ Backup statistics and management
- ✅ Selective file exclusion for efficient backups

**Usage**:
```bash
# Create full backup
./scripts/backup-restore.sh backup

# Create database backup only
./scripts/backup-restore.sh backup-db

# List available backups
./scripts/backup-restore.sh list

# Clean old backups (default 30 days)
./scripts/backup-restore.sh clean

# Clean backups older than specified days
./scripts/backup-restore.sh clean 7

# Show backup statistics
./scripts/backup-restore.sh stats

# Restore from backup
./scripts/backup-restore.sh restore zazzle_agent_backup_20241201_120000.tar.gz

# Restore database only
./scripts/backup-restore.sh restore-db database_backup_20241201_120000.db
```

**Make Commands**:
```bash
make backup                    # Create full backup
make backup-db                 # Create database backup only
make backup-list               # List available backups
make backup-clean              # Clean old backups (30 days)
make backup-clean-days DAYS=7  # Clean backups older than N days
make backup-stats              # Show backup statistics
make restore BACKUP=file.tar.gz # Restore from backup
make restore-db DB=file.db     # Restore database only
```

## 🔧 Maintenance Automation

### System Maintenance
```bash
# Full system maintenance
make maintenance

# Clean up system resources
make cleanup

# Run system diagnosis
make diagnose

# Reset entire system (DANGEROUS)
make reset-system
```

**Maintenance Tasks**:
- ✅ Health check verification
- ✅ Automatic backup creation
- ✅ Old backup cleanup
- ✅ Disk usage monitoring
- ✅ Docker resource cleanup
- ✅ System diagnosis and troubleshooting

## 📊 Status and Monitoring

### Deployment Status
```bash
# Show deployment status
make deployment-status

# Validate deployment
make validate-deployment

# Show logs
make show-logs
make show-logs-api
make show-logs-pipeline
make show-logs-frontend
```

### Pipeline Control
```bash
# Run pipeline manually
make run-pipeline
```

## 🐳 Docker Automation

### Docker Commands
```bash
# Build all Docker images
make docker-build-all

# Start with Docker Compose
make docker-run-local

# Stop Docker Compose
make docker-stop-local

# Show Docker logs
make docker-logs

# Clean Docker resources
make docker-clean
```

## ☸️ Kubernetes Automation

### Kubernetes Commands
```bash
# Deploy to Kubernetes
make k8s-deploy

# Show K8s status
make k8s-status

# Show K8s logs
make k8s-logs

# Delete K8s deployment
make k8s-delete
```

## 🧪 Development Automation

### Development Commands
```bash
# Install Poetry
make install-poetry

# Install dependencies
make install-deps

# Format code
make format

# Lint code
make lint

# Type checking
make type-check

# Run tests
make test
make test-pattern <path>

# Run pipeline locally
make run-full

# Start/stop API
make run-api
make stop-api
```

### Frontend Commands
```bash
# Frontend development
make frontend-dev
make frontend-build
make frontend-preview
make frontend-install
make frontend-lint
make frontend-clean
```

## 🗄️ Database Automation

### Database Commands
```bash
# Alembic migrations
make alembic-init
make alembic-revision
make alembic-upgrade
make alembic-downgrade

# Database operations
make check-db
make check-pipeline-db
make get-last-run
make backup-db
make restore-db
make reset-db
```

## 🔧 Utilities

### Utility Commands
```bash
# Export requirements
make export-requirements

# Clean build artifacts
make clean
```

## 📚 Common Workflows

### Initial Deployment
```bash
# 1. Setup environment
make setup-dev

# 2. Deploy application
make deploy

# 3. Verify deployment
make health-check

# 4. Create initial backup
make backup
```

### Daily Operations
```bash
# Check system health
make health-check

# View recent logs
make show-logs

# Run pipeline if needed
make run-pipeline

# Create daily backup
make backup
```

### Weekly Maintenance
```bash
# Full system maintenance
make maintenance

# Clean up resources
make cleanup

# Check backup statistics
make backup-stats
```

### Troubleshooting
```bash
# Run system diagnosis
make diagnose

# Check health with logs
make health-logs

# View specific service logs
make show-logs-api
make show-logs-pipeline
```

### Backup and Recovery
```bash
# Create backup
make backup

# List available backups
make backup-list

# Restore from backup
make restore BACKUP=zazzle_agent_backup_20241201_120000.tar.gz

# Restore database only
make restore-db DB=database_backup_20241201_120000.db
```

## 🚨 Emergency Procedures

### System Reset (DANGEROUS)
```bash
# Reset entire system
make reset-system

# Redeploy after reset
make deploy
```

### Quick Recovery
```bash
# Stop all services
docker-compose down

# Restart services
docker-compose up -d

# Check health
make health-check
```

## 📋 Best Practices

### 1. Environment Management
- Always use `make setup-dev` for first-time setup
- Validate environment variables before deployment
- Test API connections during setup

### 2. Deployment
- Use `make deploy` for initial deployment
- Use `make deploy-clean` when changing dependencies
- Use `make deploy-quick` for testing without pipeline

### 3. Monitoring
- Run `make health-check` regularly
- Monitor logs with `make show-logs`
- Use `make health-full` for comprehensive monitoring

### 4. Backup Strategy
- Create backups before major changes
- Use `make backup` for full backups
- Use `make backup-db` for database-only backups
- Clean old backups regularly with `make backup-clean`

### 5. Maintenance
- Run `make maintenance` weekly
- Use `make cleanup` to free up resources
- Monitor disk usage and backup statistics

### 6. Troubleshooting
- Use `make diagnose` for systematic troubleshooting
- Check logs with `make show-logs`
- Verify health with `make health-check`

## 🔒 Security Considerations

### Environment Variables
- Never commit `.env` files to version control
- Use `env.example` as a template
- Validate all required variables during setup

### Backup Security
- Store backups in secure locations
- Use encryption for sensitive data
- Regularly test backup restoration

### Access Control
- Limit access to deployment scripts
- Use proper file permissions
- Monitor system access

## 📈 Performance Optimization

### Docker Optimization
- Use Docker layer caching effectively
- Clean up unused Docker resources
- Monitor container resource usage

### Backup Optimization
- Exclude unnecessary files from backups
- Use incremental backups when possible
- Compress backup files for storage efficiency

### Monitoring Optimization
- Use quick health checks for regular monitoring
- Use comprehensive checks for troubleshooting
- Monitor resource usage trends

## 🎯 Future Enhancements

### Planned Improvements
1. **Automated Testing**: Integration with CI/CD pipelines
2. **Monitoring Dashboard**: Web-based monitoring interface
3. **Alert System**: Automated alerts for system issues
4. **Performance Metrics**: Detailed performance monitoring
5. **Auto-scaling**: Automatic resource scaling based on load
6. **Disaster Recovery**: Automated disaster recovery procedures

### Monitoring Enhancements
1. **Metrics Collection**: System and application metrics
2. **Log Aggregation**: Centralized log management
3. **Alert Integration**: Integration with notification systems
4. **Performance Baselines**: Automated performance benchmarking

## 📞 Support

### Getting Help
1. Check the troubleshooting section
2. Run `make diagnose` for systematic analysis
3. Review logs with `make show-logs`
4. Check health status with `make health-check`

### Common Issues
1. **Environment Issues**: Use `make setup-dev` to reinitialize
2. **Service Failures**: Check logs and restart services
3. **Database Issues**: Use `make backup-db` and `make restore-db`
4. **Resource Issues**: Use `make cleanup` to free resources

## Conclusion

This comprehensive deployment automation system provides:

- ✅ **One-command deployment** from scratch
- ✅ **Automated environment setup** and validation
- ✅ **Comprehensive health monitoring** with detailed reporting
- ✅ **Automated backup and restore** with safety features
- ✅ **Systematic maintenance** procedures
- ✅ **Efficient troubleshooting** tools
- ✅ **Production-ready** deployment automation

The system is designed for both development efficiency and production reliability, with clear separation between local development workflows and production deployment procedures. 