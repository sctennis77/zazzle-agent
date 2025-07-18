# Slow Tests Optimization Plan

## Investigation Results

### Current State
- **Full test suite**: 196.83 seconds (3:16) total runtime
- **Content generator tests**: Taking 10+ seconds each in full suite, but <0.5s when run in isolation
- **OpenAI API calls**: Already properly mocked in tests

### Root Cause Analysis

The slowdown appears to be caused by test interaction/interference rather than actual test logic:

1. **Global State Issues**: Tests may be sharing global state through the singleton usage tracker
2. **Fixture Interference**: Some test fixtures may be taking time to set up/tear down
3. **Excessive Logging**: The OpenAI usage tracker logs detailed JSON for every call
4. **Database Connections**: SQLite database connections may be slow or contended

### Optimization Strategy

#### Phase 1: Immediate Fixes (Low Risk)

1. **Optimize Usage Tracker for Tests**
   - Add test mode flag to `OpenAIUsageTracker` to disable detailed logging
   - Create separate tracker instance for tests to avoid global state issues
   - Skip session summary logging during tests

2. **Mock Usage Tracker in Tests**
   - Patch `track_openai_call` decorator to be a no-op in tests
   - Mock the usage tracker completely to eliminate logging overhead

3. **Optimize Test Database Operations**
   - Use in-memory SQLite for faster database operations
   - Implement proper database cleanup between tests

#### Phase 2: Test Infrastructure Improvements (Medium Risk)

4. **Isolate Test State**
   - Reset global singleton state between tests
   - Use pytest fixtures to ensure clean state

5. **Optimize Test Fixtures**
   - Identify and optimize slow fixtures
   - Use session-scoped fixtures where appropriate

6. **Parallel Test Execution**
   - Configure pytest-xdist for parallel test execution
   - Ensure tests are thread-safe

#### Phase 3: Long-term Improvements (Higher Risk)

7. **Refactor Usage Tracker**
   - Make usage tracker dependency-injected rather than global singleton
   - Add proper test doubles/mocks

8. **Test Categorization**
   - Separate unit tests from integration tests
   - Create fast test suite for development

### Implementation Priority

1. **High Priority**: Mock usage tracker in tests (immediate 90% improvement expected)
2. **Medium Priority**: Optimize database operations
3. **Low Priority**: Refactor to eliminate global state

### Success Metrics

- **Target**: Full test suite should run in <60 seconds
- **Stretch Goal**: Content generator tests should run in <0.1s each
- **Minimum**: No test should take >2 seconds individually

### Testing Plan

1. Implement usage tracker mocking
2. Run full test suite and measure improvement
3. Identify remaining slow tests
4. Iterate on optimizations

### Files to Modify

- `app/utils/openai_usage_tracker.py` - Add test mode
- `tests/conftest.py` - Add usage tracker mocking
- `tests/test_content_generator*.py` - Verify mocking works
- `pyproject.toml` - Add pytest-xdist for parallelization