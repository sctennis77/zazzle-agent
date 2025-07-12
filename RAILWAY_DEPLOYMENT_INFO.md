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

## Key Takeaways & Step-by-Step Deployment (Backend & Frontend)

### Key Takeaways
- **Dockerfile Naming:** Always name your Dockerfile exactly `Dockerfile` in the root of each service directory for Railway to auto-detect it.
- **Environment Variables:** Use Railway's shared variables for all secrets and config, and share only the necessary variables with each service (API, frontend, etc.).
- **Frontend API URL:** Set `VITE_API_BASE_URL` (or similar) to the public Railway backend URL for production. Switch to your custom domain after DNS is set up.
- **Public Networking:** Enable public networking for your backend API to get a public `.railway.app` URL.
- **Separate Services:** Deploy backend and frontend as separate Railway services, each with their own root directory and Dockerfile.
- **No Nginx Proxy by Default:** Nginx in the frontend Dockerfile serves static files only; API requests go directly to the backend public URL unless you add a proxy rule.
- **GitHub Integration:** Connect your Railway services to your GitHub repo for automatic deploys on push.
- **Debugging:** Always check Railway build and runtime logs for errors. Most issues are due to misnamed Dockerfiles, missing env vars, or networking config.

### Step-by-Step Deployment Instructions

#### Backend API Service
1. **Dockerfile:** Ensure `Dockerfile` is in the project root and is correct.
2. **railway.json:** Clean up and remove `dockerfilePath` if using the default name.
3. **Environment Variables:** Add all required variables to Railway shared variables and share with the backend service.
4. **Public Networking:** Click "Generate Domain" in the backend service's Networking settings to get a public URL.
5. **Deploy:** Push to GitHub or click Deploy in Railway UI. Monitor logs for success.
6. **API URL:** Use the public Railway URL for frontend API calls until DNS is set up.

#### Frontend Service
1. **Dockerfile:** Ensure `frontend/Dockerfile` exists and is correct.
2. **Root Directory:** Set to `/frontend` in Railway service settings.
3. **Environment Variables:** Share only required `VITE_` variables (e.g., `VITE_STRIPE_PUBLISHABLE_KEY`, `VITE_API_BASE_URL`) with the frontend service.
4. **API URL:** Set `VITE_API_BASE_URL` to the backend's public Railway URL.
5. **Deploy:** Push to GitHub or click Deploy in Railway UI. Monitor logs for success.
6. **Switch to Custom Domain:** After DNS is set up, update `VITE_API_BASE_URL` to your custom domain and redeploy the frontend.

---

_This section summarizes the deployment workflow and best practices for deploying both backend and frontend services on Railway, as learned in this session._

_This file documents the deployment and environment variable setup for the backend API service on Railway._ 