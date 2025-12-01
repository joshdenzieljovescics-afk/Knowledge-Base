# Optimized Lambda Layer Structure

## Layer 1: FastAPI Core (~30MB)
```txt
fastapi==0.115.5
python-multipart==0.0.20
pydantic==2.10.3
pydantic-settings==2.6.1
mangum==0.18.0
starlette
anyio
sniffio
idna
```

**Notes:**
- ❌ Remove `uvicorn` - NOT needed in Lambda (Lambda provides runtime)
- ✅ `mangum` is REQUIRED for Lambda integration

## Layer 2: AI & VectorDB (~50MB)
```txt
openai==1.57.2
weaviate-client==4.9.3
httpx
httpcore
certifi
validators
```

**Notes:**
- ✅ Add `validators` (used by weaviate internally)
- ✅ Include HTTP deps for API calls

## Layer 3: AWS SDK (~30MB)
```txt
boto3
botocore
```

**Notes:**
- 🔥 **CRITICAL:** boto3 is available in Lambda runtime by default
- ⚠️ Only include if you need a specific version
- Otherwise, rely on Lambda's built-in boto3

## Layer 4: PDF Processing (LIGHTWEIGHT) (~20MB)
```txt
pdfplumber==0.11.4
pillow==10.3.0
pdfminer.six==20250506
pypdfium2==4.30.0
```

**Notes:**
- ✅ pdfplumber for text/tables
- ✅ pillow for image processing
- ❌ Remove PyMuPDF - too large!
- ✅ pdfminer.six comes with pdfplumber

## Layer 5: Security & Auth (~15MB)
```txt
python-jose[cryptography]==3.3.0
PyJWT==2.10.1
cryptography==45.0.6
python-dotenv==1.0.1
```

**Notes:**
- ⚠️ You're using BOTH python-jose AND PyJWT - pick one!
- Recommended: Use PyJWT only (smaller, faster)

## Layer 6 (Optional): Data Processing (~25MB)
```txt
numpy==1.26.4
```

**Notes:**
- ❌ Remove `openpyxl` if not actively used
- ✅ Keep numpy only if needed for calculations

---

## 🎯 Total Size Estimate
- **Without PyMuPDF:** ~170MB (well under 250MB limit ✅)
- **With PyMuPDF:** ~420MB (exceeds limit ❌)

---

## 🚀 Lambda-Specific Recommendations

### 1. Use Lambda Runtime boto3
```python
# In your Lambda function - boto3 is already available
import boto3  # Already in Lambda runtime!
```

### 2. Remove PyMuPDF, Replace with pdfplumber
Update `backend/core/pdf_extractor.py`:

```python
# BEFORE (with PyMuPDF)
def extract_images_with_bbox_pymupdf(file_bytes, page_number):
    with fitz.open(stream=file_bytes, filetype="pdf") as doc:
        # ... PyMuPDF code

# AFTER (with pdfplumber)
def extract_images_with_bbox_pdfplumber(page, page_number):
    images = []
    for img_index, img in enumerate(page.images):
        images.append({
            "id": f"p{page_number+1}-img-{img_index}",
            "type": "image",
            "box": {
                "l": img["x0"],
                "t": img["top"],
                "r": img["x1"],
                "b": img["bottom"]
            },
            "page": page_number + 1,
            # Note: Skip image_b64 or extract from img['stream']
        })
    return images
```

### 3. Consolidate JWT Libraries
Choose ONE:
- **Option A:** Use `PyJWT` only (recommended - lighter)
- **Option B:** Use `python-jose` only

Current code uses both - consolidate to reduce size.

### 4. Lambda Handler Structure
```python
# backend/lambda_handler.py
from mangum import Mangum
from app import app

# Mangum adapter for AWS Lambda
handler = Mangum(app, lifespan="off")
```

---

## 📋 Layer Build Commands

### Build layers locally with Docker:
```bash
# Layer 1: FastAPI Core
cd backend/layers/fastapi-core
docker build -t fastapi-core-layer .
docker run --rm -v ${PWD}/layer-content:/output fastapi-core-layer

# Layer 2: AI VectorDB
cd ../ai-vectordb
docker build -t ai-vectordb-layer .
docker run --rm -v ${PWD}/layer-content:/output ai-vectordb-layer

# Etc...
```

### Check layer sizes:
```bash
cd backend/layers
for layer in */layer-content; do
  size=$(du -sh "$layer" 2>/dev/null | cut -f1)
  echo "$layer: $size"
done
```

---

## ⚠️ Common Issues & Solutions

### Issue 1: "Module not found" in Lambda
**Cause:** Missing dependency in layers  
**Solution:** Add to appropriate layer requirements.txt

### Issue 2: Layer exceeds 250MB
**Cause:** PyMuPDF or large binaries  
**Solution:** 
- Remove PyMuPDF, use pdfplumber
- Strip debug symbols: `strip --strip-unneeded *.so`
- Remove __pycache__: `find . -name "*.pyc" -delete`

### Issue 3: Cold start timeout
**Cause:** Too many heavy imports  
**Solution:**
- Lazy load heavy modules
- Use provisioned concurrency
- Reduce layer count

### Issue 4: Import conflicts
**Cause:** Version mismatch between layers  
**Solution:** Pin exact versions in all requirements.txt
