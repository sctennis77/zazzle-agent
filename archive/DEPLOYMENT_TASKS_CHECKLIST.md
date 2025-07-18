# Zazzle Agent Deployment Tasks Checklist

## Steps YOU Must Take Care Of

- [ ] **Fill out your `.env` file** with all production secrets and API keys (OpenAI, Reddit, Stripe, Imgur, Zazzle, etc.)
- [ ] **Switch Stripe keys and webhook endpoints** from test to production in both `.env` and the Stripe dashboard
- [ ] **Update GitHub/CI/CD secrets** with production values (if deploying to cloud)
- [ ] **Rotate any old or compromised secrets** before launch
- [ ] **Set up Stripe webhooks** in the Stripe dashboard for your production domain
- [ ] **Verify Stripe account is in live mode** and all business/bank details are correct
- [ ] **Backup any important data** in the current database before deploying
- [ ] **Migrate/seed the production database** if needed
- [ ] **Update K8s secrets/configmaps** with production values (if deploying to K8s)
- [ ] **Apply K8s manifests** to your production cluster (requires your kubeconfig/cloud access)
- [ ] **Configure your DNS** to point to your production server/cluster
- [ ] **Set up HTTPS/TLS certificates** (e.g., via Let’s Encrypt, Cloudflare, or your cloud provider)
- [ ] **Set up external monitoring/alerting** (e.g., UptimeRobot, Datadog, Sentry, etc.)
- [ ] **Document and test your incident response plan** (rotating secrets, restoring from backup, etc.)

---

## Steps AI Can Take Care Of (or Automate for You)

- [ ] Build and deploy the Docker stack locally (`make deploy`)
- [ ] Run all health checks and verify service status
- [ ] Update and maintain all deployment documentation and checklists
- [ ] Automate log monitoring and error reporting scripts (if you want)
- [ ] Automate database backup scripts (local only, unless you provide cloud credentials)
- [ ] Automate dependency updates and security checks (e.g., Dependabot, poetry update)
- [ ] Automate local test runs and commission flow tests
- [ ] Update K8s manifests and Dockerfiles for best practices (but you must apply them to your cluster)

---

## Summary Table

| Step                                      | You Must Do | AI Can Do/Automate |
|--------------------------------------------|:-----------:|:------------------:|
| Fill out .env with production secrets      |      ✅      |         ❌         |
| Switch Stripe keys/webhooks to production  |      ✅      |         ❌         |
| Update GitHub/CI/CD secrets                |      ✅      |         ❌         |
| Backup/migrate production database         |      ✅      |         ❌         |
| Apply K8s manifests/secrets in prod        |      ✅      |         ❌         |
| Configure DNS and HTTPS/TLS                |      ✅      |         ❌         |
| Set up external monitoring/alerting        |      ✅      |         ❌         |
| Document/test incident response plan       |      ✅      |         ❌         |
| Build/deploy Docker stack locally          |      ❌      |         ✅         |
| Run health checks and verify services      |      ❌      |         ✅         |
| Update deployment docs/checklists          |      ❌      |         ✅         |
| Automate log/error monitoring scripts      |      ❌      |         ✅         |
| Automate local DB backup scripts           |      ❌      |         ✅         |
| Automate dependency/security updates       |      ❌      |         ✅         |
| Automate local test runs                   |      ❌      |         ✅         |
| Update K8s manifests/Dockerfiles           |      ❌      |         ✅         |

---

**Review this checklist before production launch. If you want any of the AI-automatable steps scripted or handled, just ask!** 