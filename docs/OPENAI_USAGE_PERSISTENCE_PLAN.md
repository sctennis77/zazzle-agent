# OpenAI Usage Persistence Implementation Plan

## Overview
This plan outlines how to implement OpenAI API usage tracking and persistence for commission tasks (pipeline runs) and the promotion agent. Currently, the database tables exist but usage data is not being persisted.

## Phase 1: Database Schema Updates

### 1.1 Update AgentScannedPost Table
Add usage tracking columns to the existing `agent_scanned_posts` table:

```sql
ALTER TABLE agent_scanned_posts ADD COLUMN agent_model VARCHAR(64);
ALTER TABLE agent_scanned_posts ADD COLUMN prompt_tokens INTEGER DEFAULT 0;
ALTER TABLE agent_scanned_posts ADD COLUMN completion_tokens INTEGER DEFAULT 0;
ALTER TABLE agent_scanned_posts ADD COLUMN total_cost_usd NUMERIC(10, 4) DEFAULT 0;
```

### 1.2 Update SQLAlchemy Model
Update `app/db/models.py` (~line 556):

```python
class AgentScannedPost(Base):
    """Tracks posts scanned by the Clouvel promoter agent"""
    
    __tablename__ = "agent_scanned_posts"
    # ... existing columns ...
    agent_ratings = Column(JSON, nullable=True)
    
    # New usage tracking columns
    agent_model = Column(String(64), nullable=True)
    prompt_tokens = Column(Integer, default=0)
    completion_tokens = Column(Integer, default=0)
    total_cost_usd = Column(Numeric(10, 4), default=0)
```

### 1.3 Create Alembic Migration
```bash
alembic revision -m "Add usage tracking columns to agent_scanned_posts"
```

Migration file content:
```python
def upgrade():
    op.add_column('agent_scanned_posts', 
        sa.Column('agent_model', sa.String(64), nullable=True))
    op.add_column('agent_scanned_posts', 
        sa.Column('prompt_tokens', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('agent_scanned_posts', 
        sa.Column('completion_tokens', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('agent_scanned_posts', 
        sa.Column('total_cost_usd', sa.Numeric(10, 4), nullable=False, server_default='0'))

def downgrade():
    op.drop_column('agent_scanned_posts', 'total_cost_usd')
    op.drop_column('agent_scanned_posts', 'completion_tokens')
    op.drop_column('agent_scanned_posts', 'prompt_tokens')
    op.drop_column('agent_scanned_posts', 'agent_model')
```

## Phase 2: Commission Tasks (Pipeline Runs)

### 2.1 Add Usage Tracker Helper Method
Add to `app/utils/openai_usage_tracker.py`:

```python
def get_pipeline_usage_summary(self) -> Dict[str, Any]:
    """Get aggregated usage for current pipeline run.
    
    Returns:
        Dictionary with prompt_tokens, completion_tokens, image_tokens, total_cost_usd
    """
    prompt_tokens = 0
    completion_tokens = 0
    image_tokens = 0
    total_cost = 0.0
    
    for usage in self.usage_history:
        if usage.success:
            if usage.operation == "chat":
                # Estimate token split (80% prompt, 20% completion)
                prompt_tokens += int(usage.tokens_used * 0.8)
                completion_tokens += int(usage.tokens_used * 0.2)
            elif usage.operation == "image":
                image_tokens += 1  # Count number of images
            total_cost += usage.cost_usd
    
    return {
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "image_tokens": image_tokens,
        "total_cost_usd": total_cost
    }
```

### 2.2 Modify Commission Worker
Update `app/commission_worker.py`:

1. After creating pipeline_run (~line 544):
```python
# Create pipeline run
pipeline_run = PipelineRun(
    status="completed",
    summary=f"Commission for donation {donation.id}",
    config={"commission": True, "donation_id": donation.id},
    start_time=datetime.now(),
    end_time=datetime.now(),
)
session.add(pipeline_run)
session.commit()

# Create empty usage record
usage_record = PipelineRunUsage(
    pipeline_run_id=pipeline_run.id,
    idea_model=os.getenv("OPENAI_IDEA_MODEL", "gpt-4"),
    image_model="dall-e-3",
    prompt_tokens=0,
    completion_tokens=0,
    image_tokens=0,
    total_cost_usd=0.0
)
session.add(usage_record)
session.commit()
```

2. After product generation is complete (before final return):
```python
# Update usage record with actual usage
from app.utils.openai_usage_tracker import get_usage_tracker

usage_summary = get_usage_tracker().get_pipeline_usage_summary()
usage_record.prompt_tokens = usage_summary["prompt_tokens"]
usage_record.completion_tokens = usage_summary["completion_tokens"]
usage_record.image_tokens = usage_summary["image_tokens"]
usage_record.total_cost_usd = usage_summary["total_cost_usd"]
session.commit()

logger.info(f"Pipeline run {pipeline_run.id} usage - Tokens: {usage_record.prompt_tokens + usage_record.completion_tokens}, Cost: ${usage_record.total_cost_usd:.4f}")
```

## Phase 3: Promotion Agent Updates

### 3.1 Add Tracking Decorators
Update `app/agents/clouvel_promoter_agent.py`:

1. For post analysis (~line 356):
```python
@track_openai_call(model=os.getenv("OPENAI_COMMUNITY_AGENT_MODEL", "gpt-4o-mini"), operation="chat")
def _analyze_post():
    response = self.openai.chat.completions.create(
        model=os.getenv("OPENAI_COMMUNITY_AGENT_MODEL", "gpt-4o-mini"),
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"}
    )
    return response

response = _analyze_post()
```

2. For comment generation (~line 465):
```python
@track_openai_call(model=os.getenv("OPENAI_COMMUNITY_AGENT_MODEL", "gpt-4o-mini"), operation="chat")
def _generate_comment():
    response = self.openai.chat.completions.create(
        model=os.getenv("OPENAI_COMMUNITY_AGENT_MODEL", "gpt-4o-mini"),
        messages=[{"role": "user", "content": prompt}]
    )
    return response

response = _generate_comment()
```

### 3.2 Update AgentScannedPost Creation
Update the record creation in `app/agents/clouvel_promoter_agent.py` (~line 207):

```python
from app.utils.openai_usage_tracker import get_usage_tracker

# Get usage from the last API call
usage_tracker = get_usage_tracker()
usage_history = usage_tracker.usage_history
last_call = usage_history[-1] if usage_history else None

# Calculate tokens from response if available
completion_tokens = 0
if hasattr(response, 'usage') and response.usage:
    completion_tokens = response.usage.completion_tokens

scanned_post = AgentScannedPost(
    post_id=post_id,
    subreddit=submission.subreddit.display_name,
    comment_id=comment.id if comment else None,
    promoted=promoted,
    dry_run=dry_run,
    post_title=submission.title[:500],
    post_score=submission.score,
    promotion_message=promotion_message,
    rejection_reason=rejection_reason,
    agent_ratings=agent_ratings,
    # New usage fields
    agent_model=os.getenv("OPENAI_COMMUNITY_AGENT_MODEL", "gpt-4o-mini"),
    prompt_tokens=last_call.tokens_used - completion_tokens if last_call else 0,
    completion_tokens=completion_tokens,
    total_cost_usd=last_call.cost_usd if last_call else 0.0
)
session.add(scanned_post)
session.commit()
```

## Phase 4: Schema Updates

### 4.1 Update Pydantic Schema
Update `app/models.py` to include new fields in AgentScannedPostSchema:

```python
class AgentScannedPostSchema(BaseModel):
    # ... existing fields ...
    agent_ratings: Optional[dict] = None
    
    # New usage fields
    agent_model: Optional[str] = None
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_cost_usd: float = 0.0
    
    class Config:
        from_attributes = True
```

## Phase 5: Testing

### 5.1 Test Commission Usage Tracking
```python
# Run a commission task
# Check database: SELECT * FROM pipeline_run_usages WHERE pipeline_run_id = ?;
# Verify tokens and costs are recorded
```

### 5.2 Test Promotion Agent Usage Tracking
```python
# Run promotion agent
# Check database: SELECT agent_model, prompt_tokens, completion_tokens, total_cost_usd FROM agent_scanned_posts ORDER BY scanned_at DESC LIMIT 5;
# Verify usage data is recorded
```

## Phase 6: Monitoring and Reporting

### 6.1 Add Usage API Endpoints
Add to `app/api.py`:

```python
@app.get("/api/usage/summary")
async def get_usage_summary(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: Session = Depends(get_db)
):
    """Get aggregated usage statistics."""
    # Query PipelineRunUsage and AgentScannedPost tables
    # Return aggregated costs, token counts by model
```

### 6.2 Add Usage Monitoring Commands
Add to Makefile:

```makefile
check-usage:
	@echo "=== OpenAI Usage Summary ==="
	@sqlite3 data/zazzle_pipeline.db "SELECT SUM(total_cost_usd) as total_cost, SUM(prompt_tokens + completion_tokens) as total_tokens FROM pipeline_run_usages;"
	@sqlite3 data/zazzle_pipeline.db "SELECT agent_model, COUNT(*) as calls, SUM(total_cost_usd) as cost FROM agent_scanned_posts WHERE agent_model IS NOT NULL GROUP BY agent_model;"
```

## Implementation Timeline

1. **Day 1**: Database migration and schema updates
2. **Day 2**: Commission task usage tracking
3. **Day 3**: Promotion agent usage tracking
4. **Day 4**: Testing and monitoring setup

## Benefits

- **Cost Visibility**: Track OpenAI API costs per pipeline run and agent activity
- **Usage Analytics**: Understand token usage patterns for optimization
- **Budget Management**: Monitor and control API spending
- **Performance Tracking**: Correlate usage with performance metrics
- **Audit Trail**: Complete record of AI usage for compliance

## Notes

- The implementation uses existing OpenAI usage tracker infrastructure
- No performance impact as tracking happens asynchronously
- Backward compatible with existing data (NULL values for historical records)
- Can be extended to track other agents by following the same pattern