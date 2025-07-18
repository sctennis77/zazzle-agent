# Redis Pub/Sub Integration for Real-Time Updates

This document describes the Redis pub/sub integration that enables real-time task status updates across multiple services in the Zazzle Agent system.

## Overview

The Redis pub/sub integration replaces direct WebSocket broadcasting with a centralized message broker, enabling:

- **Cross-service communication**: Updates from any service (API, pipeline, commission workers) are broadcast to all connected WebSocket clients
- **Scalability**: Multiple API instances can share the same Redis instance
- **Reliability**: Messages are persisted in Redis and delivered to all subscribers
- **Real-time updates**: Task progress updates are delivered instantly to frontend clients

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Commission    │    │   Pipeline      │    │   Task Manager  │
│     Worker      │    │    Worker       │    │                 │
└─────────┬───────┘    └─────────┬───────┘    └─────────┬───────┘
          │                      │                      │
          │                      │                      │
          └──────────────────────┼──────────────────────┘
                                 │
                    ┌─────────────▼─────────────┐
                    │         Redis             │
                    │      (Pub/Sub)            │
                    └─────────────┬─────────────┘
                                 │
                    ┌─────────────▼─────────────┐
                    │   WebSocket Manager       │
                    │   (Redis Subscriber)      │
                    └─────────────┬─────────────┘
                                 │
                    ┌─────────────▼─────────────┐
                    │   Frontend Clients        │
                    │   (WebSocket)             │
                    └───────────────────────────┘
```

## Components

### 1. Redis Service (`app/redis_service.py`)

The core Redis service that handles:
- Connection management
- Publishing messages to channels
- Subscribing to channels
- Message handling and routing

**Key Methods:**
- `publish_task_update(task_id, update)`: Publishes task updates to Redis
- `publish_general_update(update)`: Publishes general updates to Redis
- `subscribe_to_channel(channel, callback)`: Subscribes to a Redis channel
- `start_listening()`: Starts the Redis listener

### 2. WebSocket Manager (`app/websocket_manager.py`)

Enhanced WebSocket manager that:
- Subscribes to Redis channels
- Forwards Redis messages to WebSocket clients
- Maintains WebSocket connections
- Handles client subscriptions to specific tasks

**Key Changes:**
- Added Redis integration on startup/shutdown
- Publishes updates to Redis instead of directly broadcasting
- Listens to Redis channels and forwards messages to WebSocket clients

### 3. Task Manager (`app/task_manager.py`)

Updated to publish task updates to Redis instead of directly calling WebSocket manager.

### 4. Commission Worker (`app/commission_worker.py`)

Updated to publish task updates to Redis for cross-service communication.

## Configuration

### Environment Variables

Add these to your `.env` file:

```bash
# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=
REDIS_SSL=false
```

### Docker Compose

Redis service is automatically included in `docker-compose.yml`:

```yaml
redis:
  image: redis:7-alpine
  ports:
    - "6379:6379"
  restart: unless-stopped
  healthcheck:
    test: ["CMD", "redis-cli", "ping"]
    interval: 30s
    timeout: 10s
    retries: 3
```

### Kubernetes

Redis deployment is included in `k8s/redis-deployment.yaml` and all services are configured with Redis environment variables.

## Usage

### Publishing Updates

**Task Updates:**
```python
from app.redis_service import redis_service

await redis_service.publish_task_update("task-123", {
    "status": "in_progress",
    "message": "Processing commission...",
    "progress": 50
})
```

**General Updates:**
```python
await redis_service.publish_general_update({
    "type": "system_notification",
    "message": "System maintenance scheduled"
})
```

### Subscribing to Updates

```python
from app.redis_service import redis_service

def on_task_update(message):
    print(f"Task update: {message}")

redis_service.subscribe_to_channel("task_updates", on_task_update)
await redis_service.start_listening()
```

## Testing

### Test Redis Pub/Sub

```bash
# Test Redis functionality
make test-redis

# Check Redis status
make redis-status

# Connect to Redis CLI
make redis-cli

# View Redis logs
make redis-logs
```

### Manual Testing

1. Start the application with Redis:
   ```bash
   make docker-run-local
   ```

2. Create a commission task through the frontend

3. Monitor Redis messages:
   ```bash
   make redis-cli
   # In Redis CLI:
   SUBSCRIBE task_updates
   ```

4. Watch for real-time updates in the frontend

## Troubleshooting

### Common Issues

**1. Redis Connection Failed**
```
Error: Failed to connect to Redis
```
- Check if Redis service is running: `make redis-status`
- Verify Redis host/port configuration
- Check Docker Compose logs: `make redis-logs`

**2. No WebSocket Updates**
```
Error: No task updates received
```
- Verify Redis pub/sub is working: `make test-redis`
- Check WebSocket manager logs
- Ensure API service started successfully

**3. Cross-Service Communication Issues**
```
Error: Updates not received across services
```
- Verify all services have Redis environment variables
- Check Redis connectivity from each service
- Monitor Redis pub/sub channels

### Debug Commands

```bash
# Check all services status
make health-check

# View all logs
make show-logs

# Test Redis connectivity
make redis-status

# Monitor Redis pub/sub
make redis-cli
# Then: SUBSCRIBE task_updates
```

## Performance Considerations

- **Redis Memory**: Monitor Redis memory usage, especially with high message volume
- **Connection Pooling**: Redis connections are pooled for efficiency
- **Message Size**: Keep messages small to minimize network overhead
- **Channel Management**: Use specific channels for different message types

## Security

- **Network Security**: Redis should only be accessible within the cluster/network
- **Authentication**: Consider enabling Redis authentication for production
- **SSL/TLS**: Enable SSL for Redis connections in production environments

## Monitoring

### Health Checks

The system includes health checks for:
- Redis connectivity
- WebSocket manager status
- Message delivery

### Metrics to Monitor

- Redis memory usage
- Message publish/subscribe rates
- WebSocket connection count
- Message delivery latency

## Migration from Direct WebSocket

The migration from direct WebSocket broadcasting to Redis pub/sub is transparent to the frontend. The WebSocket API remains the same, but the backend now uses Redis for cross-service communication.

### Benefits of Migration

1. **Scalability**: Multiple API instances can share updates
2. **Reliability**: Messages are persisted in Redis
3. **Decoupling**: Services don't need direct WebSocket manager access
4. **Monitoring**: Better visibility into message flow
5. **Debugging**: Easier to trace message delivery issues 