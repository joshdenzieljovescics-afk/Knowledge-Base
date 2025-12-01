# Two-Lambda Architecture Deployment Guide

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│              API Gateway (HTTP API)                      │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────┐
│  Lambda 1: Main API (~150MB)                            │
│  - FastAPI + Mangum                                      │
│  - PDF text/table extraction (pdfplumber)               │
│  - Chat & vector search                                  │
│  - Design-heavy detection                                │
│                                                          │
│  Layers:                                                 │
│  1. FastAPI Core (~30MB)                                │
│  2. AI VectorDB (~50MB)                                 │
│  3. PDF Processing (~20MB)                              │
│  4. Security Auth (~15MB)                               │
│  5. Numpy (~25MB) - optional                            │
│                                                          │
│  When design-heavy PDF detected:                        │
│     └─> Invokes Lambda 2 ────────────┐                  │
└──────────────────────────────────────┼──────────────────┘
                                       │
                                       ▼
                    ┌──────────────────────────────────────┐
                    │ Lambda 2: Image Processor (~240MB)   │
                    │  - PyMuPDF only                      │
                    │  - Extract images with base64         │
                    │  - Returns processed images           │
                    │                                       │
                    │  Layer:                               │
                    │  1. PyMuPDF Layer (~240MB)           │
                    └──────────────────────────────────────┘
```

## 📦 Prerequisites

1. AWS CLI configured
2. SAM CLI installed
3. Docker installed (for layer building)
4. Python 3.11
5. AWS Account with appropriate permissions

## 🚀 Deployment Steps

### Step 1: Build Lambda Layers

#### Layer 1: FastAPI Core
```bash
cd backend/layers/fastapi-core
sam build --use-container
sam deploy --guided
```

#### Layer 2: AI VectorDB
```bash
cd ../ai-vectordb
sam build --use-container
sam deploy --guided
```

#### Layer 3: PDF Processing
```bash
cd ../pdf-processing
sam build --use-container
sam deploy --guided
```

#### Layer 4: Security Auth
```bash
cd ../security-auth
sam build --use-container
sam deploy --guided
```

#### Layer 5: PyMuPDF (For Image Processor ONLY)
```bash
cd ../pymupdf-only
sam build --use-container
sam deploy --guided
```

**Note:** Copy each layer ARN after deployment. You'll need them for the main deployment.

### Step 2: Update samconfig.toml

Update `backend/samconfig.toml` with your layer ARNs:

```toml
parameter_overrides = [
    "OpenAIAPIKey=your-openai-key",
    "WeaviateURL=your-weaviate-url",
    "WeaviateAPIKey=your-weaviate-key",
    "JWTSecretKey=your-jwt-secret",
    "PDFProcessingLayerArn=arn:aws:lambda:region:account:layer:pdf-processing:1",
    "AIVectorDBLayerArn=arn:aws:lambda:region:account:layer:ai-vectordb:1",
    "FastAPICoreLayerArn=arn:aws:lambda:region:account:layer:fastapi-core:1",
    "SecurityAuthLayerArn=arn:aws:lambda:region:account:layer:security-auth:1",
    "PyMuPDFLayerArn=arn:aws:lambda:region:account:layer:pymupdf-only:1"
]
```

### Step 3: Deploy Both Lambda Functions

```bash
cd backend
sam build --use-container
sam deploy --guided
```

This will deploy:
- `SafexpressOps-KnowledgeBase` (Main API)
- `SafexpressOps-ImageProcessor` (Image extraction)
- DynamoDB tables
- S3 bucket
- API Gateway

### Step 4: Test the Deployment

#### Test Main Lambda
```bash
# Get API endpoint from outputs
API_URL=$(aws cloudformation describe-stacks \
  --stack-name knowledge-base-api \
  --query 'Stacks[0].Outputs[?OutputKey==`KnowledgeBaseAPI`].OutputValue' \
  --output text)

echo "API URL: $API_URL"

# Test health endpoint
curl "${API_URL}health"
```

#### Test Image Processor Lambda
```bash
aws lambda invoke \
  --function-name SafexpressOps-ImageProcessor \
  --payload '{"operation":"extract_images","file_bytes_base64":"test","page_numbers":[0]}' \
  response.json

cat response.json
```

## 🔧 Configuration

### Environment Variables (Main Lambda)

```bash
OPENAI_API_KEY=sk-...
WEAVIATE_URL=https://...
WEAVIATE_API_KEY=...
JWT_SECRET_KEY=...
IS_LAMBDA=true
IMAGE_PROCESSOR_LAMBDA_ARN=arn:aws:lambda:...
DOCUMENTS_TABLE=safexpress-documents
CHAT_SESSIONS_TABLE=safexpress-chat-sessions
CHAT_MESSAGES_TABLE=safexpress-chat-messages
PDF_STORAGE_BUCKET=safexpress-pdf-storage-...
```

### IAM Permissions

Main Lambda needs:
- `lambda:InvokeFunction` on Image Processor
- `s3:*` on PDF storage bucket
- `dynamodb:*` on all tables

Image Processor needs:
- None (invoked by Main Lambda)

## 📊 Cost Optimization

### Lambda Pricing Considerations

**Main Lambda:**
- **Memory:** 3008 MB
- **Timeout:** 900s (15 min)
- **Concurrent executions:** Unlimited
- **Estimated cost:** $0.20 per 1000 requests (assuming 10s avg duration)

**Image Processor Lambda:**
- **Memory:** 2048 MB
- **Timeout:** 300s (5 min)
- **Concurrent executions:** 5 (limited to control costs)
- **Estimated cost:** $0.10 per 1000 requests (assuming 5s avg duration)

### Optimization Tips

1. **Use Provisioned Concurrency** for Main Lambda if you have predictable traffic
2. **Limit concurrent executions** on Image Processor (already set to 5)
3. **Cache frequently accessed PDFs** in S3 Intelligent-Tiering
4. **Use DynamoDB On-Demand billing** for unpredictable workloads

## 🐛 Troubleshooting

### Issue: "Module not found" in Main Lambda

**Cause:** Missing layer or wrong layer ARN

**Solution:**
```bash
# Check layer is attached
aws lambda get-function --function-name SafexpressOps-KnowledgeBase \
  --query 'Configuration.Layers'

# Verify layer ARNs in samconfig.toml
```

### Issue: Image Processor timeout

**Cause:** Large PDF with many images

**Solution:**
- Increase timeout (currently 300s)
- Process pages in batches
- Increase memory (currently 2048 MB)

### Issue: "Layer exceeds 250MB"

**Cause:** PyMuPDF layer too large

**Solution:**
```bash
# Strip debug symbols from layer
cd layers/pymupdf-only/layer-content/python
find . -name "*.so" -exec strip --strip-unneeded {} \;

# Remove unnecessary files
find . -name "*.pyc" -delete
find . -name "__pycache__" -delete

# Re-zip and deploy
```

### Issue: Main Lambda can't invoke Image Processor

**Cause:** Missing IAM permission

**Solution:**
Check SAM template includes:
```yaml
Policies:
  - LambdaInvokePolicy:
      FunctionName: !Ref ImageProcessorFunction
```

## 📈 Monitoring

### CloudWatch Metrics to Watch

**Main Lambda:**
- Invocations
- Duration
- Errors
- Concurrent executions
- Throttles

**Image Processor:**
- Invocations from Main Lambda
- Duration (should be < 10s typically)
- Memory usage
- Timeout errors

### CloudWatch Alarms

```bash
# Create alarm for Main Lambda errors
aws cloudwatch put-metric-alarm \
  --alarm-name kb-main-errors \
  --alarm-description "Main Lambda errors" \
  --metric-name Errors \
  --namespace AWS/Lambda \
  --statistic Sum \
  --period 300 \
  --evaluation-periods 1 \
  --threshold 10 \
  --comparison-operator GreaterThanThreshold \
  --dimensions Name=FunctionName,Value=SafexpressOps-KnowledgeBase

# Create alarm for Image Processor timeouts
aws cloudwatch put-metric-alarm \
  --alarm-name kb-image-timeouts \
  --alarm-description "Image processor timeouts" \
  --metric-name Duration \
  --namespace AWS/Lambda \
  --statistic Maximum \
  --period 300 \
  --evaluation-periods 1 \
  --threshold 290000 \
  --comparison-operator GreaterThanThreshold \
  --dimensions Name=FunctionName,Value=SafexpressOps-ImageProcessor
```

## 🔄 Updates & Rollbacks

### Update Main Lambda Code
```bash
cd backend
sam build --use-container
sam deploy
```

### Update Image Processor
```bash
# If only lambda_image_processor.py changed
sam build --use-container
sam deploy
```

### Rollback
```bash
# List previous versions
aws lambda list-versions-by-function \
  --function-name SafexpressOps-KnowledgeBase

# Update alias to previous version
aws lambda update-alias \
  --function-name SafexpressOps-KnowledgeBase \
  --name prod \
  --function-version <previous-version>
```

## 🧪 Local Testing

### Test Main Lambda Locally
```bash
cd backend
sam local start-api --warm-containers EAGER
```

### Test Image Processor Locally
```bash
# Create test event
cat > test_event.json <<EOF
{
  "operation": "extract_images",
  "file_bytes_base64": "<base64-encoded-pdf>",
  "page_numbers": [0]
}
EOF

# Invoke locally
sam local invoke ImageProcessorFunction -e test_event.json
```

## 📝 Migration from Single Lambda

### Before (Single Lambda with PyMuPDF)
- ❌ 420MB total size (exceeds limit)
- ❌ Slow cold starts (10-15s)
- ❌ Can't deploy

### After (Two Lambda Architecture)
- ✅ Main: 150MB (under limit)
- ✅ Image Processor: 240MB (under limit)
- ✅ Fast cold starts on main (3-5s)
- ✅ Image processor only invoked when needed
- ✅ Successfully deployed

## 🎯 Next Steps

1. ✅ Deploy layers
2. ✅ Deploy Lambda functions
3. ✅ Test end-to-end
4. ✅ Set up monitoring
5. ⬜ Configure CI/CD pipeline
6. ⬜ Load testing
7. ⬜ Production deployment
