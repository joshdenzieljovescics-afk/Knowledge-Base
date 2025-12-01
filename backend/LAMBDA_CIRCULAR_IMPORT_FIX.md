# Lambda Circular Import Fix - Summary

## Root Cause
The circular import chain was:
```
lambda_handler → app.py → config.py (module-level adapter imports)
                       → routes → services → core → config (already partially initialized!)
```

## Files That Need to Be Replaced in Lambda

### 1. `config.py` - CRITICAL CHANGE
**Change:** Removed module-level adapter imports. Added lazy getter functions.

**Key changes:**
- Removed: `from database.dynamodb_adapter import get_documents_adapter` at module level
- Removed: `documents_db = get_documents_adapter()` at module level  
- Added: `get_documents_db()` lazy getter function
- Added: `get_chat_db()` lazy getter function

**How to use in other files:**
```python
# OLD (causes circular import):
from config import documents_db, chat_db

# NEW (lazy loading):
from config import get_documents_db, get_chat_db
doc_db = get_documents_db()  # Call inside function, not at module level
```

### 2. `services/pdf_service.py` - CRITICAL CHANGE
**Change:** Moved `from config import Config` from module level to inside functions.

**Key changes:**
- Removed: `from config import Config` at top of file
- Added: `from config import Config` inside `parse_and_chunk_pdf_file()` function

### 3. `services/chat_service.py` - CRITICAL CHANGE  
**Change:** Use lazy getter for chat adapter.

**Key changes:**
- Changed: `from config import chat_db` to `from config import get_chat_db`
- Changed: `self.chat_db = chat_db` to `self.chat_db = get_chat_db()`

### 4. `api/kb_routes.py` - CRITICAL CHANGE
**Change:** Use lazy getter for documents database.

**Key changes:**
- Removed: `from config import documents_db`
- Added: Helper function `_get_document_database()` that calls `from config import get_documents_db`
- Changed all `DocumentDatabase()` calls to `_get_document_database()`

### 5. `database/dynamodb_adapter.py` - Already Fixed
The version you have already has lazy `from config import Config` inside `__init__`. ✅

### 6. `database/dynamodb_chat.py` - Already Fixed
The version you have already has lazy `from config import Config` inside `__init__`. ✅

## Files That Don't Need Changes
- `lambda_handler.py` - Simple, just imports app
- `app.py` - Imports Config.validate() which is safe
- `api/routes.py` - Just registers routers
- `api/pdf_routes.py` - Uses Config.IS_LAMBDA correctly
- `api/chat_routes.py` - No direct config imports at module level
- `core/pdf_extractor.py` - Has lazy Config import inside function
- All other service files

## Quick Replacement Guide

Replace these files in your Lambda deployment (in this order):

1. **config.py** → Use `config_lambda_fixed.py`
2. **services/pdf_service.py** → Use `services/pdf_service_lambda_fixed.py`
3. **services/chat_service.py** → Use `services/chat_service_lambda_fixed.py`
4. **api/kb_routes.py** → Use `api/kb_routes_lambda_fixed.py`

## Testing
After deploying, the Lambda should start without circular import errors.
Test with a simple health check request to `/` endpoint.
