# Mapping Agent - System Architecture Documentation

## 1. Overview

The **Mapping Agent** is a data intelligence and transformation microservice that provides AI-powered column mapping, file parsing, and data transformation capabilities. It uses a 3-tier approach (exact match → rule-based → OpenAI LLM) for smart column mapping.

| Property | Value |
|----------|-------|
| **Service Name** | Mapping Agent |
| **Default Port** | 8004 |
| **Version** | 1.0.0 |
| **Technology** | FastAPI (Python) |
| **Primary Function** | Data Parsing, Column Mapping, Transformation |

---

## 2. System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           MAPPING AGENT (Port 8004)                              │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  ┌──────────────────────┐                                                        │
│  │    API Endpoints     │                                                        │
│  │ • POST /execute_task │                                                        │
│  │ • GET /tools         │                                                        │
│  │ • GET /health        │                                                        │
│  └──────────┬───────────┘                                                        │
│             │                                                                    │
│             ▼                                                                    │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │                          TOOL REGISTRY (9 Tools)                         │    │
│  ├─────────────────────────────────────────────────────────────────────────┤    │
│  │                                                                          │    │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────────┐  │    │
│  │  │   parse_file    │  │ smart_column_   │  │    transform_data       │  │    │
│  │  │                 │  │    mapping      │  │                         │  │    │
│  │  │ CSV/Excel/JSON  │  │                 │  │ Apply column mappings   │  │    │
│  │  │ → DataFrame     │  │ 3-Tier AI       │  │ & transformations       │  │    │
│  │  └─────────────────┘  └─────────────────┘  └─────────────────────────┘  │    │
│  │                                                                          │    │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────────┐  │    │
│  │  │validate_mapping │  │ get_file_info   │  │   transform_values      │  │    │
│  │  │                 │  │                 │  │                         │  │    │
│  │  │ Check mapping   │  │ File metadata   │  │ Date format, numeric    │  │    │
│  │  │ completeness    │  │ & statistics    │  │ & string transforms     │  │    │
│  │  └─────────────────┘  └─────────────────┘  └─────────────────────────┘  │    │
│  │                                                                          │    │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────────┐  │    │
│  │  │ get_sample_data │  │ detect_column_  │  │   parse_file_base64     │  │    │
│  │  │                 │  │    types        │  │                         │  │    │
│  │  │ First N rows    │  │                 │  │ Base64 encoded file     │  │    │
│  │  │ preview         │  │ int/float/date  │  │ parsing                 │  │    │
│  │  └─────────────────┘  └─────────────────┘  └─────────────────────────┘  │    │
│  │                                                                          │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
│                                      │                                           │
│                                      ▼                                           │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │                      SMART MAPPING ENGINE                                │    │
│  │                                                                          │    │
│  │   ┌──────────────┐    ┌──────────────┐    ┌────────────────────────┐    │    │
│  │   │   TIER 1     │───▶│   TIER 2     │───▶│       TIER 3           │    │    │
│  │   │ Exact Match  │    │ Rule-Based   │    │  OpenAI LLM Fallback   │    │    │
│  │   │              │    │              │    │                        │    │    │
│  │   │ String match │    │ Synonyms &   │    │ GPT-4 semantic         │    │    │
│  │   │ (normalized) │    │ abbreviations│    │ understanding          │    │    │
│  │   └──────────────┘    └──────────────┘    └────────────────────────┘    │    │
│  │                                                                          │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
│                                                                                  │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │                      MONITORING DECORATOR                                │    │
│  │                      @monitor_task()                                     │    │
│  │                 Reports to MONITORING_URL (Port 8009)                    │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Smart Mapping Engine - 3-Tier Architecture

The Smart Mapping Engine uses a cascading approach to map source columns to target columns:

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                        SMART MAPPING ENGINE FLOW                                 │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  Source Column: "Prod_ID"          Target Column: "Product Identifier"           │
│                                                                                  │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │  TIER 1: EXACT MATCHING (Fastest - ~0ms)                                │    │
│  │                                                                          │    │
│  │  1. Normalize both strings (lowercase, remove special chars)            │    │
│  │     "Prod_ID" → "prodid"                                                │    │
│  │     "Product Identifier" → "productidentifier"                          │    │
│  │                                                                          │    │
│  │  2. Compare normalized strings                                           │    │
│  │     "prodid" ≠ "productidentifier"  →  NO MATCH                         │    │
│  │                                                                          │    │
│  │  ❌ No match → Continue to Tier 2                                        │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
│                                      │                                           │
│                                      ▼                                           │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │  TIER 2: RULE-BASED SEMANTIC MATCHING (~1ms)                            │    │
│  │                                                                          │    │
│  │  Uses vocabulary of synonyms and abbreviations:                          │    │
│  │                                                                          │    │
│  │  SYNONYMS = {                                                            │    │
│  │    "product": ["item", "prod", "sku", "article"],                       │    │
│  │    "identifier": ["id", "code", "number", "num"],                       │    │
│  │    "quantity": ["qty", "amount", "count", "units"],                     │    │
│  │    "date": ["dt", "datetime", "timestamp"],                             │    │
│  │    ...                                                                   │    │
│  │  }                                                                       │    │
│  │                                                                          │    │
│  │  Expansion: "Prod_ID" → ["product_id", "prod_identifier", ...]          │    │
│  │  Check if any expansion matches target                                   │    │
│  │                                                                          │    │
│  │  ✅ Match Found! Confidence: 85%                                         │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
│                                      │                                           │
│                                      ▼ (If no match)                             │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │  TIER 3: OPENAI LLM FALLBACK (~500ms)                                   │    │
│  │                                                                          │    │
│  │  Prompt to GPT-4:                                                        │    │
│  │  "Given source column 'Prod_ID' with sample values ['P001', 'P002'],    │    │
│  │   determine if it matches target column 'Product Identifier'.           │    │
│  │   Return confidence score (0-100) and reasoning."                       │    │
│  │                                                                          │    │
│  │  Response: {"confidence": 95, "match": true, "reasoning": "..."}        │    │
│  │                                                                          │    │
│  │  ✅ Match Found! Confidence: 95%                                         │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Tool Registry

### 4.1 Complete Tool List

| Tool Name | Description | Input | Output |
|-----------|-------------|-------|--------|
| `parse_file` | Parse CSV/Excel/JSON to structured data | `file_path` or `file_content` | `{columns, rows, data}` |
| `parse_file_base64` | Parse base64-encoded file | `file_base64`, `filename` | `{columns, rows, data}` |
| `smart_column_mapping` | AI-powered column mapping | `source_columns`, `target_columns` | `{mappings, confidence}` |
| `transform_data` | Apply mappings to transform data | `data`, `mappings` | `{transformed_data}` |
| `transform_values` | Transform individual values | `values`, `transform_type` | `{transformed_values}` |
| `validate_mapping` | Validate mapping completeness | `mappings`, `required_columns` | `{valid, missing, errors}` |
| `get_file_info` | Get file metadata and stats | `file_path` | `{size, columns, rows, types}` |
| `get_sample_data` | Get first N rows for preview | `file_path`, `n_rows` | `{sample_data}` |
| `detect_column_types` | Detect data types of columns | `data` | `{column_types}` |

---

## 5. API Endpoints

### 5.1 POST /execute_task

**Purpose**: Execute any mapping tool

**Request**:
```python
class ToolRequest(BaseModel):
    tool: str                              # Tool name from registry
    inputs: Dict[str, Any]                 # Tool-specific inputs
```

**Response**:
```python
class ToolResponse(BaseModel):
    success: bool
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
```

**Example - Smart Column Mapping**:
```python
# Request
{
    "tool": "smart_column_mapping",
    "inputs": {
        "source_columns": ["Prod_ID", "Qty", "Order_Dt"],
        "target_columns": ["Product Identifier", "Quantity", "Order Date"],
        "sample_values": {
            "Prod_ID": ["P001", "P002", "P003"],
            "Qty": [100, 200, 150],
            "Order_Dt": ["2024-01-15", "2024-01-16"]
        }
    }
}

# Response
{
    "success": true,
    "result": {
        "mappings": [
            {
                "source": "Prod_ID",
                "target": "Product Identifier",
                "confidence": 0.95,
                "method": "rule_based"
            },
            {
                "source": "Qty",
                "target": "Quantity",
                "confidence": 0.98,
                "method": "exact_match"
            },
            {
                "source": "Order_Dt",
                "target": "Order Date",
                "confidence": 0.92,
                "method": "rule_based"
            }
        ],
        "unmapped_source": [],
        "unmapped_target": []
    }
}
```

### 5.2 GET /tools

```python
{
    "tools": [
        {"name": "parse_file", "description": "Parse CSV/Excel/JSON files"},
        {"name": "smart_column_mapping", "description": "AI-powered column mapping"},
        # ... more tools
    ],
    "count": 9
}
```

### 5.3 GET /health

```python
{
    "status": "healthy",
    "service": "mapping-agent",
    "version": "1.0.0"
}
```

---

## 6. Data Flow Sequence Diagram (SSD)

```
┌──────────┐     ┌─────────────┐     ┌────────────────┐     ┌──────────────┐
│  Client  │     │Mapping Agent│     │ SmartMapping   │     │   OpenAI     │
│(or Agent)│     │   (8004)    │     │    Engine      │     │    API       │
└────┬─────┘     └──────┬──────┘     └───────┬────────┘     └──────┬───────┘
     │                  │                    │                     │
     │ POST /execute_task                    │                     │
     │ tool: "parse_file"                    │                     │
     │─────────────────▶│                    │                     │
     │                  │                    │                     │
     │                  │ parse_file()       │                     │
     │                  │───────────────────▶│                     │
     │                  │                    │                     │
     │  {columns, data} │                    │                     │
     │◀─────────────────│                    │                     │
     │                  │                    │                     │
     │ POST /execute_task                    │                     │
     │ tool: "smart_column_mapping"          │                     │
     │─────────────────▶│                    │                     │
     │                  │                    │                     │
     │                  │ map_columns()      │                     │
     │                  │───────────────────▶│                     │
     │                  │                    │                     │
     │                  │    ┌───────────────┴─────────────────┐   │
     │                  │    │ TIER 1: Exact Match            │   │
     │                  │    │ Check normalized string match   │   │
     │                  │    └───────────────┬─────────────────┘   │
     │                  │                    │                     │
     │                  │    ┌───────────────┴─────────────────┐   │
     │                  │    │ TIER 2: Rule-Based              │   │
     │                  │    │ Apply synonyms & abbreviations  │   │
     │                  │    └───────────────┬─────────────────┘   │
     │                  │                    │                     │
     │                  │    ┌───────────────┴─────────────────┐   │
     │                  │    │ TIER 3: OpenAI LLM (if needed)  │   │
     │                  │    └───────────────┬─────────────────┘   │
     │                  │                    │                     │
     │                  │                    │ POST /chat/         │
     │                  │                    │ completions         │
     │                  │                    │────────────────────▶│
     │                  │                    │                     │
     │                  │                    │   LLM Response      │
     │                  │                    │◀────────────────────│
     │                  │                    │                     │
     │                  │    {mappings}      │                     │
     │                  │◀───────────────────│                     │
     │                  │                    │                     │
     │    {mappings,    │                    │                     │
     │     confidence}  │                    │                     │
     │◀─────────────────│                    │                     │
     │                  │                    │                     │
     │ POST /execute_task                    │                     │
     │ tool: "transform_data"                │                     │
     │─────────────────▶│                    │                     │
     │                  │                    │                     │
     │  {transformed_   │                    │                     │
     │      data}       │                    │                     │
     │◀─────────────────│                    │                     │
     │                  │                    │                     │
```

---

## 7. Activity Diagram

```
                            ┌─────────────────┐
                            │     START       │
                            └────────┬────────┘
                                     │
                                     ▼
                       ┌─────────────────────────────┐
                       │  Receive tool request       │
                       │  (tool name + inputs)       │
                       └─────────────┬───────────────┘
                                     │
                                     ▼
                       ┌─────────────────────────────┐
                       │  Lookup tool in registry    │
                       └─────────────┬───────────────┘
                                     │
                              ┌──────┴──────┐
                              ▼             ▼
                        ┌──────────┐  ┌──────────────┐
                        │  Found   │  │  Not Found   │
                        └────┬─────┘  └──────┬───────┘
                             │               │
                             │               ▼
                             │        ┌──────────────┐
                             │        │ Return Error │
                             │        │ "Unknown     │
                             │        │  tool"       │
                             │        └──────────────┘
                             │
                             ▼
               ┌─────────────────────────────────┐
               │  Which tool?                    │
               └──────────┬──────────────────────┘
                          │
     ┌────────────────────┼────────────────────┬──────────────────┐
     │                    │                    │                  │
     ▼                    ▼                    ▼                  ▼
┌─────────────┐  ┌─────────────────┐  ┌─────────────────┐  ┌────────────┐
│ parse_file  │  │smart_column_    │  │ transform_data  │  │  Other     │
│             │  │   mapping       │  │                 │  │  Tools     │
└──────┬──────┘  └────────┬────────┘  └────────┬────────┘  └─────┬──────┘
       │                  │                    │                  │
       ▼                  ▼                    ▼                  │
┌─────────────┐  ┌─────────────────┐  ┌─────────────────┐        │
│Read file    │  │ TIER 1: Exact   │  │Apply column     │        │
│(CSV/Excel/  │  │ string match    │  │mappings to data │        │
│JSON)        │  └────────┬────────┘  └────────┬────────┘        │
└──────┬──────┘           │                    │                  │
       │                  ▼                    ▼                  │
       ▼           ┌──────────────┐     ┌─────────────────┐       │
┌─────────────┐    │ Match found? │     │ Rename columns  │       │
│Parse to     │    └──────┬───────┘     └────────┬────────┘       │
│DataFrame    │           │                      │                │
└──────┬──────┘    ┌──────┴──────┐               ▼                │
       │           ▼             ▼        ┌─────────────────┐     │
       ▼      ┌────────┐  ┌──────────┐    │ Apply value     │     │
┌─────────────┐│  Yes   │  │   No     │    │ transformations │     │
│Extract      ││        │  │          │    └────────┬────────┘     │
│columns &    │└───┬────┘  └────┬─────┘             │              │
│sample data  │    │            │                    ▼              │
└──────┬──────┘    │            ▼             ┌─────────────────┐  │
       │           │   ┌─────────────────┐    │ Return          │  │
       ▼           │   │ TIER 2: Rule-   │    │ transformed_    │  │
┌─────────────┐    │   │ based synonyms  │    │ data            │  │
│Return       │    │   └────────┬────────┘    └────────┬────────┘  │
│{columns,    │    │            │                      │           │
│ rows, data} │    │     ┌──────┴──────┐               │           │
└──────┬──────┘    │     ▼             ▼               │           │
       │           │ ┌────────┐  ┌──────────┐          │           │
       │           │ │  Yes   │  │   No     │          │           │
       │           │ └───┬────┘  └────┬─────┘          │           │
       │           │     │            │                 │           │
       │           │     │            ▼                 │           │
       │           │     │   ┌─────────────────┐       │           │
       │           │     │   │ TIER 3: OpenAI  │       │           │
       │           │     │   │ LLM semantic    │       │           │
       │           │     │   └────────┬────────┘       │           │
       │           │     │            │                 │           │
       │           │     │            ▼                 │           │
       │           │     │   ┌─────────────────┐       │           │
       │           │     │   │ Return mapping  │       │           │
       │           │     │   │ with confidence │       │           │
       │           │     │   └────────┬────────┘       │           │
       │           │     │            │                 │           │
       │           ▼     ▼            │                 │           │
       │    ┌─────────────────────────┴─────────────────┘           │
       │    │                                                       │
       │    ▼                                                       │
       │    ┌─────────────────────────────────────────────────────┐│
       │    │              Aggregate results                       ││
       │    └─────────────────────────┬───────────────────────────┘│
       │                              │                             │
       └──────────────────────────────┼─────────────────────────────┘
                                      │
                                      ▼
                       ┌─────────────────────────────┐
                       │  Return ToolResponse        │
                       │  {success, result, error}   │
                       └─────────────┬───────────────┘
                                     │
                                     ▼
                               ┌───────────┐
                               │    END    │
                               └───────────┘
```

---

## 8. Data Models

### 8.1 ToolRequest

```python
class ToolRequest(BaseModel):
    """Request to execute a mapping tool"""
    tool: str                      # Name of tool from registry
    inputs: Dict[str, Any]         # Tool-specific inputs
```

### 8.2 ToolResponse

```python
class ToolResponse(BaseModel):
    """Response from tool execution"""
    success: bool
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
```

### 8.3 ColumnMapping

```python
class ColumnMapping(BaseModel):
    """Single column mapping result"""
    source: str                    # Source column name
    target: str                    # Target column name
    confidence: float              # 0.0 - 1.0
    method: str                    # "exact_match", "rule_based", "llm"
    transformation: Optional[str]  # Optional value transformation
```

### 8.4 MappingResult

```python
class MappingResult(BaseModel):
    """Complete mapping result"""
    mappings: List[ColumnMapping]
    unmapped_source: List[str]     # Source columns without matches
    unmapped_target: List[str]     # Target columns without matches
    overall_confidence: float
```

---

## 9. Smart Mapping Engine Configuration

### 9.1 Synonym Dictionary

```python
SYNONYMS = {
    # Product/Item identifiers
    "product": ["item", "prod", "sku", "article", "material", "part"],
    "identifier": ["id", "code", "number", "num", "no", "key"],
    
    # Quantity related
    "quantity": ["qty", "amount", "count", "units", "pieces", "pcs"],
    "ordered": ["order", "ord", "purchased", "bought"],
    
    # Date/Time related
    "date": ["dt", "datetime", "timestamp", "time", "day"],
    "created": ["creation", "created_at", "create_date"],
    "updated": ["modified", "updated_at", "modify_date"],
    
    # Customer related
    "customer": ["cust", "client", "buyer", "account"],
    "name": ["nm", "title", "label", "description"],
    
    # Financial
    "price": ["cost", "amount", "value", "rate", "charge"],
    "total": ["sum", "grand_total", "subtotal", "net"],
}
```

### 9.2 Abbreviation Expansions

```python
ABBREVIATIONS = {
    "id": "identifier",
    "qty": "quantity",
    "dt": "date",
    "nm": "name",
    "no": "number",
    "amt": "amount",
    "cust": "customer",
    "ord": "order",
    "inv": "inventory",
    "prod": "product",
    "desc": "description",
    "cat": "category",
}
```

### 9.3 LLM Prompt Template

```python
LLM_MAPPING_PROMPT = """
You are a data mapping expert. Given a source column and target columns, 
determine the best match.

Source Column: {source_column}
Sample Values: {sample_values}

Target Columns: {target_columns}

Return JSON:
{
    "best_match": "target_column_name or null",
    "confidence": 0.0-1.0,
    "reasoning": "brief explanation"
}
"""
```

---

## 10. Supported File Formats

| Format | Extensions | Parser | Notes |
|--------|------------|--------|-------|
| CSV | .csv | `pandas.read_csv()` | Auto-detect delimiter |
| Excel | .xlsx, .xls | `pandas.read_excel()` | Supports multiple sheets |
| JSON | .json | `pandas.read_json()` | Flat or nested structures |

---

## 11. Integration Examples

### 11.1 Full Mapping Pipeline

```python
import requests

MAPPING_AGENT = "http://localhost:8004"

# Step 1: Parse the source file
parse_response = requests.post(
    f"{MAPPING_AGENT}/execute_task",
    json={
        "tool": "parse_file_base64",
        "inputs": {
            "file_base64": base64_encoded_file,
            "filename": "sales_data.xlsx"
        }
    }
)
source_data = parse_response.json()["result"]

# Step 2: Get smart column mappings
mapping_response = requests.post(
    f"{MAPPING_AGENT}/execute_task",
    json={
        "tool": "smart_column_mapping",
        "inputs": {
            "source_columns": source_data["columns"],
            "target_columns": ["Product ID", "Quantity", "Order Date", "Customer Name"],
            "sample_values": source_data["sample_values"]
        }
    }
)
mappings = mapping_response.json()["result"]["mappings"]

# Step 3: Transform data using mappings
transform_response = requests.post(
    f"{MAPPING_AGENT}/execute_task",
    json={
        "tool": "transform_data",
        "inputs": {
            "data": source_data["data"],
            "mappings": mappings
        }
    }
)
transformed_data = transform_response.json()["result"]["transformed_data"]
```

### 11.2 Validate Mapping Completeness

```python
# Check if all required columns are mapped
validation_response = requests.post(
    f"{MAPPING_AGENT}/execute_task",
    json={
        "tool": "validate_mapping",
        "inputs": {
            "mappings": mappings,
            "required_columns": ["Product ID", "Quantity"]  # Must be mapped
        }
    }
)

result = validation_response.json()["result"]
if not result["valid"]:
    print(f"Missing required columns: {result['missing']}")
```

---

## 12. Error Handling

| Error Type | HTTP Status | Description |
|------------|-------------|-------------|
| Unknown tool | 400 | Tool name not in registry |
| Parse error | 400 | Unable to parse file format |
| Missing inputs | 400 | Required inputs not provided |
| LLM error | 502 | OpenAI API call failed |
| Transformation error | 500 | Error during data transformation |

---

## 13. Configuration

```python
# Environment Variables
MAPPING_AGENT_PORT = 8004
OPENAI_API_KEY = "sk-..."  # For Tier 3 LLM fallback
MONITORING_URL = "http://localhost:8009"

# Mapping Thresholds
EXACT_MATCH_THRESHOLD = 1.0       # Perfect match required
RULE_BASED_THRESHOLD = 0.7        # Minimum confidence for rule-based
LLM_CONFIDENCE_THRESHOLD = 0.6    # Minimum confidence from LLM
```

---

## 14. Performance Characteristics

| Tier | Latency | Use Case |
|------|---------|----------|
| Tier 1 (Exact) | ~0ms | Identical or normalized column names |
| Tier 2 (Rules) | ~1ms | Abbreviations and synonyms |
| Tier 3 (LLM) | ~500-1000ms | Complex semantic matching |

**Optimization**: LLM calls are only made for columns that can't be matched by Tier 1 or 2, minimizing API costs and latency.
