# Zazzle Agent Production Deployment Guide (2025)

## Overview
This guide describes the streamlined, production-like deployment process for Zazzle Agent using Docker Compose. The stack now consists of only the essential services:
- **API** (FastAPI, runs commission tasks as threads locally)
- **Frontend** (React/Vite)
- **Redis** (for real-time updates)
- **Database** (SQLite, persistent volume)
- **Stripe CLI** (for local webhook testing)

**Note:** There is no longer a long-running pipeline or commission worker container. All commission and pipeline tasks are handled as threads in the API (locally) or as Kubernetes jobs in production.

---

## Prerequisites
- Docker and Docker Compose installed and running
- `.env` file present in the project root (see `.env.example` for required variables)
- All required API keys and secrets set in `.env`

---

## Local Production-like Deployment (Docker Compose)

1. **Stop any existing services**
   ```sh
   make stop-api
   pkill -f "npm run dev" || true
   docker-compose down --remove-orphans
   pkill redis-server || true
   ```

2. **Setup environment (if not already done)**
   ```sh
   make setup-prod
   # Edit .env with your real secrets if needed
   ```

3. **Deploy the stack**
   ```sh
   make deploy
   ```
   This will:
   - Build all Docker images
   - Start all services
   - Wait for health checks
   - Run DB migrations
   - Test API and frontend health

4. **Verify services**
   - Frontend: http://localhost:5173
   - API: http://localhost:8000
   - API Docs: http://localhost:8000/docs
   - Redis: localhost:6379

5. **Useful commands**
   - View logs: `docker-compose logs -f`
   - View API logs: `docker-compose logs -f api`
   - Stop services: `docker-compose down`
   - Restart services: `docker-compose restart`
   - Run pipeline manually: `docker-compose exec api python -m app.main --mode full`

---

## Best Practices
- **No task-runner container:** All commission/pipeline tasks run as threads in the API locally, or as K8s jobs in production.
- **Keep .env up to date:** Always use real secrets for production.
- **Use `make deploy` for local prod-like testing.**
- **Keep Docker images up to date:** Rebuild with `make deploy-clean` if needed.
- **Update requirements.txt after changing Python deps:**
  ```sh
  poetry add <package>
  make export-requirements
  ```

---

## Administrative & Pre-Deployment Checklist

### Environment & Secrets
- [ ] All required secrets in `.env` (see `.env.example`)
- [ ] Stripe keys set to production values
- [ ] OpenAI, Reddit, Imgur, Zazzle keys set to production values
- [ ] GitHub secrets configured for CI/CD (if deploying to cloud)

### Database
- [ ] Backup existing database (`make backup-db`)
- [ ] Migrate/seed database as needed
- [ ] Verify DB volume is persistent

### Stripe
- [ ] Switch Stripe keys from test to production
- [ ] Update webhook endpoints in Stripe dashboard if needed
- [ ] Test Stripe CLI locally if using webhooks

### Deployment
- [ ] Stop all old services (including any host Redis)
- [ ] Run `make deploy` and verify all health checks pass
- [ ] Test commission flow end-to-end (Sponsor, Random, Specific)
- [ ] Test Stripe payment and webhook flow
- [ ] Test API and frontend endpoints
- [ ] Monitor logs for errors

### Kubernetes (Production Only)
- [ ] Ensure K8s manifests are up to date (see `k8s/`)
- [ ] Set up K8s secrets/configmaps for all environment variables
- [ ] Use K8s jobs for commission/pipeline tasks
- [ ] Use persistent volumes for DB/data
- [ ] Use production-ready ingress and TLS

---

## Troubleshooting
- **Port in use:** Stop any host Redis or other services using 6379, 8000, or 5173.
- **Build errors:** Ensure all tsconfig files have `noUnusedLocals` and `noUnusedParameters` set to `false` for production builds.
- **Secrets missing:** Double-check `.env` and K8s secrets.

---

## Final Notes
- This process is now as close as possible to production, with minimal moving parts and best practices for reliability and maintainability.
- For any issues, check logs and health endpoints first. 

---

## Security Best Practices for Production Deployment

### 1. Secrets & Environment Variables
- **Never commit `.env` or secrets to version control.**
- Use a secrets manager (e.g., GitHub Actions secrets, AWS Secrets Manager, GCP Secret Manager, or K8s secrets) for production deployments.
- Rotate API keys and secrets regularly.
- Use unique, strong values for all API keys and secrets.
- Restrict access to secrets to only those who need it.

### 2. HTTPS & Network Security
- **Always use HTTPS** for all public endpoints in production (use a reverse proxy or ingress controller with TLS).
- Restrict API and database ports to internal networks only (do not expose SQLite or Redis directly to the public internet).
- Use firewalls or security groups to limit access to only trusted IPs/networks.
- For K8s, use NetworkPolicies to restrict pod-to-pod communication.

### 3. Docker & Kubernetes Hardening
- Use official, minimal base images (already done in Dockerfiles).
- Run containers as non-root users (already done for frontend, recommended for API as well).
- Set resource limits for all containers.
- Enable Docker logging and log rotation (already configured).
- Use read-only file systems for containers where possible.
- Regularly update base images and dependencies to patch vulnerabilities.
- For K8s: use PodSecurityPolicies or PodSecurity admission, and avoid privileged containers.

### 4. Database & Data Security
- Backup the database regularly and store backups securely.
- Never expose SQLite or any database port to the public internet.
- For production, consider using a managed database (e.g., PostgreSQL) with strong authentication and encryption.
- Encrypt sensitive data at rest and in transit if possible.

### 5. API & Application Security
- Validate and sanitize all user input (already handled by FastAPI/Pydantic, but review custom logic).
- Implement proper error handling and logging (no silent exceptions; log all errors with context).
- Use rate limiting (already included via fastapi-limiter).
- Enable CORS only for trusted origins.
- Keep all dependencies up to date and monitor for vulnerabilities (e.g., Dependabot, `poetry update`).
- Use strong password policies and 2FA for all admin accounts (if applicable).

### 6. Stripe & Payment Security
- Use Stripe's official libraries and webhooks only over HTTPS.
- Never log or expose full card numbers or sensitive payment data.
- Store only the minimum required payment information.
- Monitor Stripe dashboard for suspicious activity.

### 7. Monitoring & Incident Response
- Set up monitoring and alerting for all critical services (API, frontend, Redis, DB).
- Monitor logs for errors, suspicious activity, and failed login attempts.
- Have a process for rotating secrets and revoking compromised credentials.
- Regularly review access logs and audit trails.

### 8. General
- Use strong, unique passwords for all accounts and services.
- Enable 2FA everywhere possible (GitHub, cloud providers, Stripe, etc.).
- Document your incident response plan and test it periodically.
- Review and update this checklist regularly as threats and best practices evolve.

--- 