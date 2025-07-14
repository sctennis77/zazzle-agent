# 🚀 Production Deployment Checklist for Clouvel.ai

## **YOUR TASKS (Must be done by you)**

### **Phase 1: Domain & Platform Setup (30-60 min)**
- [x] **Register clouvel.ai domain** (~$12-15/year)
  - Use Namecheap, Google Domains, or Cloudflare
  - Set up DNS records (will configure after deployment)
- [x] **Choose and set up deployment platform**:
  - **Railway** (fastest, $20-50/month) - Recommended for speed ✅
  - **DigitalOcean** (balanced, $87-157/month) - Good middle ground
  - **Google Cloud** (enterprise, $135-255/month) - Most robust
- [x] **Create platform account** and set up billing

### **Phase 2: Production Environment Setup (30-45 min)**
- [x] **Create `.env.production`** from `env.production.template`
- [x] **Fill in ALL production secrets** (do NOT commit to git):
  - Database URL (platform-specific)
  - Redis URL (platform-specific)
  - Stripe production keys (`sk_live_...`, `pk_live_...`)
  - Stripe webhook secret (`whsec_...`)
  - OpenAI API key
  - Reddit API credentials
  - Zazzle affiliate credentials
  - Email configuration (SMTP settings)
  - Security keys (SECRET_KEY, etc.)
- [x] **Upload secrets to Railway** (done automatically by deployment script)
- [x] **Review and verify secrets in Railway dashboard** (edit as needed)
- [ ] **Switch Stripe to live mode** in Stripe dashboard
- [ ] **Update Stripe webhook endpoints** to production domain
- [ ] **Verify Stripe account** has all business/bank details correct

### **Phase 3: Platform Infrastructure (15-30 min)**
- [x] **Create PostgreSQL database** on Railway (plugin added)
- [x] **Create Redis instance** on Railway (plugin added)
- [x] **Set up container registry** (not needed for Railway, handled automatically)
- [x] **Configure environment variables** in platform dashboard (verify after script upload)
- [x] **Project linked via CLI**
- [ ] **Set up monitoring/alerting** (UptimeRobot, etc.)

### **Phase 4: Domain & SSL (15-30 min)**
- [ ] **Configure DNS records** to point to deployment
- [ ] **Set up SSL certificate** (automatic on most platforms)
- [ ] **Test HTTPS access** and domain resolution

### **Phase 5: Final Production Testing (30-45 min)**
- [ ] **Test commission workflow** end-to-end
- [ ] **Verify Stripe payments** in live mode
- [ ] **Check Reddit integration** functionality
- [ ] **Test image generation** and upload
- [ ] **Verify email notifications** are working
- [ ] **Test all user flows** (donations, commissions, etc.)

### **Phase 6: CI/CD Pipeline Setup (15-30 min)**
- [ ] **Set up GitHub Actions CI workflow** for automated testing
- [ ] **Configure branch protection rules** on GitHub
- [ ] **Add pre-deployment checks** (tests, linting, security)
- [ ] **Set up deployment status checks** in Railway
- [ ] **Configure automated testing** on pull requests
- [ ] **Add code coverage reporting** (optional)
- [ ] **Set up security scanning** (optional)

---

## **TASKS I CAN HELP WITH**

### **Immediate Help (Next Few Hours)**
- [x] **Build and optimize Docker images** for production
- [x] **Update deployment scripts** for your chosen platform
- [x] **Create platform-specific deployment guides** (Railway/DigitalOcean/GCP)
- [ ] **Set up automated health checks** and monitoring scripts
- [ ] **Optimize database migrations** for production
- [ ] **Create backup/restore procedures** for production data
- [ ] **Set up logging and error tracking** (Sentry integration)
- [ ] **Optimize frontend build** for production performance
- [ ] **Create production testing scripts** for commission workflow
- [ ] **Set up rate limiting** and security headers

### **Ongoing Support**
- [ ] **Monitor deployment logs** and troubleshoot issues
- [ ] **Optimize performance** based on production metrics
- [ ] **Update dependencies** and security patches
- [ ] **Scale infrastructure** as needed
- [ ] **Implement additional monitoring** and alerting
- [ ] **Create disaster recovery** procedures

---

## **RECOMMENDED DEPLOYMENT PATH**

**For fastest launch (next few hours):**

1. **Choose Railway** - Simplest setup, built-in PostgreSQL/Redis, automatic HTTPS
2. **Register clouvel.ai** immediately
3. **Let me help you** with Docker optimization and deployment scripts
4. **You handle** environment variables and Stripe production setup
5. **Deploy together** using the automated scripts

**Estimated timeline:**
- **Platform setup**: 30 min
- **Environment config**: 30 min  
- **Deployment**: 45 min
- **Testing**: 30 min
- **Total**: ~2.5 hours

---

## **CRITICAL SUCCESS FACTORS**

1. **Stripe production keys** must be switched from test to live
2. **All API keys** must be production versions
3. **Database** must be properly migrated/seeded
4. **SSL certificate** must be valid
5. **Commission workflow** must be tested end-to-end
6. **Monitoring** must be configured for alerts

---

## **PLATFORM-SPECIFIC NOTES**

### **Railway (Recommended for Speed)**
- Built-in PostgreSQL and Redis
- Automatic HTTPS
- Simple GitHub integration
- Pay-per-use pricing
- Easy to migrate later

### **DigitalOcean (Balanced)**
- Simple pricing structure
- Good documentation
- Managed Kubernetes available
- Predictable costs

### **Google Cloud (Enterprise)**
- Best Kubernetes experience
- Strong security features
- Global infrastructure
- More complex setup

---

## **PROGRESS TRACKING**

**Started**: July 11, 2025
**Target Completion**: July 11, 2025 (Today!)
**Platform Chosen**: Railway
**Domain**: clouvel.ai

**Current Phase**: Phase 3 - Platform Infrastructure ✅
**Next Action**: Complete Phase 4 (Domain & SSL), then Phase 5 (Testing)

**Completed Phases:**
- ✅ Phase 1: Domain & Platform Setup
- ✅ Phase 2: Production Environment Setup  
- ✅ Phase 3: Platform Infrastructure

**Remaining Phases:**
- [ ] Phase 4: Domain & SSL
- [ ] Phase 5: Final Production Testing
- [ ] Phase 6: CI/CD Pipeline Setup

**Recent Updates:**
- ✅ Manual commission endpoint implemented with comprehensive test coverage
- ✅ Railway deployment pipeline configured
- ✅ All tests passing (214 passed, 10 xfailed)
- ✅ Ready for production deployment

---

*Check off items as we complete them! 🚀* 