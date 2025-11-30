# AWS Lambda Deployment Guide

This guide explains how to deploy the Knowledge Base API as an AWS Lambda function using AWS SAM (Serverless Application Model).

## Table of Contents
- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Architecture Changes](#architecture-changes)
- [Deployment Steps](#deployment-steps)
- [Configuration](#configuration)
- [Monitoring & Troubleshooting](#monitoring--troubleshooting)
- [Cost Optimization](#cost-optimization)
- [Migration Considerations](#migration-considerations)

## Overview

The Knowledge Base application can be deployed as a serverless Lambda function, which offers:

- ✅ **Auto-scaling**: Handles traffic spikes automatically
- ✅ **Pay-per-use**: Only pay for actual compute time
- ✅ **No server management**: AWS handles infrastructure
- ✅ **High availability**: Built-in redundancy
- ⚠️ **Cold starts**: Initial requests may be slower
- ⚠️ **Execution limits**: 15-minute max timeout, 10GB max memory

### What Changes?

**Stays the same:**
- FastAPI application code
- API routes and business logic
- External services (OpenAI, Weaviate)

**Changes required:**
- SQLite → DynamoDB (serverless database)
- File storage → S3 (cloud storage)
- Lambda handler wrapper (Mangum)
- Deployment via SAM/CloudFormation

## Prerequisites

### 1. Install AWS CLI

```powershell
# Download from: https://aws.amazon.com/cli/
# Or use chocolatey
choco install awscli

# Verify installation
aws --version
```

### 2. Install AWS SAM CLI

```powershell
# Download from: https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html
# Or use chocolatey
choco install aws-sam-cli

# Verify installation
sam --version
```

### 3. Configure AWS Credentials

```powershell
aws configure
# Enter:
# - AWS Access Key ID
# - AWS Secret Access Key
# - Default region (e.g., us-east-1)
# - Default output format (json)
```

### 4. Create S3 Bucket for Deployment

```powershell
# Replace with your bucket name
aws s3 mb s3://knowledge-base-deployment-artifacts
```

## Architecture Changes

### Database Migration: SQLite → DynamoDB

**Current (SQLite):**
```python
# Local file-based database
conn = sqlite3.connect('database.db')
```

**Lambda (DynamoDB):**
```python
# Cloud-based NoSQL database
import boto3
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('knowledge-base-documents')
```

### File Storage: Local → S3

**Current (Local):**
```python
# Save to local filesystem
with open(f'outputs/{filename}', 'wb') as f:
    f.write(file.read())
```

**Lambda (S3):**
```python
# Upload to S3
import boto3
s3 = boto3.client('s3')
s3.put_object(Bucket='knowledge-base-pdfs', Key=filename, Body=file.read())
```

## Deployment Steps

### Step 1: Update Dependencies

Add Lambda-specific dependencies to `requirements.txt`:

```bash
cd backend
cat >> requirements.txt << EOF
mangum==0.18.0
boto3==1.35.0
EOF
```

### Step 2: Create Parameter File

Create `samconfig.toml` in the `backend` directory:

```toml
version = 0.1

[default]
[default.deploy]
[default.deploy.parameters]
stack_name = "knowledge-base-api"
s3_bucket = "knowledge-base-deployment-artifacts"
s3_prefix = "knowledge-base"
region = "us-east-1"
capabilities = "CAPABILITY_IAM"
parameter_overrides = [
    "OpenAIApiKey=your-openai-key",
    "WeaviateUrl=https://your-cluster.weaviate.network",
    "WeaviateApiKey=your-weaviate-key",
    "JWTSecretKey=your-jwt-secret",
    "AllowedOrigins=https://yourdomain.com,http://localhost:5173"
]
```

**Security Note**: Never commit API keys! Use AWS Secrets Manager (see below).

### Step 3: Build and Deploy

```powershell
cd backend

# Build the application
sam build

# Deploy (first time - guided)
sam deploy --guided

# Subsequent deployments
sam deploy
```

The guided deployment will ask:
- Stack Name: `knowledge-base-api`
- AWS Region: `us-east-1` (or your preferred region)
- Parameter values (API keys, etc.)
- Confirm changes before deploy: `Y`
- Allow SAM CLI IAM role creation: `Y`
- Save arguments to configuration file: `Y`

### Step 4: Get API Endpoint

After deployment completes:

```powershell
# Get the API endpoint
aws cloudformation describe-stacks \
  --stack-name knowledge-base-api \
  --query 'Stacks[0].Outputs[?OutputKey==`ApiEndpoint`].OutputValue' \
  --output text
```

Example output: `https://abc123def.execute-api.us-east-1.amazonaws.com/prod`

### Step 5: Update Frontend

Update your frontend API endpoint in [frontend/src/api.js](frontend/src/api.js):

```javascript
// Before
const API_BASE_URL = 'http://localhost:8009';

// After
const API_BASE_URL = 'https://abc123def.execute-api.us-east-1.amazonaws.com/prod';
```

## Configuration

### Using AWS Secrets Manager (Recommended)

Instead of hardcoding API keys, use Secrets Manager:

```powershell
# Create secrets
aws secretsmanager create-secret \
  --name knowledge-base/openai-key \
  --secret-string "your-openai-key"

aws secretsmanager create-secret \
  --name knowledge-base/weaviate-url \
  --secret-string "https://your-cluster.weaviate.network"

aws secretsmanager create-secret \
  --name knowledge-base/weaviate-key \
  --secret-string "your-weaviate-key"

aws secretsmanager create-secret \
  --name knowledge-base/jwt-secret \
  --secret-string "your-jwt-secret"
```

Update `lambda_handler.py` to fetch secrets:

```python
import boto3
import json
from botocore.exceptions import ClientError

def get_secret(secret_name):
    session = boto3.session.Session()
    client = session.client('secretsmanager')
    try:
        response = client.get_secret_value(SecretId=secret_name)
        return response['SecretString']
    except ClientError as e:
        raise e

# Use in config
import os
os.environ['OPENAI_API_KEY'] = get_secret('knowledge-base/openai-key')
```

### Environment Variables

All environment variables are set in `template.yaml` under `Environment.Variables`.

### CORS Configuration

Update allowed origins in the deployment:

```powershell
sam deploy --parameter-overrides AllowedOrigins="https://yourdomain.com,https://app.yourdomain.com"
```

## Monitoring & Troubleshooting

### View Logs

```powershell
# Stream live logs
sam logs --stack-name knowledge-base-api --tail

# View specific time range
sam logs --stack-name knowledge-base-api \
  --start-time '10min ago' \
  --end-time 'now'
```

### CloudWatch Logs Console

1. Go to AWS Console → CloudWatch → Log Groups
2. Find `/aws/lambda/knowledge-base-api`
3. View log streams

### Common Issues

#### 1. Cold Start Timeout

**Problem**: First request times out after 30 seconds.

**Solution**:
- Increase Lambda timeout in `template.yaml` (already set to 900s)
- Use provisioned concurrency to keep functions warm (costs more)

```yaml
# In template.yaml
KnowledgeBaseFunction:
  Properties:
    ProvisionedConcurrencyConfig:
      ProvisionedConcurrentExecutions: 1
```

#### 2. Package Size Too Large

**Problem**: Deployment package exceeds 50MB uncompressed.

**Solution**: Use Lambda Layers

```powershell
# Create layer directory
mkdir -p layer/python
pip install -r requirements.txt -t layer/python/

# Update template.yaml (already commented out)
# Uncomment the DependenciesLayer section
```

#### 3. Database Connection Errors

**Problem**: SQLite doesn't work in Lambda.

**Solution**: Migrate to DynamoDB (see code changes below).

#### 4. File Upload Failures

**Problem**: Can't write to `/tmp` or file size exceeds 512MB.

**Solution**:
- Use S3 for file storage
- Generate pre-signed URLs for large uploads

### Test Locally

```powershell
# Start local API Gateway emulator
sam local start-api

# Test with curl
curl http://localhost:3000/health
```

## Cost Optimization

### Lambda Pricing (us-east-1)

- **Requests**: $0.20 per 1M requests
- **Compute**: $0.0000166667 per GB-second
- **Free Tier**: 1M requests + 400,000 GB-seconds/month

**Example Monthly Cost** (10,000 requests, 30s avg, 3GB memory):

```
Requests: 10,000 × $0.0000002 = $0.002
Compute: 10,000 × 30s × 3GB × $0.0000166667 = $15.00
Total: ~$15/month
```

### Cost Savings Tips

1. **Reduce Memory**: Test with 1024MB first, increase if needed
2. **Optimize Cold Starts**: Lazy load heavy dependencies
3. **Use Reserved Concurrency**: For predictable workloads
4. **Set Up CloudWatch Alarms**: Monitor costs in real-time

```powershell
# Create billing alarm
aws cloudwatch put-metric-alarm \
  --alarm-name knowledge-base-cost-alarm \
  --alarm-description "Alert if costs exceed $50" \
  --metric-name EstimatedCharges \
  --namespace AWS/Billing \
  --statistic Maximum \
  --period 86400 \
  --threshold 50 \
  --comparison-operator GreaterThanThreshold
```

## Migration Considerations

### Required Code Changes

#### 1. Database Layer Migration

**Create DynamoDB adapter** in `backend/database/dynamodb_adapter.py`:

```python
import boto3
from typing import Optional, List, Dict
from datetime import datetime
import uuid

class DynamoDBAdapter:
    def __init__(self):
        self.dynamodb = boto3.resource('dynamodb')
        self.documents_table = self.dynamodb.Table('knowledge-base-documents')
        self.chat_table = self.dynamodb.Table('knowledge-base-chat-history')

    def save_document(self, doc_data: Dict) -> str:
        """Save document metadata to DynamoDB"""
        doc_id = str(uuid.uuid4())
        item = {
            'document_id': doc_id,
            'file_hash': doc_data['file_hash'],
            'filename': doc_data['filename'],
            'upload_date': datetime.utcnow().isoformat(),
            'metadata': doc_data
        }
        self.documents_table.put_item(Item=item)
        return doc_id

    def get_document_by_hash(self, file_hash: str) -> Optional[Dict]:
        """Check if document exists by hash"""
        response = self.documents_table.query(
            IndexName='FileHashIndex',
            KeyConditionExpression='file_hash = :hash',
            ExpressionAttributeValues={':hash': file_hash}
        )
        items = response.get('Items', [])
        return items[0] if items else None

    def list_documents(self) -> List[Dict]:
        """List all documents"""
        response = self.documents_table.scan()
        return response.get('Items', [])

    def delete_document(self, doc_id: str) -> bool:
        """Delete document by ID"""
        try:
            self.documents_table.delete_item(Key={'document_id': doc_id})
            return True
        except Exception as e:
            print(f"Error deleting document: {e}")
            return False
```

#### 2. File Storage Migration

**Create S3 adapter** in `backend/utils/s3_storage.py`:

```python
import boto3
from botocore.exceptions import ClientError
import os

class S3Storage:
    def __init__(self, bucket_name: str = None):
        self.s3 = boto3.client('s3')
        self.bucket = bucket_name or os.environ.get('PDF_BUCKET_NAME')

    def upload_file(self, file_data: bytes, key: str) -> str:
        """Upload file to S3"""
        try:
            self.s3.put_object(
                Bucket=self.bucket,
                Key=key,
                Body=file_data,
                ContentType='application/pdf'
            )
            return f"s3://{self.bucket}/{key}"
        except ClientError as e:
            raise Exception(f"Upload failed: {e}")

    def download_file(self, key: str) -> bytes:
        """Download file from S3"""
        try:
            response = self.s3.get_object(Bucket=self.bucket, Key=key)
            return response['Body'].read()
        except ClientError as e:
            raise Exception(f"Download failed: {e}")

    def generate_presigned_url(self, key: str, expiration: int = 3600) -> str:
        """Generate pre-signed URL for file access"""
        try:
            url = self.s3.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket, 'Key': key},
                ExpiresIn=expiration
            )
            return url
        except ClientError as e:
            raise Exception(f"URL generation failed: {e}")
```

#### 3. Update Config for Lambda

**Modify `backend/config.py`**:

```python
import os
from dotenv import load_dotenv

# Only load .env in local development
if not os.environ.get('AWS_EXECUTION_ENV'):
    load_dotenv(override=True)

class Config:
    # ... existing config ...

    # Lambda-specific settings
    IS_LAMBDA = bool(os.environ.get('AWS_EXECUTION_ENV'))
    PDF_BUCKET_NAME = os.environ.get('PDF_BUCKET_NAME', 'knowledge-base-pdfs')
    DOCUMENTS_TABLE = os.environ.get('DOCUMENTS_TABLE', 'knowledge-base-documents')
    CHAT_TABLE = os.environ.get('CHAT_TABLE', 'knowledge-base-chat-history')
```

#### 4. Update App Initialization

**Modify `backend/app.py`**:

```python
def create_app():
    """Create and configure the FastAPI application"""
    Config.validate()

    app = FastAPI(
        title="PDF Processing and Knowledge Base API",
        description="API for PDF processing, knowledge base management, and chat functionality",
        version="1.0.0",
        max_request_size=10 * 1024 * 1024
    )

    # Lambda-specific: Skip cleanup on exit
    if not Config.IS_LAMBDA:
        import atexit
        atexit.register(cleanup_on_exit)

    # ... rest of configuration ...

    return app
```

### Testing Strategy

1. **Local Testing**: Use `sam local` for development
2. **Dev Deployment**: Deploy to a dev/test stack first
3. **Integration Tests**: Test all endpoints with real data
4. **Load Testing**: Use artillery or k6 to test under load
5. **Production Deployment**: Deploy to production after validation

### Rollback Plan

If deployment fails or issues occur:

```powershell
# Delete the stack (rollback)
aws cloudformation delete-stack --stack-name knowledge-base-api

# Or rollback to previous version
aws cloudformation rollback-stack --stack-name knowledge-base-api
```

## Advanced Features

### Multi-Region Deployment

Deploy to multiple regions for better latency:

```powershell
# Deploy to us-west-2
sam deploy --region us-west-2 --stack-name knowledge-base-api-west

# Deploy to eu-west-1
sam deploy --region eu-west-1 --stack-name knowledge-base-api-eu
```

### Custom Domain

Add a custom domain with Route53 + ACM:

```yaml
# In template.yaml
DomainName:
  Type: AWS::ApiGatewayV2::DomainName
  Properties:
    DomainName: api.yourdomain.com
    DomainNameConfigurations:
      - CertificateArn: arn:aws:acm:us-east-1:123456789012:certificate/abc123
```

### CI/CD Pipeline

Automate deployments with GitHub Actions:

```yaml
# .github/workflows/deploy.yml
name: Deploy to Lambda
on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: aws-actions/setup-sam@v2
      - name: SAM Deploy
        run: sam deploy --no-confirm-changeset
        env:
          AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
          AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
```

## Next Steps

1. ✅ Review this guide thoroughly
2. ✅ Set up AWS credentials
3. ✅ Create deployment bucket
4. ✅ Update `requirements.txt` with `mangum` and `boto3`
5. ✅ Migrate database code to DynamoDB
6. ✅ Migrate file storage to S3
7. ✅ Test locally with `sam local start-api`
8. ✅ Deploy to dev/test environment
9. ✅ Run integration tests
10. ✅ Deploy to production

## Support & Resources

- **AWS SAM Docs**: https://docs.aws.amazon.com/serverless-application-model/
- **FastAPI on Lambda**: https://fastapi.tiangolo.com/deployment/lambda/
- **Mangum Adapter**: https://mangum.io/
- **DynamoDB Guide**: https://docs.aws.amazon.com/dynamodb/

---

**Questions?** Review the troubleshooting section or check AWS CloudWatch logs for detailed error messages.
