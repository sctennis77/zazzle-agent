# Test Database Setup and Management

This document outlines the process for creating, updating, and managing test databases for the Zazzle Agent project.

## Overview

The project uses SQLite databases for both production and testing. Test databases are created with sample data to ensure consistent testing environments.

## Database Types

### 1. Production Database
- **File**: `zazzle_pipeline.db`
- **Purpose**: Stores actual pipeline runs, Reddit posts, and product information
- **Location**: Project root directory

### 2. Test Databases
- **Files**: 
  - `test_interaction_agent.db` - For interaction agent tests
  - In-memory databases (for unit tests via pytest fixtures)
- **Purpose**: Isolated test data for specific test scenarios

## Setting Up Test Database

### Method 1: Using the Test Data Creation Script

The `scripts/create_test_data.py` script creates a comprehensive test database with sample data:

```bash
# Create test data for interaction agent
python3 scripts/create_test_data.py
```

This script will:
- Initialize a new database (or use existing)
- Create a sample pipeline run with COMPLETED status
- Add a test Reddit post with realistic data
- Create 3 sample products with affiliate links
- Return IDs of created entities for reference

### Method 2: Using Make Commands

```bash
# Initialize database with migrations
make alembic-upgrade

# Create test data
python3 scripts/create_test_data.py

# Check database contents
make check-db
```

### Method 3: Manual Database Reset

```bash
# Backup existing database (recommended)
make backup-db

# Reset database (WARNING: deletes all data)
make reset-db

# Recreate tables with latest schema
make alembic-upgrade

# Create test data
python3 scripts/create_test_data.py
```

## Test Database Schema

The test database includes the following tables:

### PipelineRun
- `id`: Primary key
- `status`: Pipeline status (COMPLETED, RUNNING, FAILED, etc.)
- `start_time`: Pipeline start timestamp
- `end_time`: Pipeline end timestamp
- `subreddit`: Target subreddit name

### RedditPost
- `id`: Primary key
- `reddit_id`: Reddit post ID
- `title`: Post title
- `content`: Post content
- `score`: Post score
- `subreddit`: Subreddit name
- `url`: Post URL
- `pipeline_run_id`: Foreign key to PipelineRun
- `comment_summary`: Summary of comments

### ProductInfo
- `id`: Primary key
- `title`: Product title
- `description`: Product description
- `image_url`: Product image URL
- `affiliate_link`: Zazzle affiliate link
- `reddit_post_id`: Foreign key to RedditPost
- `pipeline_run_id`: Foreign key to PipelineRun

## Sample Test Data

The `scripts/create_test_data.py` script creates the following sample data:

### Pipeline Run
- Status: COMPLETED
- Subreddit: "test_subreddit"
- Timestamps: Current UTC time

### Reddit Post
- ID: "test_post_123"
- Title: "Test Post Title"
- Content: "This is a test post content for testing the interaction agent."
- Score: 1000
- URL: "https://reddit.com/r/test_subreddit/comments/test_post_123"
- Comment Summary: "Test comment summary"

### Products (3 samples)
- Titles: "Test Product 1", "Test Product 2", "Test Product 3"
- Descriptions: Corresponding descriptions
- Image URLs: "https://example.com/test_image_{1,2,3}.jpg"
- Affiliate Links: "https://zazzle.com/test_product_{1,2,3}?affiliate_id=test"

## Updating Test Database for New Tests

### 1. Adding New Test Scenarios

To add new test scenarios, modify `scripts/create_test_data.py`:

```python
# Add new pipeline run with different status
pipeline_run_failed = PipelineRun(
    status=PipelineStatus.FAILED.value,
    start_time=datetime.now(timezone.utc),
    end_time=datetime.now(timezone.utc),
    subreddit="failed_test_subreddit"
)

# Add new Reddit post with different characteristics
reddit_post_low_score = RedditPost(
    reddit_id="low_score_post",
    title="Low Score Post",
    content="This post has a low score for testing edge cases.",
    score=5,  # Low score
    subreddit="test_subreddit",
    url="https://reddit.com/r/test_subreddit/comments/low_score_post",
    pipeline_run_id=pipeline_run.id,
    comment_summary="Low engagement post"
)
```

### 2. Database Migration

When schema changes are made:

```bash
# Generate new migration
make alembic-revision

# Apply migration to test database
make alembic-upgrade

# Recreate test data with new schema
python3 scripts/create_test_data.py
```

### 3. Testing Database Changes

```bash
# Run specific test file
make test-pattern tests/test_interaction_agent.py

# Run all tests
make test

# Check database contents
make check-db
```

## Best Practices

### 1. Database Isolation
- Use separate test databases for different test scenarios
- Never use production database for testing
- Use in-memory databases for unit tests when possible

### 2. Data Consistency
- Always create test data with known, predictable values
- Use realistic but fake data (e.g., "test_" prefixed IDs)
- Include edge cases in test data (low scores, empty content, etc.)

### 3. Cleanup
- Backup databases before major changes
- Use `make backup-db` before destructive operations
- Clean up test databases after testing

### 4. Version Control
- Don't commit large database files to git
- Include database schema migrations in version control
- Document database changes in commit messages

## Troubleshooting

### Common Issues

1. **Database Locked**
   ```bash
   # Stop any running processes
   make stop-api
   # Wait a moment, then retry
   ```

2. **Migration Conflicts**
   ```bash
   # Check current migration status
   alembic current
   # Downgrade if needed
   make alembic-downgrade
   # Upgrade to latest
   make alembic-upgrade
   ```

3. **Test Data Not Found**
   ```bash
   # Recreate test data
   python3 scripts/create_test_data.py
   # Check database contents
   make check-db
   ```

### Database Inspection

```bash
# Check database contents
make check-db

# Get last pipeline run details
make get-last-run

# Check pipeline database status
make check-pipeline-db

# Run health check
make health-check
```

## Integration with CI/CD

For continuous integration, the test database setup should be automated:

```yaml
# Example GitHub Actions step
- name: Setup Test Database
  run: |
    make alembic-upgrade
    python3 scripts/create_test_data.py
    make test
```

## Related Files

- `scripts/create_test_data.py` - Main test data creation script
- `scripts/init_db.py` - Database initialization script
- `scripts/check_db.py` - Database inspection script
- `tests/conftest.py` - Pytest configuration with database fixtures
- `alembic/` - Database migration files
- `Makefile` - Database management commands 