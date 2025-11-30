# Lambda Quick Start Guide

Quick reference for deploying the Knowledge Base API to AWS Lambda.

## Prerequisites Checklist

- [ ] AWS Account with admin access
- [ ] AWS CLI installed and configured
- [ ] AWS SAM CLI installed
- [ ] S3 bucket for deployment artifacts
- [ ] OpenAI API key
- [ ] Weaviate cluster URL and API key

## One-Time Setup (5 minutes)

### 1. Install Tools

```powershell
# AWS CLI
choco install awscli

# SAM CLI
choco install aws-sam-cli

# Verify
aws --version
sam --version
```

### 2. Configure AWS

```powershell
aws configure
# Enter your AWS credentials when prompted
```

### 3. Create Deployment Bucket

```powershell
# Replace YOURBUCKETNAME with a unique name
aws s3 mb s3://YOURBUCKETNAME
```

### 4. Update Configuration

Edit [samconfig.toml](samconfig.toml):

```toml
s3_bucket = "YOURBUCKETNAME"  # Your bucket from step 3
parameter_overrides = [
    "OpenAIApiKey=sk-...",     # Your OpenAI key
    "WeaviateUrl=https://...", # Your Weaviate URL
    "WeaviateApiKey=...",      # Your Weaviate key
    "JWTSecretKey=...",        # Random secret (min 32 chars)
    "AllowedOrigins=https://yourdomain.com"
]
```

## Deployment Commands

### First Deployment

```powershell
cd backend

# Build
sam build

# Deploy (guided)
sam deploy --guided
```

### Subsequent Deployments

```powershell
cd backend
sam build && sam deploy
```

### Update Only Code (Fast)

```powershell
cd backend
sam build && sam deploy --no-confirm-changeset
```

## Testing

### Test Locally

```powershell
cd backend

# Start local API
sam local start-api

# In another terminal, test
curl http://localhost:3000/health
```

### Test Deployed API

```powershell
# Get your API endpoint
aws cloudformation describe-stacks \
  --stack-name knowledge-base-api \
  --query 'Stacks[0].Outputs[?OutputKey==`ApiEndpoint`].OutputValue' \
  --output text

# Test health endpoint
curl https://YOUR-API-ID.execute-api.us-east-1.amazonaws.com/prod/health
```

## View Logs

### Stream Live Logs

```powershell
sam logs --stack-name knowledge-base-api --tail
```

### View Recent Logs

```powershell
sam logs --stack-name knowledge-base-api --start-time '30min ago'
```

## Common Tasks

### Update Environment Variables

Edit [template.yaml](template.yaml) under `Globals.Function.Environment.Variables`:

```yaml
Environment:
  Variables:
    ENVIRONMENT: production
    DEBUG: 'false'
```

Then redeploy:

```powershell
sam build && sam deploy
```

### Update API Keys

**Option 1: Via samconfig.toml** (Quick, less secure)

Edit `parameter_overrides` in [samconfig.toml](samconfig.toml), then:

```powershell
sam deploy
```

**Option 2: Via AWS Secrets Manager** (Recommended for production)

```powershell
# Store secret
aws secretsmanager create-secret \
  --name knowledge-base/openai-key \
  --secret-string "sk-your-new-key"

# Update secret
aws secretsmanager update-secret \
  --secret-id knowledge-base/openai-key \
  --secret-string "sk-your-new-key"
```

### Delete Stack

```powershell
aws cloudformation delete-stack --stack-name knowledge-base-api

# Wait for deletion to complete
aws cloudformation wait stack-delete-complete --stack-name knowledge-base-api
```

## Troubleshooting

### Build Fails

```powershell
# Clean and rebuild
rm -rf .aws-sam
sam build
```

### Deployment Fails

Check CloudFormation events:

```powershell
aws cloudformation describe-stack-events \
  --stack-name knowledge-base-api \
  --max-items 10
```

### Lambda Errors

View CloudWatch logs:

```powershell
sam logs --stack-name knowledge-base-api --tail
```

Or use AWS Console: CloudWatch → Log Groups → `/aws/lambda/knowledge-base-api`

### Timeout Issues

Increase timeout in [template.yaml](template.yaml):

```yaml
Timeout: 900  # 15 minutes (max)
```

### Memory Issues

Increase memory in [template.yaml](template.yaml):

```yaml
MemorySize: 3008  # 3GB (adjust as needed)
```

## Cost Monitoring

### View Current Costs

```powershell
aws ce get-cost-and-usage \
  --time-period Start=2025-01-01,End=2025-01-31 \
  --granularity MONTHLY \
  --metrics BlendedCost \
  --filter file://filter.json
```

### Set Up Billing Alert

```powershell
# Create SNS topic for alerts
aws sns create-topic --name billing-alerts

# Subscribe your email
aws sns subscribe \
  --topic-arn arn:aws:sns:us-east-1:ACCOUNT-ID:billing-alerts \
  --protocol email \
  --notification-endpoint your@email.com

# Create CloudWatch alarm
aws cloudwatch put-metric-alarm \
  --alarm-name knowledge-base-billing \
  --alarm-description "Alert when costs exceed $50" \
  --metric-name EstimatedCharges \
  --namespace AWS/Billing \
  --statistic Maximum \
  --period 86400 \
  --threshold 50 \
  --comparison-operator GreaterThanThreshold
```

## Production Checklist

Before going live:

- [ ] Use AWS Secrets Manager for API keys
- [ ] Set `DEBUG: 'false'` in environment
- [ ] Configure specific CORS origins (not `*`)
- [ ] Set up CloudWatch alarms for errors
- [ ] Set up billing alerts
- [ ] Enable CloudWatch Logs retention (30 days)
- [ ] Test all endpoints thoroughly
- [ ] Document your API endpoint
- [ ] Update frontend to use production URL
- [ ] Set up custom domain (optional)
- [ ] Enable API Gateway throttling
- [ ] Review IAM permissions

## Key Files

| File | Purpose |
|------|---------|
| [lambda_handler.py](lambda_handler.py) | Lambda entry point |
| [template.yaml](template.yaml) | SAM infrastructure template |
| [samconfig.toml](samconfig.toml) | Deployment configuration |
| [requirements.txt](requirements.txt) | Python dependencies |
| [LAMBDA_DEPLOYMENT_GUIDE.md](LAMBDA_DEPLOYMENT_GUIDE.md) | Detailed guide |

## Getting Help

1. **Check logs**: `sam logs --stack-name knowledge-base-api --tail`
2. **Review guide**: See [LAMBDA_DEPLOYMENT_GUIDE.md](LAMBDA_DEPLOYMENT_GUIDE.md)
3. **AWS Docs**: https://docs.aws.amazon.com/serverless-application-model/
4. **SAM Issues**: https://github.com/aws/aws-sam-cli/issues

## Next Steps

After successful deployment:

1. Test all API endpoints
2. Update frontend API URL
3. Migrate database to DynamoDB (see deployment guide)
4. Migrate file storage to S3 (see deployment guide)
5. Set up monitoring and alerts
6. Document your deployment process

---

**Estimated deployment time**: 5-10 minutes (first time), 2-3 minutes (subsequent)

**Estimated costs**: ~$15-30/month for moderate usage (see deployment guide for details)
