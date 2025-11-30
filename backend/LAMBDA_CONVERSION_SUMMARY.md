# Lambda Conversion Summary

## What Was Created

I've created a complete AWS Lambda deployment setup for your Knowledge Base application. Here's everything that was added:

### 📄 Core Files Created

1. **[lambda_handler.py](lambda_handler.py)** - Lambda entry point
   - Wraps your FastAPI app with Mangum adapter
   - Makes your app compatible with AWS Lambda/API Gateway

2. **[template.yaml](template.yaml)** - AWS SAM infrastructure template
   - Defines Lambda function configuration
   - Sets up API Gateway for HTTP routing
   - Creates DynamoDB tables for data storage
   - Creates S3 bucket for PDF storage
   - Configures CloudWatch logging
   - Sets up CORS and security

3. **[samconfig.toml](samconfig.toml)** - Deployment configuration
   - Pre-configured deployment settings
   - Environment variables and parameters
   - S3 bucket for deployment artifacts

### 📚 Documentation

4. **[LAMBDA_DEPLOYMENT_GUIDE.md](LAMBDA_DEPLOYMENT_GUIDE.md)** - Comprehensive deployment guide
   - Complete prerequisites and setup
   - Step-by-step deployment instructions
   - Architecture changes explained
   - Migration strategy from SQLite to DynamoDB
   - Migration strategy from local files to S3
   - Monitoring and troubleshooting
   - Cost optimization tips
   - Production checklist

5. **[LAMBDA_QUICK_START.md](LAMBDA_QUICK_START.md)** - Quick reference guide
   - Fast deployment commands
   - Common tasks
   - Troubleshooting shortcuts
   - Production checklist

6. **[LAMBDA_CONVERSION_SUMMARY.md](LAMBDA_CONVERSION_SUMMARY.md)** - This file
   - Overview of all changes
   - What to do next

### 🔧 Adapter Code

7. **[database/dynamodb_adapter.py](database/dynamodb_adapter.py)** - DynamoDB adapter
   - Replaces SQLite operations with DynamoDB
   - Document metadata storage
   - Chat history storage
   - Same interface as existing database operations

8. **[utils/s3_storage.py](utils/s3_storage.py)** - S3 storage adapter
   - Replaces local file storage with S3
   - PDF upload/download operations
   - Pre-signed URL generation
   - File management utilities

### 🚀 Automation Scripts

9. **[deploy.ps1](deploy.ps1)** - PowerShell deployment script
   - Automated build and deployment
   - Local testing support
   - Log streaming
   - Stack management
   - API testing

### 📦 Dependencies Updated

10. **[requirements.txt](requirements.txt)** - Updated with Lambda dependencies
    - Added `mangum` - ASGI to AWS Lambda adapter
    - Added `boto3` - AWS SDK for Python
    - Added `botocore` - Core AWS SDK functionality

## Architecture Changes Overview

### Before (Traditional Server)
```
┌──────────────┐
│   FastAPI    │
│      App     │
└──────┬───────┘
       │
       ├─► SQLite Database (local file)
       ├─► File Storage (local disk)
       └─► Running on: uvicorn server (port 8009)
```

### After (Serverless Lambda)
```
┌────────────────┐
│  API Gateway   │ ◄── HTTPS endpoint
└────────┬───────┘
         │
    ┌────▼────┐
    │ Lambda  │ ◄── Your FastAPI app
    │Function │
    └────┬────┘
         │
         ├─► DynamoDB (serverless database)
         ├─► S3 (cloud file storage)
         └─► Weaviate (unchanged)
```

## What You Need to Do

### Immediate Actions (Required Before Deployment)

1. **Install AWS Tools** (if not already installed)
   ```powershell
   choco install awscli
   choco install aws-sam-cli
   ```

2. **Configure AWS Credentials**
   ```powershell
   aws configure
   ```

3. **Create S3 Deployment Bucket**
   ```powershell
   aws s3 mb s3://knowledge-base-deployment-artifacts
   ```

4. **Update samconfig.toml**
   - Replace placeholder values with your actual:
     - OpenAI API key
     - Weaviate URL and API key
     - JWT secret key
     - Allowed CORS origins
     - S3 bucket name

### Code Migration (Optional but Recommended)

To fully utilize Lambda features, you'll need to migrate from SQLite and local file storage:

#### Option 1: Quick Deploy (Test First)
Deploy as-is to test, migrate database later:
- SQLite will work but data won't persist between Lambda executions
- Local file operations will fail

#### Option 2: Full Migration (Recommended)
Migrate to DynamoDB and S3 before deploying:

**Database Migration Steps:**

1. Update your database imports:
   ```python
   # Before
   from database.operations import save_document, get_document

   # After
   from database.dynamodb_adapter import get_dynamodb_adapter
   db = get_dynamodb_adapter()
   ```

2. Replace SQLite calls with DynamoDB calls:
   ```python
   # Before
   doc_id = save_document(doc_data)

   # After
   db = get_dynamodb_adapter()
   doc_id = db.save_document(doc_data)
   ```

**File Storage Migration Steps:**

1. Update file storage imports:
   ```python
   # Before
   with open(f'outputs/{filename}', 'wb') as f:
       f.write(file_data)

   # After
   from utils.s3_storage import get_s3_storage
   s3 = get_s3_storage()
   s3_key = s3.upload_file(file_data, filename)
   ```

2. Update config.py to detect Lambda environment:
   ```python
   import os

   class Config:
       IS_LAMBDA = bool(os.environ.get('AWS_EXECUTION_ENV'))
       PDF_BUCKET_NAME = os.environ.get('PDF_BUCKET_NAME')
   ```

## Deployment Process

### First-Time Deployment (Recommended)

Use the automated script:

```powershell
cd backend
.\deploy.ps1 -Guided
```

This will:
1. Check prerequisites
2. Build the application
3. Guide you through deployment settings
4. Deploy to AWS
5. Show you the API endpoint

### Subsequent Deployments

```powershell
cd backend
.\deploy.ps1
```

### Testing Locally Before Deployment

```powershell
cd backend
.\deploy.ps1 local
```

This starts a local API Gateway emulator at `http://localhost:3000`

## What Changes in Your Application

### Environment Detection

Your app will automatically detect if it's running in Lambda:

```python
import os

# Check if running in Lambda
is_lambda = bool(os.environ.get('AWS_EXECUTION_ENV'))

if is_lambda:
    # Use DynamoDB and S3
    from database.dynamodb_adapter import get_dynamodb_adapter
    from utils.s3_storage import get_s3_storage
else:
    # Use SQLite and local files (development)
    from database.operations import *
```

### API Endpoint Changes

**Before:**
```
http://localhost:8009/api/endpoint
```

**After:**
```
https://abc123xyz.execute-api.us-east-1.amazonaws.com/prod/api/endpoint
```

You'll need to update your frontend to use the new endpoint.

### Environment Variables

Now managed through AWS:
- Set in `template.yaml` or `samconfig.toml`
- Can use AWS Secrets Manager for sensitive values
- No `.env` file needed in Lambda

## Cost Implications

### Lambda Pricing

**Free Tier (First 12 months):**
- 1M requests/month
- 400,000 GB-seconds/month

**After Free Tier:**
- Requests: $0.20 per 1M requests
- Compute: $0.0000166667 per GB-second

**Example Monthly Cost:**
- 10,000 requests/month
- 30 seconds average per request
- 3GB memory

```
Requests: 10,000 × $0.0000002 = $0.002
Compute: 10,000 × 30s × 3GB × $0.0000166667 = $15.00
Total: ~$15/month
```

### Other AWS Services

- **DynamoDB**: Free tier 25GB storage, 25 read/write units
- **S3**: $0.023/GB storage, $0.0004/1000 requests
- **API Gateway**: $1.00 per million requests
- **CloudWatch Logs**: $0.50/GB ingested

**Estimated Total:** $15-30/month for moderate usage

## Monitoring After Deployment

### View Logs

```powershell
# Stream live logs
.\deploy.ps1 logs

# Or directly with SAM
sam logs --stack-name knowledge-base-api --tail
```

### Check Stack Status

```powershell
.\deploy.ps1 info
```

### Test API

```powershell
.\deploy.ps1 test
```

### AWS Console

1. **CloudWatch**: Monitor logs and metrics
   - Go to CloudWatch → Log Groups → `/aws/lambda/knowledge-base-api`

2. **Lambda**: View function configuration
   - Go to Lambda → Functions → `knowledge-base-api`

3. **API Gateway**: View API configuration
   - Go to API Gateway → Your API → Routes

4. **DynamoDB**: View database tables
   - Go to DynamoDB → Tables

## Rollback Strategy

If something goes wrong:

```powershell
# Delete entire stack
.\deploy.ps1 delete

# Or manually
aws cloudformation delete-stack --stack-name knowledge-base-api
```

This removes:
- Lambda function
- API Gateway
- DynamoDB tables
- S3 bucket
- CloudWatch logs
- All related resources

## Next Steps

1. ✅ Review this summary
2. ✅ Read [LAMBDA_QUICK_START.md](LAMBDA_QUICK_START.md) for commands
3. ✅ Read [LAMBDA_DEPLOYMENT_GUIDE.md](LAMBDA_DEPLOYMENT_GUIDE.md) for details
4. ✅ Install AWS CLI and SAM CLI
5. ✅ Configure AWS credentials
6. ✅ Update [samconfig.toml](samconfig.toml) with your settings
7. ✅ (Optional) Migrate database code to DynamoDB
8. ✅ (Optional) Migrate file storage to S3
9. ✅ Test locally: `.\deploy.ps1 local`
10. ✅ Deploy to AWS: `.\deploy.ps1 -Guided`
11. ✅ Update frontend with new API endpoint
12. ✅ Test deployed application
13. ✅ Set up monitoring and alerts
14. ✅ Configure production settings

## Troubleshooting

### Common Issues

**Build fails:**
```powershell
# Clean and rebuild
rm -rf .aws-sam
sam build
```

**Deployment timeout:**
- Increase timeout in template.yaml (already set to 900s)

**Package too large:**
- Use Lambda Layers (instructions in deployment guide)

**Can't connect to database:**
- Check DynamoDB table names in template.yaml
- Verify IAM permissions

**Files not uploading:**
- Check S3 bucket name in environment variables
- Verify S3 bucket exists

### Getting Help

1. Check logs: `.\deploy.ps1 logs`
2. Check CloudWatch in AWS Console
3. Review [LAMBDA_DEPLOYMENT_GUIDE.md](LAMBDA_DEPLOYMENT_GUIDE.md)
4. Check AWS documentation
5. Review CloudFormation events in AWS Console

## Benefits of Lambda Deployment

✅ **Auto-scaling**: Handles any traffic volume
✅ **Pay-per-use**: Only pay for actual usage
✅ **No maintenance**: AWS manages infrastructure
✅ **High availability**: Built-in redundancy
✅ **Global deployment**: Deploy to multiple regions
✅ **Integrated monitoring**: CloudWatch logs and metrics
✅ **Security**: IAM roles, VPC support, encryption

## Considerations

⚠️ **Cold starts**: First request may be slower (~2-5 seconds)
⚠️ **Execution limits**: 15-minute max timeout
⚠️ **Memory limits**: 10GB max
⚠️ **Local storage**: Only /tmp available (512MB-10GB)
⚠️ **Stateless**: No persistent local state

## Files You Can Ignore/Delete After Migration

Once fully migrated to Lambda:

- `app_original_backup.py` (backup, not needed)
- `cleanup_databases.py` (SQLite specific)
- `test_*.py` (local testing scripts)
- `*.db` files (SQLite databases)
- `outputs/` directory (local file storage)

Keep for local development:
- `.env` file (for local testing)
- All other Python files
- `requirements.txt`

## Summary

You now have a complete serverless deployment setup for your Knowledge Base application. The FastAPI app will run on AWS Lambda with:

- **Managed infrastructure** via CloudFormation
- **Serverless compute** via Lambda
- **NoSQL database** via DynamoDB
- **File storage** via S3
- **API routing** via API Gateway
- **Monitoring** via CloudWatch

All infrastructure is defined as code in `template.yaml` and can be deployed with a single command.

---

**Ready to deploy?** Start with the [LAMBDA_QUICK_START.md](LAMBDA_QUICK_START.md) guide!
