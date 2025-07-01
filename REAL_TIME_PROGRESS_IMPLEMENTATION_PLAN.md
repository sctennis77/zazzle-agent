# Real-Time Progress Tracking & On-Demand Compute Implementation Plan

## Overview
This document outlines the implementation plan for adding real-time progress tracking and on-demand compute to the Zazzle Agent commission system. The goal is to provide users with immediate feedback on their commission progress while optimizing compute costs by only running processing when needed.

## Technology Choices

### Real-Time Updates: Server-Sent Events (SSE)
**Why SSE over WebSockets:**
- One-way communication (server → client) - perfect for progress updates
- Native FastAPI support - built-in `StreamingResponse`
- Automatic reconnection - browsers handle reconnection automatically
- No connection management - no need to track connections, handle disconnects
- HTTP-based - works through proxies, firewalls, load balancers
- Less code - no WebSocket upgrade handling, connection state management

### On-Demand Compute: Local Job Controller
**Why Local over K8s Jobs:**
- Simpler than K8s (no cluster management)
- Faster startup (no container pull/start)
- Easier debugging
- No K8s dependencies
- Can still run alongside existing task runner

## Implementation Phases

### Phase 1: Progress Tracking (Week 1)
**Goal:** Add real-time progress tracking infrastructure

**Tasks:**
1. **Database Schema Changes**
   - Add `progress_events` table
   - Add `k8s_jobs` table (for local job tracking)
   - Create Alembic migration

2. **Progress Event System**
   - Create `ProgressEvent` model
   - Define progress stages: `created`, `processing`, `generating_ideas`, `creating_images`, `uploading`, `creating_products`, `completed`
   - Store progress events in database with timestamps

3. **Progress Tracking Service**
   - Create `ProgressTracker` service
   - Methods to emit progress events
   - Hook into existing pipeline stages

4. **SSE Endpoint**
   - Add `/api/progress/{task_id}/stream` endpoint
   - Implement Server-Sent Events streaming
   - Handle connection management

5. **Pipeline Integration**
   - Hook progress updates into existing pipeline
   - Add progress events at key stages
   - **Keep existing task runner unchanged**

**Deliverables:**
- Progress tracking database tables
- SSE endpoint for real-time updates
- Progress events emitted during pipeline execution
- Existing task runner continues to work

### Phase 2: Local Job Controller (Week 2)
**Goal:** Implement on-demand local job processing

**Tasks:**
1. **Job Controller Service**
   - Create `LocalJobController` service
   - Watch for new tasks in database
   - Spawn subprocess for each task
   - Monitor job status and update progress

2. **Job Processing**
   - Implement isolated process execution
   - Use Python's `subprocess` or `multiprocessing`
   - Process management with proper cleanup
   - Progress updates via database events

3. **Job Templates**
   - Create job configuration templates
   - Resource limits and environment setup
   - Job completion handling

4. **Integration with Existing System**
   - Run alongside existing task runner
   - Test with subset of tasks
   - Compare results between both systems

**Deliverables:**
- Local job controller service
- Job processing infrastructure
- Both systems running in parallel
- Validation of job controller results

### Phase 3: Frontend Integration (Week 3)
**Goal:** Add real-time progress UI components

**Tasks:**
1. **Real-Time UI Components**
   - Progress tracking modal/component
   - Live status updates
   - Progress bars for each stage
   - Error handling and retry options

2. **Commission Status Page**
   - Dedicated page showing all user commissions
   - Real-time status updates
   - Product preview when ready

3. **SSE Client Integration**
   - Frontend SSE client implementation
   - Connection management and reconnection
   - Error handling for connection issues

**Deliverables:**
- Real-time progress UI components
- Commission status page
- SSE client integration
- Error handling and retry UI

### Phase 4: Validation & Migration (Week 4)
**Goal:** Comprehensive testing and gradual migration

**Tasks:**
1. **Comprehensive Testing**
   - Test job controller with various task types
   - Validate progress tracking accuracy
   - Performance testing and optimization
   - Error handling validation

2. **Gradual Migration**
   - Move subset of tasks to job controller
   - Monitor and compare results
   - Gradually increase job controller usage
   - Task runner becomes fallback only

3. **Configuration Management**
   - Add configuration options for system selection
   - Priority settings for job controller vs task runner
   - Feature flags for gradual rollout

**Deliverables:**
- Comprehensive test suite
- Gradual migration strategy
- Configuration management
- Both systems validated and working

### Phase 5: Cleanup (Week 5)
**Goal:** Remove old system once new system is proven

**Tasks:**
1. **Final Validation**
   - Ensure job controller handles all edge cases
   - Performance validation
   - Error handling validation

2. **Code Cleanup**
   - Remove task runner code
   - Clean up old configurations
   - Update documentation

3. **Deployment**
   - Deploy final version
   - Monitor for any issues
   - Update deployment scripts

**Deliverables:**
- Clean codebase with only job controller
- Updated documentation
- Deployed and monitored system

## Database Schema Changes

### New Tables

```sql
-- Progress events for real-time tracking
CREATE TABLE progress_events (
    id INTEGER PRIMARY KEY,
    task_id INTEGER REFERENCES pipeline_tasks(id),
    stage VARCHAR(50) NOT NULL,
    message TEXT,
    progress_percent INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Job tracking for local job integration
CREATE TABLE local_jobs (
    id INTEGER PRIMARY KEY,
    task_id INTEGER REFERENCES pipeline_tasks(id),
    job_name VARCHAR(255) NOT NULL,
    process_id INTEGER,
    status VARCHAR(50) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP NULL,
    error_message TEXT NULL
);
```

## API Endpoints

### New Endpoints

```
GET /api/progress/{task_id}/stream     # SSE endpoint for real-time updates
GET /api/progress/{task_id}/status     # Current status snapshot
GET /api/commissions/user/{user_id}    # User's commission history
POST /api/jobs/create                  # Create local job (internal)
GET /api/jobs/{job_id}/status          # Job status endpoint
```

## Configuration

### Environment Variables

```python
# config.py additions
USE_JOB_CONTROLLER = True          # Enable new system
KEEP_TASK_RUNNER = True            # Keep fallback
JOB_CONTROLLER_PRIORITY = 10       # Higher priority than task runner
PROGRESS_UPDATE_INTERVAL = 1       # Seconds between progress updates
MAX_CONCURRENT_JOBS = 3            # Maximum concurrent job processes
```

## Fallback Strategy

### Dual System Approach
1. **Primary**: Local job controller processes new commissions
2. **Fallback**: Existing task runner continues running
3. **Migration**: Gradually move tasks from task runner to job controller
4. **Validation**: Compare results between both systems
5. **Cleanup**: Remove task runner once job controller is proven

### Configuration-driven
```python
# Enable/disable systems via configuration
USE_JOB_CONTROLLER = True  # Enable new system
KEEP_TASK_RUNNER = True    # Keep fallback
JOB_CONTROLLER_PRIORITY = 10  # Higher priority than task runner
```

## Progress Stages

### Commission Processing Stages
1. **created** - Task created, waiting to start
2. **processing** - Job started, initializing
3. **generating_ideas** - Generating product ideas from Reddit content
4. **creating_images** - Creating images with DALL-E
5. **uploading** - Uploading images to Imgur
6. **creating_products** - Creating products on Zazzle
7. **completed** - Commission completed successfully

### Error Stages
- **failed** - Commission failed with error
- **retrying** - Commission being retried

## Testing Strategy

### Phase 1 Testing
- Unit tests for progress tracking service
- Integration tests for SSE endpoint
- Pipeline integration tests

### Phase 2 Testing
- Job controller unit tests
- Process management tests
- Integration tests with existing pipeline

### Phase 3 Testing
- Frontend component tests
- SSE client tests
- End-to-end commission flow tests

### Phase 4 Testing
- Performance testing
- Load testing
- Error scenario testing
- Migration validation tests

## Monitoring & Observability

### Metrics to Track
- Job processing time
- Progress update frequency
- SSE connection count
- Error rates
- System resource usage

### Logging
- Progress event logging
- Job lifecycle logging
- Error logging with context
- Performance metrics logging

## Rollback Plan

### If Issues Arise
1. **Immediate**: Disable job controller, revert to task runner only
2. **Investigation**: Analyze logs and metrics
3. **Fix**: Address issues in job controller
4. **Re-test**: Validate fixes before re-enabling

### Rollback Triggers
- High error rates (>5%)
- Performance degradation (>50% slower)
- Resource exhaustion
- User complaints about missing progress updates

## Success Criteria

### Phase 1 Success
- ✅ Progress events stored in database
- ✅ SSE endpoint returns real-time updates
- ✅ Pipeline emits progress events
- ✅ Existing task runner unaffected

### Phase 2 Success
- ✅ Job controller processes tasks successfully
- ✅ Progress updates work in job controller
- ✅ Both systems run in parallel
- ✅ Results match between systems

### Phase 3 Success
- ✅ Frontend displays real-time progress
- ✅ Users can see commission status
- ✅ Error handling works properly
- ✅ SSE connections stable

### Phase 4 Success
- ✅ Job controller handles all task types
- ✅ Performance meets requirements
- ✅ Error handling robust
- ✅ Migration completed successfully

### Phase 5 Success
- ✅ Task runner removed
- ✅ Codebase clean
- ✅ System stable in production
- ✅ Documentation updated

## Implementation Notes

### Key Principles
1. **Incremental Development**: Each phase builds on the previous
2. **Validation First**: Test thoroughly before moving to next phase
3. **Fallback Always**: Keep existing system as backup
4. **User Experience**: Real-time feedback is priority
5. **Performance**: Don't degrade existing performance

### Risk Mitigation
1. **Database Changes**: Use Alembic migrations, test thoroughly
2. **Process Management**: Proper cleanup, resource limits
3. **SSE Connections**: Connection pooling, timeout handling
4. **Error Handling**: Comprehensive error catching and reporting
5. **Resource Usage**: Monitor and limit concurrent jobs

### Performance Considerations
1. **SSE Connections**: Limit concurrent connections
2. **Database Queries**: Optimize progress event queries
3. **Process Spawning**: Limit concurrent job processes
4. **Memory Usage**: Monitor job process memory usage
5. **Network**: Optimize progress update frequency

---

**This plan provides a comprehensive roadmap for implementing real-time progress tracking and on-demand compute while maintaining system reliability and user experience.** 