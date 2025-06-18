# Test Database Quick Reference

## Quick Commands

### Create Test Database
```bash
# Create default test database
make create-test-db

# Create with backup
python3 scripts/create_test_db.py --backup

# Create specific test database
python3 scripts/create_test_db.py --db-path my_test.db

# Create interaction agent test database
python3 scripts/create_test_db.py --interaction-agent
```

### Database Management
```bash
# Check database contents
make check-db

# Backup database
make backup-db

# Reset database (WARNING: deletes all data)
make reset-db

# Apply database migrations
make alembic-upgrade
```

### Testing
```bash
# Run all tests
make test

# Run specific test file
make test-pattern tests/test_interaction_agent.py

# Test interaction agent
make test-interaction-agent
```

## Common Workflows

### Setting Up New Test Environment
```bash
# 1. Backup existing database
make backup-db

# 2. Create fresh test database
make create-test-db

# 3. Verify setup
make check-db

# 4. Run tests
make test
```

### Adding New Test Data
```bash
# 1. Modify create_test_data.py or scripts/create_test_db.py
# 2. Create new test database
make create-test-db

# 3. Test the new data
make test-pattern tests/test_your_new_test.py
```

### Database Schema Changes
```bash
# 1. Create migration
make alembic-revision

# 2. Apply migration
make alembic-upgrade

# 3. Recreate test data
make create-test-db

# 4. Test changes
make test
```

## Troubleshooting

### Database Locked
```bash
make stop-api
# Wait a moment, then retry your command
```

### Migration Issues
```bash
# Check current status
alembic current

# Downgrade if needed
make alembic-downgrade

# Upgrade to latest
make alembic-upgrade
```

### Test Data Missing
```bash
# Recreate test data
make create-test-db

# Check database contents
make check-db
```

## File Locations

- **Test Database**: `test_interaction_agent.db`
- **Production Database**: `zazzle_pipeline.db`
- **Test Data Script**: `scripts/create_test_db.py`
- **Legacy Test Script**: `create_test_data.py`
- **Database Scripts**: `scripts/` directory
- **Migrations**: `alembic/` directory

## Environment Variables

- `DATABASE_URL`: Database connection string
- `TESTING`: Set to `true` for test environment
- `OUTPUT_DIR`: Test output directory 