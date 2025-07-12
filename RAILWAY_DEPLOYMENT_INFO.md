# Railway Deployment Info

## Backend API Service Setup Checklist

| Setting/Variable   | Value/Source                        | Notes                        |
|--------------------|-------------------------------------|------------------------------|
| Source Repo        | sctennis77/zazzle-agent             | Already set                  |
| Root Directory     | `/`                                 | Already set                  |
| Branch             | `main`                              | Already set                  |
| DATABASE_URL       | From Postgres plugin                | Required                     |
| REDIS_URL          | From Redis plugin                   | Required                     |
| PORT               | Railway sets automatically          | App should use this          |
| API/Secret Keys    | From your .env.production           | Stripe, OpenAI, etc.         |
| Healthcheck        | `/health` endpoint                  | Recommended                  |
| Volumes            | Only if you need persistent storage | Optional                     |

---

## Environment Variable Management Best Practice

- **Source of Truth:** Always use your local `.env.production` file as the source of truth for secrets and environment variables.
- **Copy/Paste:** When updating secrets or variables, copy them from `.env.production` and paste into Railway's project shared variables.
- **Share as Needed:** Use Railway's variable sharing feature to share secrets with all services that require them (API, frontend, etc.).
- **Keep `.env.production` out of version control:** Ensure `.env.production` is in `.gitignore` and never committed to your repo.

---

_This file documents the deployment and environment variable setup for the backend API service on Railway._ 