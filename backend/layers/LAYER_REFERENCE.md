# Lambda Layer Quick Reference

## 📦 Layer Structure

```
Main Lambda (SafexpressOps-KnowledgeBase):
├── Layer 1: fastapi-core (~30MB)
├── Layer 2: ai-vectordb (~50MB)
├── Layer 3: pdf-processing (~20MB)
├── Layer 4: security-auth (~15MB)
└── Layer 5: numpy-layer (~25MB) [OPTIONAL]
Total: ~140-165MB ✅

Image Processor Lambda (SafexpressOps-ImageProcessor):
└── Layer 1: pymupdf-only (~240MB)
Total: ~240MB ✅
```

## 🛠️ Layer Dependencies Summary

### Layer 1: fastapi-core
```
✅ fastapi==0.115.5
✅ python-multipart==0.0.20
✅ pydantic==2.10.3
✅ pydantic-settings==2.6.1
✅ mangum==0.18.0
❌ uvicorn (NOT needed in Lambda)
```

### Layer 2: ai-vectordb
```
✅ openai==1.57.2
✅ weaviate-client==4.9.3
✅ httpx
✅ httpcore
✅ certifi
✅ validators
```

### Layer 3: pdf-processing
```
✅ pdfplumber==0.11.4
✅ pillow==10.3.0
✅ pdfminer.six==20250506
❌ PyMuPDF (moved to separate Lambda)
```

### Layer 4: security-auth
```
✅ PyJWT==2.10.1 (recommended)
OR python-jose[cryptography]==3.3.0 (alternative)
✅ cryptography==45.0.6
✅ python-dotenv==1.0.1
```

### Layer 5: numpy-layer (Optional)
```
✅ numpy==1.26.4
❌ openpyxl (not used - removed)
```

### Layer 6: pymupdf-only (Image Processor ONLY)
```
✅ PyMuPDF==1.24.0
✅ pillow==10.3.0
```

## 🔑 Key Points

### What Changed from Your Original Setup?

**Original Layer 1:**
```diff
  fastapi==0.115.5
- uvicorn[standard]==0.32.1  ❌ REMOVED (not needed in Lambda)
  python-multipart==0.0.20
  pydantic==2.10.3
  pydantic-settings==2.6.1
  mangum==0.18.0
```

**Original Layer 3:**
```diff
  pdfplumber==0.11.4
  pillow==10.3.0
  python-jose[cryptography]==3.3.0
  python-dotenv==1.0.1
+ pdfminer.six==20250506  ✅ ADDED (was implicit dependency)
```

**Original Layer 4:**
```diff
  numpy==1.26.4
- openpyxl==3.1.2  ❌ REMOVED (not used in your code)
```

**Original Layer 5 → Now Separate Lambda:**
```diff
- PyMuPDF==1.24.0  ❌ MOVED to dedicated Image Processor Lambda
```

### ⚠️ Important: boto3

**boto3 is NOT in any layer!**

Why? It's **already included in Lambda runtime** by default.

If you need a specific version:
```bash
# Add to a new layer
echo "boto3==1.34.0" > layers/aws-sdk/requirements.txt
```

## 📏 Size Estimates

| Layer | Original | Optimized | Savings |
|-------|----------|-----------|---------|
| FastAPI Core | ~50MB | ~30MB | -40% |
| AI VectorDB | ~50MB | ~50MB | 0% |
| PDF Processing | ~270MB | ~20MB | -93% ⭐ |
| Security Auth | ~15MB | ~15MB | 0% |
| Numpy | ~30MB | ~25MB | -17% |
| **Total Main Lambda** | **~415MB ❌** | **~140MB ✅** | **-66%** |

## 🚀 Deployment Commands

### Build All Layers
```bash
#!/bin/bash
# build-all-layers.sh

LAYERS=("fastapi-core" "ai-vectordb" "pdf-processing" "security-auth" "pymupdf-only")

for layer in "${LAYERS[@]}"; do
  echo "Building layer: $layer"
  cd "layers/$layer"
  
  # Create Dockerfile if not exists
  cat > Dockerfile <<EOF
FROM public.ecr.aws/lambda/python:3.11

COPY requirements.txt .
RUN pip install -r requirements.txt -t /asset

CMD ["cp", "-r", "/asset", "/output"]
EOF
  
  # Build with Docker
  docker build -t "$layer-layer" .
  
  # Create layer content
  mkdir -p layer-content/python
  docker run --rm -v "\$(pwd)/layer-content/python:/output" "$layer-layer" \
    sh -c "cp -r /asset/* /output/"
  
  # Zip layer
  cd layer-content
  zip -r "../$layer-layer.zip" python/
  cd ..
  
  echo "✅ Layer $layer built"
  cd ../..
done

echo "🎉 All layers built successfully!"
```

### Deploy Layer to AWS
```bash
#!/bin/bash
# deploy-layer.sh <layer-name>

LAYER_NAME=$1
LAYER_ZIP="${LAYER_NAME}-layer.zip"

aws lambda publish-layer-version \
  --layer-name "safexpress-${LAYER_NAME}" \
  --description "SafexpressOps ${LAYER_NAME} layer" \
  --zip-file "fileb://layers/${LAYER_NAME}/${LAYER_ZIP}" \
  --compatible-runtimes python3.11 \
  --compatible-architectures x86_64

echo "✅ Layer ${LAYER_NAME} deployed"
```

### Get Layer ARNs
```bash
#!/bin/bash
# get-layer-arns.sh

LAYERS=("fastapi-core" "ai-vectordb" "pdf-processing" "security-auth" "pymupdf-only")

echo "Layer ARNs:"
for layer in "${LAYERS[@]}"; do
  ARN=$(aws lambda list-layer-versions \
    --layer-name "safexpress-${layer}" \
    --max-items 1 \
    --query 'LayerVersions[0].LayerVersionArn' \
    --output text)
  echo "${layer}: ${ARN}"
done
```

## 🧹 Maintenance

### Update a Single Layer
```bash
# 1. Update requirements.txt
cd layers/fastapi-core
vim requirements.txt

# 2. Rebuild
./build-layer.sh fastapi-core

# 3. Deploy new version
./deploy-layer.sh fastapi-core

# 4. Get new ARN
aws lambda list-layer-versions \
  --layer-name safexpress-fastapi-core \
  --max-items 1

# 5. Update samconfig.toml with new ARN
# 6. Redeploy main Lambda
sam build --use-container
sam deploy
```

### Clean Up Old Layer Versions
```bash
#!/bin/bash
# cleanup-old-layers.sh

LAYER_NAME="safexpress-fastapi-core"

# Keep only latest 3 versions
aws lambda list-layer-versions --layer-name "$LAYER_NAME" \
  --query 'LayerVersions[3:].Version' \
  --output text | \
  xargs -I {} aws lambda delete-layer-version \
    --layer-name "$LAYER_NAME" \
    --version-number {}

echo "✅ Cleaned up old versions of $LAYER_NAME"
```

## 🔍 Debugging

### Check Layer Contents
```bash
# Download layer
aws lambda get-layer-version-by-arn \
  --arn arn:aws:lambda:region:account:layer:safexpress-fastapi-core:1 \
  --query 'Content.Location' \
  --output text | xargs curl -o layer.zip

# Extract and inspect
unzip layer.zip
ls -lh python/
```

### Test Layer Locally
```bash
# Create test Lambda
mkdir test-lambda
cd test-lambda

cat > test.py <<EOF
import sys
sys.path.insert(0, '/opt/python')

import fastapi
import pydantic

print(f"FastAPI: {fastapi.__version__}")
print(f"Pydantic: {pydantic.__version__}")
EOF

# Run with layer
docker run --rm \
  -v $(pwd)/layer-content/python:/opt/python:ro \
  -v $(pwd)/test.py:/var/task/test.py:ro \
  public.ecr.aws/lambda/python:3.11 \
  python test.py
```

## 📋 Checklist

### Before Deployment
- [ ] All layer requirements.txt files updated
- [ ] Layers built with Docker
- [ ] Layer sizes checked (all < 250MB)
- [ ] samconfig.toml updated with Layer ARNs
- [ ] Environment variables configured
- [ ] IAM permissions reviewed

### After Deployment
- [ ] Main Lambda deployed successfully
- [ ] Image Processor Lambda deployed successfully
- [ ] API Gateway endpoint accessible
- [ ] DynamoDB tables created
- [ ] S3 bucket created
- [ ] Test PDF upload and processing
- [ ] CloudWatch logs flowing
- [ ] Metrics dashboard created

## 🆘 Emergency Rollback

```bash
# Rollback to previous version
aws lambda update-function-configuration \
  --function-name SafexpressOps-KnowledgeBase \
  --layers \
    arn:aws:lambda:region:account:layer:fastapi-core:PREVIOUS_VERSION \
    arn:aws:lambda:region:account:layer:ai-vectordb:PREVIOUS_VERSION \
    ...
```
