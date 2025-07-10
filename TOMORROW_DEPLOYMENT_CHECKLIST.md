# Tomorrow's Deployment Checklist 🚀

## Pre-Deployment (Tonight/Tomorrow Morning)

### ✅ Domain Registration
- [ ] **Register clouvel.ai** (confirmed available!)
  - Registrar: Namecheap, Google Domains, or Cloudflare
  - Cost: ~$12-15/year
  - Set up DNS records (will configure after deployment)

### ✅ Choose Deployment Platform
**Recommended Options:**
1. **Railway** (Fastest - $20-50/month)
   - Pros: Simple, built-in PostgreSQL/Redis, automatic HTTPS
   - Cons: Limited customization, vendor lock-in
   
2. **DigitalOcean** (Balanced - $87-157/month)
   - Pros: Simple pricing, good docs, room to grow
   - Cons: Limited global presence
   
3. **Google Cloud** (Enterprise - $135-255/month)
   - Pros: Best Kubernetes, strong security, global scale
   - Cons: Complex, unpredictable pricing

### ✅ Prepare Environment Variables
- [ ] Copy `env.production.template` to `.env.production`
- [ ] Fill in all required values:
  - Database URL (platform-specific)
  - Redis URL (platform-specific)
  - Stripe production keys
  - OpenAI API key
  - Reddit API credentials
  - Zazzle affiliate credentials
  - Email configuration
  - Security keys

## Deployment Day (Tomorrow)

### Phase 1: Platform Setup (30 minutes)
- [ ] **Create account** on chosen platform
- [ ] **Set up container registry** (if needed)
- [ ] **Create database** (PostgreSQL)
- [ ] **Create Redis instance**
- [ ] **Configure environment variables** in platform dashboard

### Phase 2: Application Deployment (45 minutes)
- [ ] **Build Docker images** locally
- [ ] **Push images** to container registry
- [ ] **Deploy application** using platform-specific method
- [ ] **Verify services** are running
- [ ] **Test health endpoints**

### Phase 3: Domain & SSL (30 minutes)
- [ ] **Configure DNS records** to point to deployment
- [ ] **Set up SSL certificate** (automatic on most platforms)
- [ ] **Test HTTPS** access
- [ ] **Verify domain** is working

### Phase 4: Production Testing (30 minutes)
- [ ] **Test commission workflow** end-to-end
- [ ] **Verify Stripe payments** (test mode first)
- [ ] **Check Reddit integration**
- [ ] **Test image generation**
- [ ] **Verify email notifications**

### Phase 5: Monitoring & Security (30 minutes)
- [ ] **Set up monitoring** (platform-specific)
- [ ] **Configure logging**
- [ ] **Set up alerts** for downtime
- [ ] **Review security settings**
- [ ] **Test backup/restore** procedures

## Go-Live Checklist

### Final Verification
- [ ] **All services healthy**
- [ ] **SSL certificate valid**
- [ ] **Domain resolving correctly**
- [ ] **Commission workflow working**
- [ ] **Payments processing**
- [ ] **Images generating**
- [ ] **Emails sending**

### Production Switch
- [ ] **Switch Stripe to live mode**
- [ ] **Update any test URLs**
- [ ] **Announce launch** (if desired)
- [ ] **Monitor for issues**

## Emergency Contacts & Resources

### Platform Support
- **Railway**: Discord community, email support
- **DigitalOcean**: 24/7 support, extensive docs
- **Google Cloud**: 24/7 support, enterprise-grade

### Backup Plans
- **If Railway fails**: Quick migration to DigitalOcean
- **If domain issues**: Use platform subdomain temporarily
- **If database issues**: Restore from backup, check logs

## Cost Tracking
- **Domain**: $12-15/year
- **Platform**: $20-255/month (depending on choice)
- **Total first month**: $32-270

## Success Metrics
- [ ] **Zero downtime** during deployment
- [ ] **All features working** in production
- [ ] **Commission workflow** processing correctly
- [ ] **Payments flowing** through Stripe
- [ ] **Monitoring alerts** configured
- [ ] **Documentation updated** for production

---

## Quick Commands for Tomorrow

```bash
# 1. Check domain availability (already done)
python3 scripts/check-domain.py

# 2. Build and test locally
make build
make test

# 3. Deploy to production
./scripts/deploy-production.sh

# 4. Health check
curl https://clouvel.ai/health
```

**🎯 Goal: Clouvel live by end of day tomorrow!** 