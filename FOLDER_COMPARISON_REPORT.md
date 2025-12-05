# Knowledge-Base Folder Comparison Report

## Executive Summary

Comparison between `knowledge-base/` (Original) and `knowledge-base copy/` folders.

**Key Findings:**
- Most files are **IDENTICAL** between both folders
- The **"knowledge-base copy"** folder has more features:
  - Quota integration in chat services
  - LLM error handling with user-friendly popups
  - Expanded CORS origins for agent microservices
  - Additional utility scripts (check_db.py, security_audit.py)
- The **"knowledge-base"** folder has more debug data files (weaviate search results JSONs)

---

## Files with Differences

### 1. `app.py` - Main Application Entry Point

| Aspect | Original (`knowledge-base/`) | Copy (`knowledge-base copy/`) |
|--------|------------------------------|-------------------------------|
| **Lines** | 131 lines | 137 lines |
| **CORS Origins** | Basic: `5173, 5174, 3000, 3001` | Extended: `5173, 5174, 3000, 3001, 8000-8011` (all agent ports) |

**Difference Details:**
- **Copy** adds 10 additional CORS origins for agent microservices:
  ```python
  # Additional in copy:
  "http://localhost:8000",  # accounts
  "http://localhost:8001",  # accounts (alt)
  "http://localhost:8002",  # login-signup
  "http://localhost:8003",  # token-quota
  "http://localhost:8004",  # knowledge-base
  "http://localhost:8005",  # kb (alt)
  "http://localhost:8006",  # agents
  "http://localhost:8007",  # agents (alt)
  "http://localhost:8008",  # orchestrator
  "http://localhost:8009",  # orchestrator (alt)
  "http://localhost:8010",  # reserved
  "http://localhost:8011",  # token-quota-service
  ```

**Recommendation:** ✅ Use **Copy** version - supports multi-agent architecture

---

### 2. `api/chat_routes.py` - Chat API Endpoints

| Aspect | Original (`knowledge-base/`) | Copy (`knowledge-base copy/`) |
|--------|------------------------------|-------------------------------|
| **Lines** | 322 lines | 417 lines (+95) |
| **User ID Extraction** | Inline: `current_user.get("sub") or current_user.get("user_id")` | Helper function: `extract_user_id()` |
| **LLM Error Handling** | ❌ None | ✅ `LLMServiceException` import and handling |
| **Quota Endpoint** | ❌ None | ✅ `/chat/quota` endpoint for balance |
| **Error Response** | Basic HTTPException | JSONResponse with structured `is_llm_error` flag |

**Key Additions in Copy:**

1. **`extract_user_id()` helper function:**
   ```python
   def extract_user_id(current_user: dict) -> str:
       """Extract user ID from JWT payload with fallbacks."""
       return current_user.get("sub") or current_user.get("user_id") or current_user.get("email") or "anonymous"
   ```

2. **LLM Error Handling:**
   ```python
   from utils.llm_error_handler import LLMServiceException
   
   except LLMServiceException as e:
       return JSONResponse(
           status_code=e.status_code,
           content=e.to_dict()  # Includes is_llm_error: true for frontend popup
       )
   ```

3. **Quota Endpoint:**
   ```python
   @chat_router.get('/quota')
   async def get_quota_balance(current_user: dict = Depends(get_current_user)):
       """Get user's quota balance from token-quota-service."""
   ```

**Recommendation:** ✅ Use **Copy** version - better error handling and quota support

---

### 3. `services/chat_service.py` - Chat Service Logic

| Aspect | Original (`knowledge-base/`) | Copy (`knowledge-base copy/`) |
|--------|------------------------------|-------------------------------|
| **Lines** | 381 lines | 454 lines (+73) |
| **Quota Integration** | ❌ None | ✅ `QuotaClientSync` with `QUOTA_ENABLED` flag |
| **Token Estimation** | ❌ None | ✅ `_estimate_tokens()` method |
| **LLM Error Handling** | Basic exception | ✅ `is_llm_error()` check with `LLMServiceException` |
| **Usage Reporting** | ❌ None | ✅ Reports to quota service after LLM call |

**Key Additions in Copy:**

1. **Quota Client Integration:**
   ```python
   from utils.quota_client import QuotaClientSync
   
   QUOTA_ENABLED = os.getenv("QUOTA_ENABLED", "true").lower() == "true"
   quota_client = QuotaClientSync() if QUOTA_ENABLED else None
   ```

2. **Token Estimation Method:**
   ```python
   def _estimate_tokens(self, text: str) -> int:
       """Estimate tokens for quota checking (before LLM call)."""
       return len(text) // 4  # Rough approximation
   ```

3. **`_generate_response()` includes user_id parameter:**
   ```python
   def _generate_response(self, messages, session_id, user_id=None):
       # ... generates response ...
       # After getting response, report to quota service:
       if QUOTA_ENABLED and quota_client and user_id:
           quota_client.report(
               user_id=user_id,
               service="knowledge-base",
               model=model,
               input_tokens=response.usage.prompt_tokens,
               output_tokens=response.usage.completion_tokens
           )
   ```

4. **LLM Error Handling:**
   ```python
   from utils.llm_error_handler import is_llm_error, handle_llm_error, LLMServiceException
   
   except Exception as e:
       if is_llm_error(e):
           llm_error = handle_llm_error(e, context="chat completion")
           raise LLMServiceException(llm_error)
       raise
   ```

**Recommendation:** ✅ Use **Copy** version - has quota tracking and better error handling

---

## Identical Files (No Differences)

The following files are **IDENTICAL** in both folders:

### API Routes
- ✅ `api/kb_routes.py` (544 lines) - Knowledge base endpoints
- ✅ `api/pdf_routes.py` - PDF processing endpoints
- ✅ `api/admin_routes.py` (348 lines) - Admin endpoints
- ✅ `api/routes.py` - Route registration
- ✅ `api/__init__.py`

### Services
- ✅ `services/query_processor.py` (330 lines) - Query processing and reranking
- ✅ `services/openai_service.py` - OpenAI API calls
- ✅ `services/weaviate_search_service.py` (306 lines) - Vector search
- ✅ `services/chunking_service.py` - PDF chunking
- ✅ `services/pdf_service.py` - PDF parsing
- ✅ `services/weaviate_service.py` - Weaviate operations
- ✅ `services/context_manager.py` - Context management
- ✅ `services/anchoring_service.py` - Coordinate anchoring

### Utils
- ✅ `utils/llm_error_handler.py` (290 lines) - LLM error handling
- ✅ `utils/quota_client.py` (251 lines) - Quota service client
- ✅ `utils/kb_logger.py` - Logging utilities
- ✅ `utils/token_tracker.py` - Token tracking
- ✅ `utils/text_utils.py` - Text utilities
- ✅ `utils/file_utils.py` - File utilities
- ✅ `utils/coordinate_utils.py` - PDF coordinates

### Database
- ✅ `database/document_db.py` - Document database
- ✅ `database/chat_db.py` - Chat sessions database
- ✅ `database/weaviate_client.py` - Weaviate client
- ✅ `database/operations.py` - Database operations
- ✅ `database/document_validator.py` - Validation
- ✅ `database/kb_logs_db.py` - Logging database

### Configuration
- ✅ `config.py` - Configuration settings

### Middleware
- ✅ `middleware/security_middleware.py` - Security
- ✅ `middleware/jwt_middleware.py` - JWT auth

### Models
- ✅ `models/schemas.py` - Pydantic schemas

---

## Files Only in Original (`knowledge-base/`)

| File | Description |
|------|-------------|
| `image_context.json` | Image context data (debug file) |
| `image_only_chunks.json` | Image chunks data (debug file) |
| `weaviate_search_results_*.json` | 14 search result debug files (dates: Nov 24 - Dec 4) |

---

## Files Only in Copy (`knowledge-base copy/`)

| File | Description | Purpose |
|------|-------------|---------|
| `check_db.py` | Database inspection script | Utility for checking SQLite tables and data |
| `security_audit.py` | Security audit script | Checks for PII/sensitive data in databases |

**check_db.py Contents:**
- Inspects `kb_logs.db` for chat session logs
- Shows document processing logs
- Displays recent log entries with timing data

**security_audit.py Contents:**
- Audits all SQLite databases for sensitive columns
- Checks for PII patterns (user_id, email, session_id, etc.)
- Provides security analysis summary
- Reports on data storage practices

---

## Recommendations

### Use the `knowledge-base copy/` Folder

The "copy" folder is the **more complete** version with:

1. ✅ **Quota Integration** - Tracks token usage per user
2. ✅ **LLM Error Handling** - User-friendly error popups
3. ✅ **Extended CORS** - Supports multi-agent architecture
4. ✅ **Security Audit Tools** - check_db.py, security_audit.py
5. ✅ **Helper Functions** - Cleaner code with `extract_user_id()`

### Files to Migrate from Original

If you want the debug data:
- `image_context.json`
- `image_only_chunks.json`  
- `weaviate_search_results_*.json` (14 files - consider if needed)

### Suggested Action

1. Rename `knowledge-base` → `knowledge-base-old`
2. Rename `knowledge-base copy` → `knowledge-base`
3. Copy any needed JSON debug files from old to new
4. Delete `knowledge-base-old` after verification

---

## Version Control Note

If these folders are tracked in git, consider using the copy version as the main branch since it has more features implemented.

---

*Generated: $(date)*
*Comparison Tool: GitHub Copilot*
