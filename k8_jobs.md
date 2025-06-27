# Implementation Plan: K8s Jobs API with Real-Time WebSocket Status Updates

## 1. Preparation & Dependencies
- **Review current task runner logic** (where/how tasks are triggered).
- **Add dependencies:**
  - `kubernetes` Python client (for Job management)
  - `fastapi[websockets]` (for WebSocket support)
  - (Optional) `redis` or in-memory pub/sub for multi-instance coordination

---

## 2. K8s Job Template & Utility
- **Create a Job spec template** (YAML or Python dict) for your task runner.
- **Implement a Python utility** to:
  - Generate a unique Job name (e.g., `task-runner-{pipeline_run_id}-{uuid}`)
  - Fill in the Job spec (image, env vars, etc.)
  - Submit the Job to the cluster using the Kubernetes API
  - Return the Job name for tracking

---

## 3. Feature Flag & Config
- Add a config/env variable (e.g., `USE_K8S_JOBS`) to toggle between legacy and K8s Job execution.
- Optionally, allow both to run for side-by-side testing.

---

## 4. Task Trigger Logic
- Update the backend so that, on donation submission:
  - If `USE_K8S_JOBS` is enabled, launch a K8s Job and return the Job name/ID.
  - Otherwise, use the legacy method.
  - Optionally, trigger both for migration/testing.

---

## 5. Job Status Tracking API
- **Implement a REST endpoint** (e.g., `/api/task-status?job_name=...`) that:
  - Queries the K8s API for Job status (`Active`, `Succeeded`, `Failed`, etc.)
  - Returns a normalized status for the frontend

---

## 6. WebSocket Real-Time Status Updates
- **Add a WebSocket endpoint** (e.g., `/ws/task-status/{job_name}`) using FastAPI.
- On client connect:
  - Start a background task to watch the Job status (using K8s watch API or polling)
  - Push status updates to the client in real time (e.g., `{"status": "Running"}`, `{"status": "Succeeded"}`)
  - Optionally, close the connection when the Job completes or fails
- (Optional) Use Redis pub/sub if you have multiple backend instances, to coordinate status updates.

---

## 7. Frontend Integration
- **Add a WebSocket client** to the frontend:
  - Connect to `/ws/task-status/{job_name}` after task submission
  - Update the UI dynamically as status messages are received
  - Fallback to polling the REST endpoint if WebSocket is unavailable

---

## 8. Logging, Monitoring, and Error Handling
- Log all Job creation, status changes, and errors.
- Handle edge cases (e.g., Job not found, K8s API errors, network issues).
- Optionally, expose Job logs via an API for debugging.

---

## 9. Documentation
- Document both execution modes, Job spec, and WebSocket usage.
- Provide example API/WebSocket calls and expected responses.

---

## 10. Rollout & Migration
- **Phase 1:** Implement and test in dev/staging.
- **Phase 2:** Enable dual execution in production (feature flag).
- **Phase 3:** Monitor, compare, and validate.
- **Phase 4:** Migrate fully to K8s Jobs + WebSockets when ready.

---

## Example: FastAPI WebSocket Endpoint

```python
from fastapi import WebSocket, APIRouter
from kubernetes import client, config
import asyncio

router = APIRouter()

@router.websocket("/ws/task-status/{job_name}")
async def task_status_ws(websocket: WebSocket, job_name: str, namespace: str = "default"):
    await websocket.accept()
    config.load_kube_config()  # or load_incluster_config()
    batch_v1 = client.BatchV1Api()
    while True:
        job = batch_v1.read_namespaced_job(name=job_name, namespace=namespace)
        status = job.status
        if status.succeeded:
            await websocket.send_json({"status": "Succeeded"})
            break
        elif status.failed:
            await websocket.send_json({"status": "Failed"})
            break
        elif status.active:
            await websocket.send_json({"status": "Running"})
        else:
            await websocket.send_json({"status": "Pending"})
        await asyncio.sleep(2)
    await websocket.close()
```

---

## Key Best Practices
- **Unique Job names** for traceability.
- **Configurable execution mode** for easy migration/rollback.
- **Robust error handling** and logging.
- **WebSocket fallback** to polling for reliability.
- **Documentation** for future maintainers. 