# Backend Refactoring Plan

## Executive Summary

This document outlines a comprehensive restructuring plan for `app.py` (2446 lines) into a clean, maintainable, and professional backend architecture. The file currently mixes concerns including API routes, PDF processing, AI integration, database operations, and utility functions.

## Current State Analysis

### File Statistics
- **Total Lines**: 2446
- **Main Components**:
  - Flask API setup and routes (3 endpoints)
  - OpenAI client configuration
  - Weaviate vector database operations
  - PDF extraction and parsing (pdfplumber + PyMuPDF)
  - AI-powered chunking and analysis
  - Text matching and anchoring algorithms
  - Large commented-out code blocks (OCR/CV features)

### Identified Issues
1. ❌ Single monolithic file with mixed concerns
2. ❌ API logic mixed with business logic
3. ❌ No separation between services and utilities
4. ❌ Hardcoded configuration values
5. ❌ Large chunks of commented code (500+ lines)
6. ❌ No clear module boundaries
7. ❌ Difficult to test individual components
8. ❌ No type hints or comprehensive documentation

## Proposed Architecture

```
backend/
├── app.py                          # Flask app initialization & route registration only
├── requirements.txt                # Dependencies
├── config.py                       # Configuration management
├── .env                           # Environment variables
│
├── api/                           # API Layer (Flask routes)
│   ├── __init__.py
│   ├── routes.py                  # Route definitions
│   ├── pdf_routes.py              # PDF-related endpoints
│   └── kb_routes.py               # Knowledge base endpoints
│
├── services/                      # Business Logic Layer
│   ├── __init__.py
│   ├── pdf_service.py             # PDF processing orchestration
│   ├── chunking_service.py        # AI chunking logic
│   ├── anchoring_service.py       # Coordinate anchoring
│   ├── weaviate_service.py        # Vector DB operations
│   └── openai_service.py          # OpenAI API interactions
│
├── core/                          # Core Processing Logic
│   ├── __init__.py
│   ├── pdf_extractor.py           # Low-level PDF extraction
│   ├── text_processor.py          # Text processing utilities
│   ├── image_processor.py         # Image handling
│   └── table_processor.py         # Table extraction
│
├── utils/                         # Utility Functions
│   ├── __init__.py
│   ├── text_utils.py              # Text normalization, matching
│   ├── coordinate_utils.py        # Bounding box calculations
│   ├── file_utils.py              # File I/O operations
│   └── validators.py              # Input validation
│
├── models/                        # Data Models & Schemas
│   ├── __init__.py
│   ├── chunk.py                   # Chunk data model
│   ├── document.py                # Document metadata model
│   ├── schemas.py                 # JSON schemas
│   └── enums.py                   # Enumerations (chunk types, etc.)
│
├── database/                      # Database Layer
│   ├── __init__.py
│   ├── weaviate_client.py         # Weaviate connection management
│   └── operations.py              # CRUD operations
│
└── tests/                         # Unit tests (to be created)
    ├── __init__.py
    ├── test_pdf_service.py
    ├── test_chunking.py
    └── test_utils.py
```

## Detailed File Breakdown

### 1. **app.py** (New - ~50 lines)
**Purpose**: Application entry point and initialization

**Contents**:
- Flask app creation
- CORS configuration
- Route blueprint registration
- Error handler registration
- Application startup logic

**Example Structure**:
```python
from flask import Flask
from flask_cors import CORS
from api.routes import register_routes
from config import Config

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    CORS(app)
    
    # Register blueprints
    register_routes(app)
    
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, port=8009)
```

---

### 2. **config.py** (~50 lines)
**Purpose**: Centralized configuration management

**Contents**:
- Environment variable loading
- Configuration classes (Dev, Prod, Test)
- OpenAI API settings
- Weaviate connection settings
- File paths and constants

**Example Structure**:
```python
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # OpenAI
    OPENAI_API_KEY = os.environ.get("OPENAI_APIKEY")
    OPENAI_MODEL = "gpt-4o"
    
    # Weaviate
    WEAVIATE_URL = os.environ.get("WEAVIATE_URL")
    WEAVIATE_API_KEY = os.environ.get("WEAVIATE_API_KEY")
    
    # Processing
    MAX_CHUNK_SIZE = 1000
    BATCH_SIZE = 100
    
    # File paths
    OUTPUT_DIR = "outputs"
    DEBUG = True
```

---

### 3. **api/routes.py** (~100 lines)
**Purpose**: Route definitions and request/response handling

**Functions to Include**:
- `/parse-pdf` (POST) - Parse and chunk PDF
- `/upload-to-kb` (POST) - Upload to knowledge base
- `/list-kb` (GET) - List KB entries
- Error handlers

**Responsibilities**:
- Request validation
- Response formatting
- HTTP status codes
- Error handling

**No business logic** - delegates to services

---

### 4. **services/pdf_service.py** (~200 lines)
**Purpose**: High-level PDF processing orchestration

**Functions from app.py**:
- `parse_and_chunk_pdf()` logic (orchestration only)
- `process_text_only()`
- `process_images_only()`
- `merge_text_and_image_chunks()`
- `is_design_heavy_simple()`

**Responsibilities**:
- Coordinate PDF extraction pipeline
- Decide processing strategy (standard vs design-heavy)
- Manage processing workflow
- Call appropriate extractors and processors

---

### 5. **services/chunking_service.py** (~150 lines)
**Purpose**: AI-powered chunking logic

**Functions from app.py**:
- OpenAI chunking calls
- JSON schema definitions
- Prompt engineering
- Chunk creation and validation

**Key Constant**:
- `JSON_SCHEMA` definition
- Chunking prompts

---

### 6. **services/anchoring_service.py** (~300 lines)
**Purpose**: Anchor AI chunks to PDF coordinates

**Functions from app.py**:
- `_anchor_chunks_to_pdf()`
- `_match_chunk_to_lines_with_exclusion()`
- `_is_page_break_continuation()`
- `_lines_are_continuous()`
- `_calculate_chunk_box()`
- `_calculate_match_score()`
- `find_best_matching_table()`
- `calculate_table_similarity()`

**Responsibilities**:
- Match text chunks to PDF lines
- Handle cross-page continuations
- Calculate bounding boxes
- Table matching logic

---

### 7. **services/weaviate_service.py** (~150 lines)
**Purpose**: Weaviate operations and knowledge base management

**Functions from app.py**:
- `insert_document()`
- `delete_document_and_chunks()`
- `replace_document()`
- `query_weaviate()`
- `rerank_with_openai()`

**Responsibilities**:
- Document CRUD operations
- Chunk insertion
- Vector search
- Query reranking

---

### 8. **services/openai_service.py** (~100 lines)
**Purpose**: OpenAI API interactions

**Functions**:
- Create OpenAI client
- Image analysis
- Text generation
- Reranking
- Error handling and retries

**Responsibilities**:
- Manage OpenAI client
- Handle API calls
- Format prompts
- Parse responses

---

### 9. **core/pdf_extractor.py** (~400 lines)
**Purpose**: Low-level PDF extraction (text, tables, images)

**Functions from app.py**:
- `assemble_elements()`
- `lines_from_chars()`
- `extract_tables_with_bbox()`
- `extract_images_with_bbox_pymupdf()`
- `build_simplified_view_from_elements()`

**Responsibilities**:
- Character-level extraction
- Line grouping with font metadata
- Table detection
- Image extraction with coordinates
- Simplified view generation

---

### 10. **core/text_processor.py** (~100 lines)
**Purpose**: Text processing and manipulation

**Functions**:
- Word tolerance calculation
- Line breaking detection
- Font style detection
- Text formatting

---

### 11. **core/image_processor.py** (~100 lines)
**Purpose**: Image extraction and analysis

**Functions**:
- Image extraction from PDF
- Base64 encoding
- Image metadata handling
- Context matching

---

### 12. **core/table_processor.py** (~80 lines)
**Purpose**: Table extraction and processing

**Functions from app.py**:
- `extract_table_text_content()`
- `line_intersects_bbox()`
- Table content extraction
- Table similarity calculations

---

### 13. **utils/text_utils.py** (~80 lines)
**Purpose**: Text utility functions

**Functions from app.py**:
- `_normalize()`
- Text comparison
- Word splitting
- Character filtering

---

### 14. **utils/coordinate_utils.py** (~120 lines)
**Purpose**: Bounding box and coordinate calculations

**Functions from app.py**:
- `_lines_are_on_same_page()`
- `_lines_are_vertically_close()`
- `_pdf_lines_for_match()`
- Bounding box calculations
- Coordinate transformations

---

### 15. **utils/file_utils.py** (~60 lines)
**Purpose**: File operations

**Functions**:
- Save JSON outputs
- Load JSON files
- Generate unique filenames
- File validation

---

### 16. **models/chunk.py** (~80 lines)
**Purpose**: Chunk data model

**Classes**:
```python
@dataclass
class ChunkMetadata:
    type: str
    section: str
    context: str
    tags: List[str]
    page: int
    anchored: bool
    box: Optional[Dict]
    # ... other fields

@dataclass
class Chunk:
    text: str
    metadata: ChunkMetadata
    chunk_id: str
    created_at: str
```

---

### 17. **models/document.py** (~60 lines)
**Purpose**: Document metadata model

**Classes**:
```python
@dataclass
class DocumentMetadata:
    source_file: str
    processed_date: str
    total_chunks: int
    processing_version: str
    # ... other fields
```

---

### 18. **models/schemas.py** (~40 lines)
**Purpose**: JSON schemas and constants

**Contents**:
- Chunk schema definitions
- Response schemas
- Validation schemas

---

### 19. **database/weaviate_client.py** (~80 lines)
**Purpose**: Weaviate connection management

**Functions**:
- Initialize Weaviate client
- Create collections
- Connection health checks
- Singleton pattern implementation

---

### 20. **database/operations.py** (~100 lines)
**Purpose**: Database CRUD operations

**Functions**:
- Insert operations
- Update operations
- Delete operations
- Query operations

---

## Migration Strategy

### Phase 1: Preparation (Day 1)
1. ✅ Create new directory structure
2. ✅ Create `__init__.py` files for all packages
3. ✅ Set up `config.py` with environment variables
4. ✅ Create basic models (`Chunk`, `Document`)

### Phase 2: Extract Utilities (Day 1-2)
1. ✅ Move text utilities → `utils/text_utils.py`
2. ✅ Move coordinate utilities → `utils/coordinate_utils.py`
3. ✅ Move file utilities → `utils/file_utils.py`
4. ✅ Test utilities independently

### Phase 3: Extract Core Modules (Day 2-3)
1. ✅ Move PDF extraction → `core/pdf_extractor.py`
2. ✅ Move text processing → `core/text_processor.py`
3. ✅ Move image processing → `core/image_processor.py`
4. ✅ Move table processing → `core/table_processor.py`
5. ✅ Update imports

### Phase 4: Extract Services (Day 3-4)
1. ✅ Move Weaviate operations → `services/weaviate_service.py`
2. ✅ Move OpenAI operations → `services/openai_service.py`
3. ✅ Move anchoring logic → `services/anchoring_service.py`
4. ✅ Move chunking logic → `services/chunking_service.py`
5. ✅ Move PDF service → `services/pdf_service.py`

### Phase 5: Create API Layer (Day 4-5)
1. ✅ Create route definitions → `api/routes.py`
2. ✅ Extract endpoint logic
3. ✅ Implement request validation
4. ✅ Test endpoints

### Phase 6: Finalize (Day 5)
1. ✅ Create new minimal `app.py`
2. ✅ Update imports across all files
3. ✅ Remove commented code blocks
4. ✅ Add type hints
5. ✅ Test entire application

### Phase 7: Documentation & Testing (Day 6)
1. ✅ Add docstrings to all functions
2. ✅ Create README for each module
3. ✅ Write basic unit tests
4. ✅ Integration testing

---

## Code Organization Principles

### 1. Separation of Concerns
- **API Layer**: Only handles HTTP requests/responses
- **Service Layer**: Contains business logic
- **Core Layer**: Low-level processing
- **Utils**: Reusable helper functions
- **Models**: Data structures only

### 2. Dependency Direction
```
API → Services → Core → Utils
                 ↓
              Models
```

### 3. Import Rules
- ✅ Higher layers can import lower layers
- ❌ Lower layers should NOT import higher layers
- ✅ Utils and Models can be imported anywhere
- ❌ Avoid circular dependencies

### 4. Function Size
- Target: 20-50 lines per function
- Complex functions: Break into smaller helpers
- Single Responsibility Principle

### 5. Error Handling
- Services raise domain-specific exceptions
- API layer catches and converts to HTTP responses
- Centralized error handling

---

## Benefits After Refactoring

### Maintainability ✨
- Easy to locate specific functionality
- Clear module boundaries
- Single Responsibility Principle

### Testability 🧪
- Each module can be tested independently
- Mock dependencies easily
- Better code coverage

### Scalability 📈
- Easy to add new features
- Can swap implementations (e.g., different vector DB)
- Horizontal organization

### Readability 📖
- Self-documenting structure
- Smaller, focused files
- Clear naming conventions

### Collaboration 👥
- Multiple developers can work simultaneously
- Reduced merge conflicts
- Clear ownership boundaries

---

## File Size Comparison

| Current | After Refactoring |
|---------|-------------------|
| app.py: 2446 lines | 20 files averaging 50-150 lines each |
| 1 monolithic file | Clear modular structure |
| Mixed concerns | Separated concerns |

---

## Breaking Changes & Compatibility

### Import Changes
**Before:**
```python
from app import parse_and_chunk_pdf
```

**After:**
```python
from services.pdf_service import parse_and_chunk_pdf
```

### Configuration Changes
**Before:**
```python
openai_api_key = os.environ.get("OPENAI_APIKEY")
```

**After:**
```python
from config import Config
api_key = Config.OPENAI_API_KEY
```

---

## Cleanup Tasks

### Remove Commented Code
- Lines 1600-2200: Commented OCR/CV functions
- Lines 660-730: Old `/parse-pdf` endpoint
- Estimated removal: ~600 lines

### Code to Archive
Before deletion, save commented code to:
- `archive/ocr_processing.py` (for future reference)
- `archive/cv_detection.py`

---

## Risk Mitigation

### Testing Strategy
1. Unit tests for utilities first
2. Integration tests for services
3. End-to-end tests for API
4. Compare outputs before/after refactoring

### Rollback Plan
1. Keep original `app.py` as `app.py.backup`
2. Tag current Git commit
3. Incremental migration (branch per phase)
4. Feature flags for new modules

### Validation Checklist
- [ ] All 3 endpoints return same results
- [ ] PDF parsing produces identical output
- [ ] Weaviate uploads work correctly
- [ ] File outputs match original
- [ ] No performance degradation
- [ ] All imports resolve correctly

---

## Post-Refactoring Tasks

### Documentation
1. Update README.md with new structure
2. Add docstrings to all public functions
3. Create architecture diagram
4. API documentation (OpenAPI/Swagger)

### Code Quality
1. Add type hints (`from typing import ...`)
2. Run linter (pylint/flake8)
3. Format code (black)
4. Add logging throughout

### Testing
1. Unit tests (pytest)
2. Integration tests
3. Load testing
4. Edge case testing

---

## Timeline Estimate

| Phase | Duration | Deliverable |
|-------|----------|-------------|
| Phase 1: Preparation | 4 hours | Directory structure + config |
| Phase 2: Utilities | 6 hours | 3 utility modules + tests |
| Phase 3: Core Modules | 8 hours | 4 core modules + tests |
| Phase 4: Services | 10 hours | 5 service modules + tests |
| Phase 5: API Layer | 6 hours | Route definitions + validation |
| Phase 6: Finalize | 4 hours | New app.py + integration |
| Phase 7: Documentation | 4 hours | Docs + testing |
| **Total** | **42 hours** | **Complete refactor** |

---

## Success Metrics

- ✅ Average file size < 200 lines
- ✅ No circular dependencies
- ✅ 100% import resolution
- ✅ All existing tests pass
- ✅ Code coverage > 60%
- ✅ Linter score > 8.0/10
- ✅ API response times unchanged (±5%)

---

## Notes & Recommendations

### Priority Files to Refactor First
1. **Utilities** (text, coordinates) - Used everywhere
2. **PDF Extractor** - Core functionality
3. **Services** - Business logic
4. **API Routes** - User-facing

### Optional Enhancements
- Add caching (Redis) for processed PDFs
- Implement async processing (Celery)
- Add rate limiting
- Implement proper logging (structlog)
- Add monitoring (Prometheus)

### Dependencies to Add
```txt
# requirements.txt additions
python-dotenv==1.0.0
pytest==7.4.0
black==23.3.0
pylint==2.17.0
mypy==1.3.0
```

---

## Conclusion

This refactoring plan transforms a 2446-line monolithic file into a clean, maintainable, professional backend architecture with:
- 20+ focused modules
- Clear separation of concerns  
- Easy testability
- Scalable structure
- Industry best practices

**Estimated Effort**: 42 hours (1 week)  
**Risk Level**: Medium (with proper testing)  
**Business Value**: High (long-term maintainability)

---

## Approval & Next Steps

**Review Status**: ⏳ Awaiting Review  
**Approved By**: _____________  
**Start Date**: _____________  
**Target Completion**: _____________  

**Next Step**: Review this plan and provide feedback before execution begins.
