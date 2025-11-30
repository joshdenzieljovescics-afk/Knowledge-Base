# AWS Lambda Deployment - Complete Package

Your Knowledge Base application is now ready to be deployed to AWS Lambda! This package includes everything you need to transform your traditional FastAPI application into a serverless, auto-scaling cloud application.

## 📦 What's Included

### Core Deployment Files
- **[lambda_handler.py](lambda_handler.py)** - Lambda entry point with Mangum adapter
- **[template.yaml](template.yaml)** - AWS SAM infrastructure template
- **[samconfig.toml](samconfig.toml)** - Deployment configuration
- **[deploy.ps1](deploy.ps1)** - Automated deployment script

### Documentation
- **[LAMBDA_QUICK_START.md](LAMBDA_QUICK_START.md)** - ⭐ Start here! Quick reference
- **[LAMBDA_DEPLOYMENT_GUIDE.md](LAMBDA_DEPLOYMENT_GUIDE.md)** - Complete deployment guide
- **[LAMBDA_CONVERSION_SUMMARY.md](LAMBDA_CONVERSION_SUMMARY.md)** - What was changed
- **[LAMBDA_ARCHITECTURE.md](LAMBDA_ARCHITECTURE.md)** - Architecture diagrams
- **[LAMBDA_README.md](LAMBDA_README.md)** - This file

### Adapter Code
- **[database/dynamodb_adapter.py](database/dynamodb_adapter.py)** - DynamoDB operations
- **[utils/s3_storage.py](utils/s3_storage.py)** - S3 file storage

## 🚀 Quick Start (5 Minutes)

### 1. Install Prerequisites

```powershell
# Install AWS CLI
choco install awscli

# Install SAM CLI
choco install aws-sam-cli

# Configure AWS credentials
aws configure
```

### 2. Update Configuration

Edit [samconfig.toml](samconfig.toml) and replace these values:

```toml
s3_bucket = "your-deployment-bucket-name"

parameter_overrides = [
    "OpenAIApiKey=sk-your-key",
    "WeaviateUrl=https://your-cluster.weaviate.network",
    "WeaviateApiKey=your-key",
    "JWTSecretKey=your-secret-min-32-chars",
    "AllowedOrigins=https://yourdomain.com"
]
```

### 3. Create Deployment Bucket

```powershell
aws s3 mb s3://your-deployment-bucket-name
```

### 4. Deploy!

```powershell
cd backend
.\deploy.ps1 -Guided
```

That's it! Your API will be live in ~5 minutes.

## 📖 Documentation Structure

```
Start Here → LAMBDA_QUICK_START.md
    │
    ├─ Need more details? → LAMBDA_DEPLOYMENT_GUIDE.md
    │   │
    │   ├─ Prerequisites
    │   ├─ Step-by-step deployment
    │   ├─ Code migration guide
    │   ├─ Troubleshooting
    │   └─ Production checklist
    │
    ├─ What changed? → LAMBDA_CONVERSION_SUMMARY.md
    │   │
    │   ├─ Files created
    │   ├─ Architecture changes
    │   └─ Next steps
    │
    └─ How does it work? → LAMBDA_ARCHITECTURE.md
        │
        ├─ System diagrams
        ├─ Request flow
        ├─ Storage architecture
        └─ Security layers
```

## 🏗️ Architecture Overview

### Before (Traditional Server)
```
Your Computer → FastAPI (port 8009) → SQLite + Local Files
```

### After (Serverless Lambda)
```
Internet → API Gateway → Lambda → DynamoDB + S3 + Weaviate
```

### Benefits
- ✅ Auto-scales from 0 to thousands of requests
- ✅ Pay only for actual usage ($15-30/month typical)
- ✅ No server maintenance
- ✅ High availability (99.99% uptime SLA)
- ✅ Global deployment ready

## 🎯 Common Commands

All commands use the [deploy.ps1](deploy.ps1) script for convenience:

```powershell
# First deployment (guided setup)
.\deploy.ps1 -Guided

# Subsequent deployments
.\deploy.ps1

# Test locally before deploying
.\deploy.ps1 local

# View live logs
.\deploy.ps1 logs

# Get stack information
.\deploy.ps1 info

# Test deployed API
.\deploy.ps1 test

# Delete everything
.\deploy.ps1 delete
```

Or use SAM CLI directly:

```powershell
# Build
sam build

# Deploy
sam deploy

# Local testing
sam local start-api

# Stream logs
sam logs --tail --stack-name knowledge-base-api
```

## 📊 What Gets Deployed

### AWS Resources Created

1. **Lambda Function** (`knowledge-base-api`)
   - Your FastAPI application
   - 3GB memory, 15-minute timeout
   - Auto-scaling from 0 to 1000 concurrent executions

2. **API Gateway** (HTTP API)
   - HTTPS endpoint: `https://xxx.execute-api.region.amazonaws.com/prod`
   - CORS configured
   - Access logging enabled

3. **DynamoDB Tables**
   - `knowledge-base-documents` - Document metadata
   - `knowledge-base-chat-history` - Chat conversations
   - On-demand billing (pay per request)

4. **S3 Bucket** (`knowledge-base-pdfs-{account-id}`)
   - PDF file storage
   - Versioning enabled
   - Encrypted at rest

5. **CloudWatch Log Groups**
   - Lambda execution logs
   - API Gateway access logs
   - 30-day retention

### Total Cost Estimate

**For 10,000 requests/month:**
- Lambda: ~$15
- DynamoDB: ~$2
- S3: ~$1
- API Gateway: ~$0.01
- CloudWatch: ~$0.50

**Total: ~$18-20/month**

Free tier covers first 1M requests + 400,000 GB-seconds/month!

## 🔧 Migration Guide

### Database Migration (SQLite → DynamoDB)

**Before:**
```python
from database.operations import save_document
doc_id = save_document(doc_data)
```

**After:**
```python
from database.dynamodb_adapter import get_dynamodb_adapter
db = get_dynamodb_adapter()
doc_id = db.save_document(doc_data)
```

### File Storage Migration (Local → S3)

**Before:**
```python
with open(f'outputs/{filename}', 'wb') as f:
    f.write(file_data)
```

**After:**
```python
from utils.s3_storage import get_s3_storage
s3 = get_s3_storage()
s3_key = s3.upload_file(file_data, filename)
```

**See [LAMBDA_DEPLOYMENT_GUIDE.md](LAMBDA_DEPLOYMENT_GUIDE.md) for complete migration examples.**

## 🐛 Troubleshooting

### Build Fails
```powershell
# Clean and rebuild
rm -rf .aws-sam
sam build
```

### Deployment Fails
```powershell
# Check CloudFormation events
aws cloudformation describe-stack-events --stack-name knowledge-base-api
```

### Lambda Errors
```powershell
# View logs
.\deploy.ps1 logs

# Or in AWS Console
# CloudWatch → Log Groups → /aws/lambda/knowledge-base-api
```

### Package Too Large
- Use Lambda Layers (see deployment guide)
- Remove unnecessary dependencies
- Use Docker-based Lambda (advanced)

## 📈 Monitoring

### View Metrics

**In AWS Console:**
1. Go to Lambda → knowledge-base-api
2. Click "Monitor" tab
3. View metrics: invocations, errors, duration, throttles

**Using CLI:**
```powershell
# Get stack info
.\deploy.ps1 info

# Stream logs
.\deploy.ps1 logs

# Test endpoint
.\deploy.ps1 test
```

### Set Up Alarms

```powershell
# Error rate alarm
aws cloudwatch put-metric-alarm \
  --alarm-name kb-api-errors \
  --alarm-description "Alert on Lambda errors" \
  --metric-name Errors \
  --namespace AWS/Lambda \
  --statistic Sum \
  --period 300 \
  --threshold 10 \
  --comparison-operator GreaterThanThreshold
```

## 🔐 Security Best Practices

### 1. Use AWS Secrets Manager

Instead of putting API keys in [samconfig.toml](samconfig.toml):

```powershell
# Store secrets
aws secretsmanager create-secret \
  --name knowledge-base/openai-key \
  --secret-string "sk-your-key"

# Update Lambda to read from Secrets Manager
# (See deployment guide for code examples)
```

### 2. Configure CORS Properly

In production, specify exact origins:

```toml
AllowedOrigins=https://yourdomain.com,https://app.yourdomain.com
```

### 3. Enable WAF (Web Application Firewall)

```yaml
# Add to template.yaml
WebAcl:
  Type: AWS::WAFv2::WebACL
  Properties:
    # ... WAF rules
```

### 4. Use VPC for Lambda (Optional)

For sensitive workloads, run Lambda in VPC:

```yaml
# In template.yaml
VpcConfig:
  SecurityGroupIds:
    - sg-xxxxx
  SubnetIds:
    - subnet-xxxxx
    - subnet-yyyyy
```

## 🌍 Multi-Region Deployment

Deploy to multiple regions for global low latency:

```powershell
# US East
sam deploy --region us-east-1 --stack-name kb-api-us-east

# Europe
sam deploy --region eu-west-1 --stack-name kb-api-eu-west

# Asia
sam deploy --region ap-southeast-1 --stack-name kb-api-asia
```

Then use Route53 for geo-routing.

## 📝 Deployment Checklist

### Before First Deployment

- [ ] AWS CLI installed and configured
- [ ] SAM CLI installed
- [ ] AWS credentials configured
- [ ] S3 deployment bucket created
- [ ] [samconfig.toml](samconfig.toml) updated with your values
- [ ] API keys ready (OpenAI, Weaviate, JWT secret)

### Testing

- [ ] Test locally: `.\deploy.ps1 local`
- [ ] Code builds successfully: `sam build`
- [ ] All environment variables set correctly

### Deployment

- [ ] Deploy to dev/test first: `.\deploy.ps1 -Guided`
- [ ] Test all endpoints
- [ ] Check CloudWatch logs
- [ ] Monitor for errors

### Production

- [ ] Use Secrets Manager for API keys
- [ ] Configure specific CORS origins
- [ ] Set up CloudWatch alarms
- [ ] Set up billing alerts
- [ ] Document API endpoint
- [ ] Update frontend with production URL
- [ ] Test thoroughly
- [ ] Set up custom domain (optional)

## 🆘 Getting Help

1. **Check Documentation**
   - [LAMBDA_QUICK_START.md](LAMBDA_QUICK_START.md) - Quick commands
   - [LAMBDA_DEPLOYMENT_GUIDE.md](LAMBDA_DEPLOYMENT_GUIDE.md) - Detailed guide
   - [LAMBDA_ARCHITECTURE.md](LAMBDA_ARCHITECTURE.md) - How it works

2. **Check Logs**
   ```powershell
   .\deploy.ps1 logs
   ```

3. **AWS Resources**
   - [AWS SAM Documentation](https://docs.aws.amazon.com/serverless-application-model/)
   - [FastAPI on Lambda](https://fastapi.tiangolo.com/deployment/lambda/)
   - [Mangum Documentation](https://mangum.io/)

4. **Common Issues**
   - Build fails → Clean `.aws-sam` directory
   - Deploy fails → Check CloudFormation events
   - Lambda errors → Check CloudWatch logs
   - Timeout → Increase timeout in template.yaml
   - Out of memory → Increase MemorySize in template.yaml

## 🎉 Success Indicators

After deployment, you should see:

1. ✅ CloudFormation stack created successfully
2. ✅ API endpoint URL displayed
3. ✅ All resources created (Lambda, API Gateway, DynamoDB, S3)
4. ✅ Test endpoint responds: `.\deploy.ps1 test`
5. ✅ Logs showing in CloudWatch

## 🔄 Making Updates

### Update Code

```powershell
# 1. Make changes to your Python code
# 2. Deploy
.\deploy.ps1
```

### Update Infrastructure

```powershell
# 1. Edit template.yaml
# 2. Deploy
.\deploy.ps1
```

### Update Environment Variables

```powershell
# 1. Edit template.yaml or samconfig.toml
# 2. Deploy
.\deploy.ps1
```

## 🗑️ Cleanup

To remove everything and stop charges:

```powershell
.\deploy.ps1 delete
```

This deletes:
- Lambda function
- API Gateway
- DynamoDB tables (and all data)
- S3 bucket (you may need to empty it first)
- CloudWatch logs
- All related resources

**Warning:** This is permanent! Back up any important data first.

## 📞 Next Steps

1. ✅ **Read [LAMBDA_QUICK_START.md](LAMBDA_QUICK_START.md)** - Get started in 5 minutes
2. ✅ **Deploy to test** - Try it out with `.\deploy.ps1 -Guided`
3. ✅ **Test thoroughly** - Make sure everything works
4. ✅ **Migrate database code** - Follow the deployment guide
5. ✅ **Deploy to production** - Go live!

## 💡 Pro Tips

- Start with a small deployment to test
- Use `sam local` to test changes before deploying
- Monitor costs in AWS Cost Explorer
- Set up billing alerts early
- Keep your `template.yaml` in Git for version control
- Use separate stacks for dev/staging/production
- Enable X-Ray tracing for debugging
- Use Lambda Layers for large dependencies

---

**Ready to deploy?** Head over to [LAMBDA_QUICK_START.md](LAMBDA_QUICK_START.md) and get started in 5 minutes!

**Need help?** Check [LAMBDA_DEPLOYMENT_GUIDE.md](LAMBDA_DEPLOYMENT_GUIDE.md) for detailed instructions and troubleshooting.

**Questions about architecture?** See [LAMBDA_ARCHITECTURE.md](LAMBDA_ARCHITECTURE.md) for diagrams and explanations.
