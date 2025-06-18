# Zazzle Agent Deployment Guide

This guide provides comprehensive instructions for deploying the Zazzle Agent application using Docker and Kubernetes.

## 🚀 **Quick Start Options**

### **Option 1: Local Docker Compose (Recommended for Development)**
```bash
# Clone the repository
git clone https://github.com/sctennis77/zazzle-agent.git
cd zazzle-agent

# Set up environment variables
cp .env.example .env
# Edit .env with your API keys

# Run the application
docker-compose up -d
```

### **Option 2: Cloud Deployment (Production)**
Follow the detailed steps below for production deployment.

## 📋 **Prerequisites**

### **Required Accounts & Services**
- [GitHub Account](https://github.com) (for repository and container registry)
- [OpenAI API Key](https://platform.openai.com/api-keys)
- [Reddit API Credentials](https://www.reddit.com/prefs/apps)
- [Zazzle Affiliate Account](https://www.zazzle.com/affiliate)

### **Infrastructure Options**
Choose one of the following cloud providers:

#### **A. Google Cloud Platform (GCP) - Recommended**
- Google Cloud Account
- Google Kubernetes Engine (GKE) cluster
- Cloud Build enabled
- Container Registry access

#### **B. Amazon Web Services (AWS)**
- AWS Account
- Amazon EKS cluster
- ECR repository
- Route 53 for DNS

#### **C. Microsoft Azure**
- Azure Account
- Azure Kubernetes Service (AKS)
- Azure Container Registry
- Azure DNS

## 🔧 **Local Development Setup**

### **1. Environment Configuration**
```bash
# Copy environment template
cp .env.example .env

# Edit with your credentials
nano .env
```

Required environment variables:
```env
OPENAI_API_KEY=your_openai_api_key
REDDIT_CLIENT_ID=your_reddit_client_id
REDDIT_CLIENT_SECRET=your_reddit_client_secret
REDDIT_USER_AGENT=your_reddit_user_agent
ZAZZLE_AFFILIATE_ID=your_zazzle_affiliate_id
```

### **2. Local Docker Compose**
```bash
# Build and start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### **3. Service URLs**
- **Frontend**: http://localhost:5173
- **API**: http://localhost:8000
- **API Health**: http://localhost:8000/health

## ☁️ **Production Deployment**

### **Phase 1: GitHub Setup**

#### **1. Repository Configuration**
```bash
# Make repository private (recommended for production)
# Go to GitHub Settings > General > Danger Zone > Change repository visibility
```

#### **2. GitHub Secrets Setup**
Navigate to your repository → Settings → Secrets and variables → Actions

Add the following secrets:
- `OPENAI_API_KEY`
- `REDDIT_CLIENT_ID`
- `REDDIT_CLIENT_SECRET`
- `REDDIT_USER_AGENT`
- `ZAZZLE_AFFILIATE_ID`

#### **3. Enable GitHub Container Registry**
- Go to Settings → Packages
- Ensure "Inherit access from source repository" is enabled

### **Phase 2: Cloud Infrastructure Setup**

#### **GCP Setup (Recommended)**

1. **Create GKE Cluster**
```bash
# Install Google Cloud CLI
gcloud auth login
gcloud config set project YOUR_PROJECT_ID

# Create GKE cluster
gcloud container clusters create zazzle-agent-cluster \
  --zone=us-central1-a \
  --num-nodes=3 \
  --machine-type=e2-standard-2 \
  --enable-autoscaling \
  --min-nodes=1 \
  --max-nodes=5
```

2. **Configure kubectl**
```bash
gcloud container clusters get-credentials zazzle-agent-cluster --zone=us-central1-a
```

3. **Install NGINX Ingress Controller**
```bash
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.8.2/deploy/static/provider/cloud/deploy.yaml
```

#### **AWS Setup**

1. **Create EKS Cluster**
```bash
# Install eksctl
eksctl create cluster \
  --name zazzle-agent-cluster \
  --region us-west-2 \
  --nodegroup-name standard-workers \
  --node-type t3.medium \
  --nodes 3 \
  --nodes-min 1 \
  --nodes-max 5
```

2. **Install AWS Load Balancer Controller**
```bash
kubectl apply -k "github.com/aws/eks-charts/stable/aws-load-balancer-controller//crds?ref=master"
```

### **Phase 3: Kubernetes Deployment**

#### **1. Prepare Secrets**
```bash
# Create base64 encoded secrets
echo -n "your_openai_api_key" | base64
echo -n "your_reddit_client_id" | base64
echo -n "your_reddit_client_secret" | base64
echo -n "your_reddit_user_agent" | base64
echo -n "your_zazzle_affiliate_id" | base64
```

#### **2. Update Kubernetes Configuration**
```bash
# Edit k8s/secrets.yaml with your base64 encoded values
nano k8s/secrets.yaml

# Update k8s/ingress.yaml with your domain
nano k8s/ingress.yaml
```

#### **3. Deploy to Kubernetes**
```bash
# Create namespace and resources
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/secrets.yaml
kubectl apply -f k8s/persistent-volume.yaml

# Deploy services
kubectl apply -f k8s/api-deployment.yaml
kubectl apply -f k8s/frontend-deployment.yaml
kubectl apply -f k8s/pipeline-deployment.yaml
kubectl apply -f k8s/interaction-deployment.yaml
kubectl apply -f k8s/ingress.yaml
```

#### **4. Verify Deployment**
```bash
# Check pod status
kubectl get pods -n zazzle-agent

# Check services
kubectl get services -n zazzle-agent

# Check ingress
kubectl get ingress -n zazzle-agent
```

### **Phase 4: DNS and SSL Setup**

#### **1. Domain Configuration**
- Point your domain to the load balancer IP
- For GCP: Use Cloud DNS
- For AWS: Use Route 53

#### **2. SSL Certificate**
```bash
# Install cert-manager (for automatic SSL)
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.0/cert-manager.yaml

# Create ClusterIssuer for Let's Encrypt
kubectl apply -f k8s/cluster-issuer.yaml
```

## 🔄 **CI/CD Pipeline**

### **Automated Deployment**
The GitHub Actions workflow automatically:
1. Runs all tests
2. Builds Docker images
3. Pushes to GitHub Container Registry
4. Deploys to staging (if configured)
5. Deploys to production (if configured)

### **Manual Deployment**
```bash
# Trigger deployment
git push origin main

# Monitor deployment
kubectl get pods -n zazzle-agent -w
```

## 📊 **Monitoring and Maintenance**

### **Health Checks**
```bash
# Check service health
kubectl get pods -n zazzle-agent

# View logs
kubectl logs -f deployment/zazzle-agent-api -n zazzle-agent
kubectl logs -f deployment/zazzle-agent-pipeline -n zazzle-agent
kubectl logs -f deployment/zazzle-agent-interaction -n zazzle-agent
```

### **Scaling**
```bash
# Scale API service
kubectl scale deployment zazzle-agent-api --replicas=3 -n zazzle-agent

# Scale frontend service
kubectl scale deployment zazzle-agent-frontend --replicas=3 -n zazzle-agent
```

### **Updates**
```bash
# Update to latest version
git pull origin main
kubectl apply -f k8s/

# Rollback if needed
kubectl rollout undo deployment/zazzle-agent-api -n zazzle-agent
```

## 🛠️ **Troubleshooting**

### **Common Issues**

#### **1. Pods Not Starting**
```bash
# Check pod events
kubectl describe pod <pod-name> -n zazzle-agent

# Check logs
kubectl logs <pod-name> -n zazzle-agent
```

#### **2. Database Issues**
```bash
# Check database connectivity
kubectl exec -it <api-pod> -n zazzle-agent -- python -c "from app.db.database import init_db; init_db()"
```

#### **3. API Key Issues**
```bash
# Verify secrets
kubectl get secrets zazzle-agent-secrets -n zazzle-agent -o yaml
```

### **Performance Optimization**

#### **Resource Limits**
- Monitor resource usage: `kubectl top pods -n zazzle-agent`
- Adjust limits in deployment files as needed

#### **Database Optimization**
- Consider migrating to PostgreSQL for production
- Implement database backups
- Monitor query performance

## 🔒 **Security Considerations**

### **Production Security Checklist**
- [ ] Repository is private
- [ ] All secrets are properly configured
- [ ] SSL/TLS is enabled
- [ ] Network policies are configured
- [ ] Regular security updates are applied
- [ ] Monitoring and alerting is set up

### **API Key Rotation**
```bash
# Update secrets
kubectl patch secret zazzle-agent-secrets -n zazzle-agent -p '{"data":{"OPENAI_API_KEY":"<new-base64-key>"}}'

# Restart deployments
kubectl rollout restart deployment/zazzle-agent-api -n zazzle-agent
kubectl rollout restart deployment/zazzle-agent-pipeline -n zazzle-agent
kubectl rollout restart deployment/zazzle-agent-interaction -n zazzle-agent
```

## 📈 **Scaling Strategy**

### **Horizontal Scaling**
- API and Frontend services can scale horizontally
- Pipeline and Interaction services should remain single instance
- Use auto-scaling based on CPU/memory usage

### **Vertical Scaling**
- Monitor resource usage and adjust limits
- Consider upgrading node types for better performance

## 🎯 **Next Steps**

1. **Set up monitoring** (Prometheus + Grafana)
2. **Implement logging** (ELK Stack or similar)
3. **Add backup strategy** for database
4. **Set up alerting** for critical issues
5. **Implement blue-green deployments**
6. **Add performance testing**

## 📞 **Support**

For deployment issues:
1. Check the troubleshooting section
2. Review logs and events
3. Verify configuration
4. Create an issue in the GitHub repository

---

**Happy Deploying! 🚀** 