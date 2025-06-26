# Clouvel Commission System - Execution Plan
*June 26, 2024*

## Overview
Transform the Zazzle Agent from a random subreddit generator to a commission-based AI artist system where Clouvel generates content in response to user donations and sponsored requests.

## Phase 1: Core Functionality (Minimal Refactor)

### 1.1 Sponsor Tiers & Supporter Experience
- [ ] **Database Schema Changes**
  - [ ] Create `sponsor_tiers` table (id, name, min_amount, benefits, description) - **Individual donor levels**
  - [ ] Create `sponsors` table (id, donation_id, tier_id, subreddit, status, created_at) - **Individual sponsors**
  - [ ] Create `sponsor_tier_benefits` table (id, tier_id, benefit_type, benefit_value) - **Benefits for individual sponsors**
  - [ ] Create `subreddit_tiers` table (id, subreddit, tier_level, min_total_donation, status) - **Community fundraising levels**
  - [ ] Create `subreddit_fundraising_goals` table (id, subreddit, goal_amount, current_amount, deadline) - **Community goals**
  - [ ] Add Alembic migration for new tables
  - [ ] Update existing donation flow to create sponsor records

- [ ] **API Endpoints**
  - [ ] `GET /api/sponsor-tiers` - List available individual sponsor tiers
  - [ ] `GET /api/subreddit-tiers` - List subreddit community tiers
  - [ ] `POST /api/sponsors` - Create sponsor record from donation
  - [ ] `GET /api/sponsors` - List current sponsors (for "donor wall")
  - [ ] `GET /api/subreddit-fundraising` - Get subreddit fundraising status
  - [ ] Update donation webhook to create sponsor records

- [ ] **Frontend Components**
  - [ ] Add sponsor tiers display to donation modal (individual levels)
  - [ ] Create "Supporter Wall" component showing current sponsors
  - [ ] Create "Subreddit Leaderboard" showing community fundraising progress
  - [ ] Update donation flow to associate with sponsor tiers
  - [ ] Add sponsor tier selection UI
  - [ ] Display subreddit tier status and progress

### 1.2 Task Queue System (Database-Driven)
- [ ] **Database Schema Changes**
  - [ ] Create `pipeline_tasks` table (id, type, subreddit, sponsor_id, status, priority, created_at, scheduled_for, completed_at)
  - [ ] Create `task_types` enum ('SPONSORED_POST', 'FRONT_PICK', 'CROSS_POST', 'SUBREDDIT_TIER_POST')
  - [ ] Add Alembic migration for task queue tables

- [ ] **Core Logic Implementation**
  - [ ] Create `TaskQueue` class in `app/task_queue.py`
  - [ ] Implement `add_task()`, `get_next_task()`, `mark_completed()` methods
  - [ ] Add task priority and scheduling logic
  - [ ] Modify `run_full_pipeline()` to check task queue first, fallback to random
  - [ ] Add logic to create tasks when subreddit tiers are reached

- [ ] **API Endpoints**
  - [ ] `GET /api/tasks` - List upcoming tasks
  - [ ] `POST /api/tasks` - Add new sponsored task
  - [ ] `GET /api/tasks/queue` - Show current queue status
  - [ ] `PUT /api/tasks/{id}/status` - Update task status

### 1.3 Event-Driven Pipeline
- [ ] **New Pipeline Method**
  - [ ] Create `run_task_pipeline(task_id)` in `app/pipeline.py`
  - [ ] Keep existing `run_full_pipeline()` unchanged
  - [ ] Add task queue integration to main pipeline runner
  - [ ] Implement task-specific pipeline configuration

- [ ] **Task Runner Service**
  - [ ] Create `app/task_runner.py` with async task processor
  - [ ] Add to docker-compose as new service
  - [ ] Process tasks every 5 minutes, prioritize sponsored tasks
  - [ ] Add task runner health monitoring

### 1.4 Subreddit Tier System
- [ ] **Database Schema Changes**
  - [ ] Create `subreddit_tiers` table (id, subreddit, tier_level, min_total_donation, status) - **Community levels**
  - [ ] Create `subreddit_fundraising_goals` table (id, subreddit, goal_amount, current_amount, deadline) - **Community goals**
  - [ ] Add Alembic migration for subreddit tier tables

- [ ] **Logic Implementation**
  - [ ] Implement tier-based subreddit selection (community fundraising levels)
  - [ ] Add fundraising goal tracking per subreddit
  - [ ] Create subreddit competition leaderboard
  - [ ] Add subreddit tier validation
  - [ ] Implement automatic task creation when subreddit tiers are reached
  - [ ] Track individual sponsors vs community progress separately

## Phase 2: Clouvel Identity & Interaction

### 2.1 Dedicated Subreddit Setup
- [ ] **Configuration Updates**
  - [ ] Add `/r/clouvel` to subreddit configuration
  - [ ] Update interaction agent to prioritize clouvel subreddit
  - [ ] Implement cross-posting logic for sponsored content
  - [ ] Configure clouvel-specific posting rules

- [ ] **Content Strategy**
  - [ ] Create clouvel introduction posts
  - [ ] Implement commission announcement format
  - [ ] Add signature style to generated content
  - [ ] Create clouvel personality guidelines

### 2.2 Enhanced Interaction Agent
- [ ] **Cross-Posting Features**
  - [ ] Cross-post sponsored content to clouvel subreddit
  - [ ] Reply to comments with clouvel personality
  - [ ] Track engagement metrics per sponsored post
  - [ ] Implement commission completion announcements

- [ ] **Interaction Improvements**
  - [ ] Add clouvel signature to all interactions
  - [ ] Implement commission status updates
  - [ ] Add engagement tracking for sponsored posts
  - [ ] Create interaction templates for different scenarios

## Phase 3: Commission System

### 3.1 Commission Workflow
- [ ] **Database Schema Changes**
  - [ ] Create `commissions` table (id, sponsor_id, subreddit, description, status, budget, created_at)
  - [ ] Create `commission_status` enum ('PENDING', 'IN_PROGRESS', 'COMPLETED', 'FAILED')
  - [ ] Add Alembic migration for commission tables

- [ ] **Commission Logic**
  - [ ] Convert donations to commission credits ($5 = 1 commission)
  - [ ] Implement commission queue processing
  - [ ] Add commission completion tracking
  - [ ] Create commission validation rules
  - [ ] Link commissions to both individual sponsors and subreddit tiers

### 3.2 UI Enhancements
- [ ] **Frontend Components**
  - [ ] Commission queue display
  - [ ] Sponsor leaderboard (individual donors)
  - [ ] Subreddit fundraising goals (community progress)
  - [ ] Clouvel's current work status
  - [ ] Commission history and gallery

- [ ] **Dashboard Features**
  - [ ] Real-time commission status
  - [ ] Sponsor tier benefits display (individual levels)
  - [ ] Subreddit tier status display (community levels)
  - [ ] Subreddit competition leaderboard
  - [ ] Commission progress tracking

## Phase 4: Deployment & Go-Live

### 4.1 Infrastructure Setup
- [ ] **GitHub Secrets Configuration**
  - [ ] `STRIPE_SECRET_KEY` (live)
  - [ ] `STRIPE_WEBHOOK_SECRET` (live)
  - [ ] `REDDIT_CLIENT_ID` (production)
  - [ ] `REDDIT_CLIENT_SECRET` (production)
  - [ ] `OPENAI_API_KEY` (production)
  - [ ] `ZAZZLE_AFFILIATE_ID` (production)
  - [ ] `IMGUR_CLIENT_ID` (production)

### 4.2 Domain & Hosting
- [ ] **Domain Registration**
  - [ ] Purchase domain (clouvel.art recommended)
  - [ ] Configure DNS settings
  - [ ] Set up SSL certificates

- [ ] **Hosting Platform Selection**
  - [ ] Choose hosting platform (Railway/Render recommended)
  - [ ] Configure production environment
  - [ ] Set up CI/CD pipeline
  - [ ] Configure environment variables

### 4.3 Stripe Production
- [ ] **Production Configuration**
  - [ ] Switch to live Stripe keys
  - [ ] Configure webhook endpoints
  - [ ] Set up proper error handling
  - [ ] Test payment flows

- [ ] **Compliance Setup**
  - [ ] Add privacy policy
  - [ ] Add terms of service
  - [ ] Configure tax settings
  - [ ] Set up refund policies

### 4.4 Final Deployment
- [ ] **Pre-deployment Checklist**
  - [ ] Run full test suite
  - [ ] Database migration to production
  - [ ] Environment variable configuration
  - [ ] Health check validation
  - [ ] Load testing

- [ ] **Go-live Steps**
  - [ ] Deploy to production
  - [ ] Monitor initial pipeline runs
  - [ ] Verify payment processing
  - [ ] Test commission workflow
  - [ ] Monitor error logs

## Phase 5: Critical Additions

### 5.1 Essential Features
- [ ] **Rate Limiting**
  - [ ] Implement API rate limits for commission submissions
  - [ ] Add rate limiting for donation submissions
  - [ ] Configure rate limiting for Reddit interactions

- [ ] **Error Recovery**
  - [ ] Robust error handling for failed commissions
  - [ ] Automatic retry logic for failed tasks
  - [ ] Error notification system

- [ ] **Monitoring & Analytics**
  - [ ] Add commission success/failure metrics
  - [ ] Implement performance monitoring
  - [ ] Create dashboard for key metrics

### 5.2 Security & Compliance
- [ ] **Security Measures**
  - [ ] Input validation for commission descriptions
  - [ ] SQL injection prevention
  - [ ] XSS protection
  - [ ] CSRF protection

- [ ] **Legal Requirements**
  - [ ] Terms of Service for commissions
  - [ ] Privacy Policy for sponsors
  - [ ] Content Guidelines
  - [ ] Refund Policy

### 5.3 Backup & Recovery
- [ ] **Backup Strategy**
  - [ ] Automated database backups
  - [ ] Configuration backup
  - [ ] Disaster recovery plan
  - [ ] Data retention policies

## Implementation Timeline

### Week 1: Foundation
- [ ] Complete Phase 1.1 (Sponsor Tiers)
- [ ] Complete Phase 1.2 (Task Queue System)
- [ ] Database migrations and testing

### Week 2: Core Logic
- [ ] Complete Phase 1.3 (Event-Driven Pipeline)
- [ ] Complete Phase 1.4 (Subreddit Tier System)
- [ ] Integration testing

### Week 3: Clouvel Identity
- [ ] Complete Phase 2.1 (Dedicated Subreddit)
- [ ] Complete Phase 2.2 (Enhanced Interaction)
- [ ] Content strategy implementation

### Week 4: Commission System
- [ ] Complete Phase 3.1 (Commission Workflow)
- [ ] Complete Phase 3.2 (UI Enhancements)
- [ ] End-to-end testing

### Week 5: Production
- [ ] Complete Phase 4 (Deployment & Go-Live)
- [ ] Complete Phase 5 (Critical Additions)
- [ ] Production monitoring and optimization

## Risk Mitigation

### Technical Risks
- [ ] **Minimal Refactor Approach**
  - [ ] Keep existing pipeline intact
  - [ ] Add new paths without breaking existing functionality
  - [ ] Use feature flags for gradual rollout

- [ ] **Database Safety**
  - [ ] Use Alembic for safe schema changes
  - [ ] Backup before each migration
  - [ ] Test migrations on staging environment

- [ ] **Rollback Strategy**
  - [ ] Maintain ability to revert to current system
  - [ ] Database rollback procedures
  - [ ] Feature flag rollback mechanisms

### Business Risks
- [ ] **Content Moderation**
  - [ ] Implement content guidelines
  - [ ] Add content filtering
  - [ ] Create reporting mechanisms

- [ ] **Payment Security**
  - [ ] PCI compliance verification
  - [ ] Secure payment processing
  - [ ] Fraud detection measures

## Success Metrics

### Technical Metrics
- [ ] Pipeline success rate > 95%
- [ ] Task queue processing time < 5 minutes
- [ ] API response time < 200ms
- [ ] Database query performance optimization

### Business Metrics
- [ ] Commission completion rate
- [ ] Sponsor retention rate
- [ ] Subreddit engagement metrics
- [ ] Revenue per commission

## Notes

- **Priority**: Focus on minimal refactoring to maintain stability
- **Testing**: Comprehensive testing at each phase
- **Documentation**: Update documentation as features are implemented
- **Monitoring**: Implement monitoring from day one of production
- **Tier Distinction**: 
  - **Sponsor Tiers**: Individual donor levels (Bronze, Silver, Gold, etc.)
  - **Subreddit Tiers**: Community fundraising levels (many sponsors contribute to reach community goals)

---

*This plan will be updated as implementation progresses and new requirements are identified.* 