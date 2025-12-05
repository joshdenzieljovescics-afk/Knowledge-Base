# Sheets Agent - System Architecture Documentation

## 1. Overview

The **Sheets Agent** is a pure CRUD microservice for Google Sheets operations. It provides comprehensive tools for creating, reading, updating, and managing Google Spreadsheets with advanced features like multi-sheet uploads, date-based updates, and ABC analysis formatting.

| Property | Value |
|----------|-------|
| **Service Name** | Google Sheets Agent |
| **Default Port** | 8003 |
| **Version** | 2.0.0 |
| **Technology** | FastAPI (Python) |
| **Primary Function** | Google Sheets CRUD Operations |

---

## 2. System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                          SHEETS AGENT (Port 8003)                                │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  ┌────────────────────────┐                                                      │
│  │     API Endpoints      │                                                      │
│  │ • POST /execute_task   │                                                      │
│  │ • GET /tools           │                                                      │
│  │ • GET /health          │                                                      │
│  └───────────┬────────────┘                                                      │
│              │                                                                   │
│              ▼                                                                   │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │                       TOOL REGISTRY (15 Tools)                           │    │
│  ├─────────────────────────────────────────────────────────────────────────┤    │
│  │                                                                          │    │
│  │  ┌─────────────────────────────────────────────────────────────────┐    │    │
│  │  │                    CORE CRUD OPERATIONS                          │    │    │
│  │  │                                                                  │    │    │
│  │  │  create_sheet    read_sheet    update_sheet    append_rows      │    │    │
│  │  │  clear_sheet     get_sheet_metadata                              │    │    │
│  │  └─────────────────────────────────────────────────────────────────┘    │    │
│  │                                                                          │    │
│  │  ┌─────────────────────────────────────────────────────────────────┐    │    │
│  │  │                    DATA UPLOAD OPERATIONS                        │    │    │
│  │  │                                                                  │    │    │
│  │  │  upload_mapped_data     upload_multi_sheet_data                  │    │    │
│  │  │  update_by_date_match   apply_sheet_formatting                   │    │    │
│  │  └─────────────────────────────────────────────────────────────────┘    │    │
│  │                                                                          │    │
│  │  ┌─────────────────────────────────────────────────────────────────┐    │    │
│  │  │                    DATA VALIDATION OPERATIONS                    │    │    │
│  │  │                                                                  │    │    │
│  │  │  check_sheet_has_data      check_dates_have_data                 │    │    │
│  │  │  check_dates_and_columns_have_data    find_rows_by_dates         │    │    │
│  │  │  check_specific_cells_have_data                                  │    │    │
│  │  └─────────────────────────────────────────────────────────────────┘    │    │
│  │                                                                          │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
│                                      │                                           │
│                                      ▼                                           │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │                      GOOGLE SHEETS API LAYER                             │    │
│  │                                                                          │    │
│  │   ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐     │    │
│  │   │ OAuth2          │    │ Sheets API v4   │    │ Drive API v3    │     │    │
│  │   │ Credentials     │    │                 │    │                 │     │    │
│  │   │                 │    │ • spreadsheets  │    │ • files.create  │     │    │
│  │   │ Build from      │    │ • values        │    │ • permissions   │     │    │
│  │   │ credentials_dict│    │ • batchUpdate   │    │                 │     │    │
│  │   └─────────────────┘    └─────────────────┘    └─────────────────┘     │    │
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
                                      │
                                      ▼
              ┌───────────────────────────────────────────────────┐
              │                GOOGLE CLOUD                        │
              ├───────────────────────────────────────────────────┤
              │                                                    │
              │  ┌─────────────────────────────────────────────┐  │
              │  │            Google Sheets API                 │  │
              │  │                                              │  │
              │  │  https://sheets.googleapis.com/v4           │  │
              │  └─────────────────────────────────────────────┘  │
              │                                                    │
              │  ┌─────────────────────────────────────────────┐  │
              │  │            Google Drive API                  │  │
              │  │                                              │  │
              │  │  https://www.googleapis.com/drive/v3        │  │
              │  └─────────────────────────────────────────────┘  │
              │                                                    │
              └───────────────────────────────────────────────────┘
```

---

## 3. Tool Registry - Complete Reference

### 3.1 Core CRUD Tools

| Tool | Description | Key Inputs | Returns |
|------|-------------|------------|---------|
| `create_sheet` | Create new Google Spreadsheet | `spreadsheet_name` | `spreadsheet_id`, `spreadsheet_url` |
| `read_sheet` | Read data from a sheet range | `spreadsheet_id`, `range` | `values[][]` |
| `update_sheet` | Update specific range | `spreadsheet_id`, `range`, `values` | `updated_cells` |
| `append_rows` | Append rows to end of sheet | `spreadsheet_id`, `sheet_name`, `values` | `appended_rows` |
| `clear_sheet` | Clear data from a range | `spreadsheet_id`, `range` | `cleared_range` |
| `get_sheet_metadata` | Get spreadsheet info | `spreadsheet_id` | `sheets[]`, `row_counts` |

### 3.2 Data Upload Tools

| Tool | Description | Key Inputs | Returns |
|------|-------------|------------|---------|
| `upload_mapped_data` | Upload pre-transformed data | `spreadsheet_id`, `sheet_name`, `data` | `rows_uploaded` |
| `upload_multi_sheet_data` | Upload to multiple sheets | `spreadsheet_id`, `sheets_data{}` | `sheets_created[]` |
| `update_by_date_match` | Update rows by matching dates | `spreadsheet_id`, `date_column`, `updates[]` | `rows_updated` |
| `apply_sheet_formatting` | Apply ABC formatting | `spreadsheet_id`, `formatting_rules` | `formats_applied` |

### 3.3 Data Validation Tools

| Tool | Description | Key Inputs | Returns |
|------|-------------|------------|---------|
| `check_sheet_has_data` | Check if sheet has existing data | `spreadsheet_id`, `sheet_name` | `has_data`, `row_count` |
| `check_dates_have_data` | Check if dates already exist | `spreadsheet_id`, `dates[]` | `existing_dates[]` |
| `check_dates_and_columns_have_data` | Check date+column conflicts | `spreadsheet_id`, `dates[]`, `columns[]` | `conflicts[]` |
| `find_rows_by_dates` | Find row numbers for dates | `spreadsheet_id`, `dates[]` | `date_row_mapping{}` |
| `check_specific_cells_have_data` | Check specific cell values | `spreadsheet_id`, `cells[]` | `cells_with_data[]` |

---

## 4. OAuth2 Authentication Flow

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                        OAUTH2 CREDENTIALS FLOW                                   │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  ┌────────────────────┐     ┌────────────────────┐     ┌────────────────────┐   │
│  │    Client App      │     │    Sheets Agent    │     │   Google OAuth     │   │
│  │   (Frontend)       │     │     (Port 8003)    │     │     Server         │   │
│  └─────────┬──────────┘     └─────────┬──────────┘     └─────────┬──────────┘   │
│            │                          │                          │              │
│            │  User initiates Google   │                          │              │
│            │  Sign-In                 │                          │              │
│            │─────────────────────────────────────────────────────▶│              │
│            │                          │                          │              │
│            │   Auth code / tokens     │                          │              │
│            │◀─────────────────────────────────────────────────────│              │
│            │                          │                          │              │
│            │  POST /execute_task      │                          │              │
│            │  + credentials_dict      │                          │              │
│            │─────────────────────────▶│                          │              │
│            │                          │                          │              │
│            │                          │  Build OAuth2 credentials│              │
│            │                          │  from credentials_dict   │              │
│            │                          │                          │              │
│            │                          │  ┌────────────────────┐  │              │
│            │                          │  │ Credentials(        │  │              │
│            │                          │  │   token=token,      │  │              │
│            │                          │  │   refresh_token=...,│  │              │
│            │                          │  │   token_uri=...,    │  │              │
│            │                          │  │   client_id=...,    │  │              │
│            │                          │  │   client_secret=... │  │              │
│            │                          │  │ )                   │  │              │
│            │                          │  └────────────────────┘  │              │
│            │                          │                          │              │
│            │                          │  API call with creds     │              │
│            │                          │─────────────────────────▶│              │
│            │                          │                          │              │
│            │                          │     API response         │              │
│            │                          │◀─────────────────────────│              │
│            │                          │                          │              │
│            │   Tool response          │                          │              │
│            │◀─────────────────────────│                          │              │
│            │                          │                          │              │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### 4.1 CredentialsDict Structure

```python
class CredentialsDict(BaseModel):
    """OAuth2 credentials passed from frontend"""
    token: str                    # Access token
    refresh_token: str            # Refresh token for renewal
    token_uri: str                # Token endpoint URL
    client_id: str                # OAuth client ID
    client_secret: str            # OAuth client secret
    scopes: List[str]             # Granted OAuth scopes
    expiry: Optional[str] = None  # Token expiry timestamp
```

### 4.2 Required OAuth Scopes

```python
REQUIRED_SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",     # Full Sheets access
    "https://www.googleapis.com/auth/drive.file"        # Create/access files
]
```

---

## 5. API Endpoints

### 5.1 POST /execute_task

**Purpose**: Execute any Sheets tool

**Request**:
```python
class ToolRequest(BaseModel):
    tool: str                              # Tool name from registry
    inputs: Dict[str, Any]                 # Tool-specific inputs
    credentials_dict: CredentialsDict      # OAuth credentials
```

**Response**:
```python
class ToolResponse(BaseModel):
    success: bool
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
```

### 5.2 GET /tools

```python
{
    "tools": [
        {"name": "create_sheet", "description": "Create a new Google Spreadsheet"},
        {"name": "read_sheet", "description": "Read data from a Google Sheet"},
        # ... 13 more tools
    ],
    "count": 15
}
```

### 5.3 GET /health

```python
{
    "status": "healthy",
    "service": "google-sheets-agent",
    "version": "2.0.0",
    "description": "Pure CRUD operations for Google Sheets"
}
```

---

## 6. Data Flow Sequence Diagram (SSD)

```
┌──────────┐     ┌─────────────┐     ┌────────────────┐     ┌──────────────┐
│  Client  │     │Sheets Agent │     │  Google API    │     │  Monitoring  │
│(or Agent)│     │   (8003)    │     │   (Cloud)      │     │    (8009)    │
└────┬─────┘     └──────┬──────┘     └───────┬────────┘     └──────┬───────┘
     │                  │                    │                     │
     │ POST /execute_task                    │                     │
     │ tool: "create_sheet"                  │                     │
     │ + credentials_dict                    │                     │
     │─────────────────▶│                    │                     │
     │                  │                    │                     │
     │                  │ @monitor_task()    │                     │
     │                  │ task_started       │                     │
     │                  │──────────────────────────────────────────▶│
     │                  │                    │                     │
     │                  │ Build OAuth2       │                     │
     │                  │ credentials        │                     │
     │                  │                    │                     │
     │                  │ spreadsheets.      │                     │
     │                  │ create()           │                     │
     │                  │───────────────────▶│                     │
     │                  │                    │                     │
     │                  │ {spreadsheet_id,   │                     │
     │                  │  spreadsheet_url}  │                     │
     │                  │◀───────────────────│                     │
     │                  │                    │                     │
     │                  │ task_completed     │                     │
     │                  │──────────────────────────────────────────▶│
     │                  │                    │                     │
     │  {success: true, │                    │                     │
     │   result: {...}} │                    │                     │
     │◀─────────────────│                    │                     │
     │                  │                    │                     │
     │ POST /execute_task                    │                     │
     │ tool: "upload_multi_sheet_data"       │                     │
     │─────────────────▶│                    │                     │
     │                  │                    │                     │
     │                  │ FOR each sheet:    │                     │
     │                  │                    │                     │
     │                  │ batchUpdate()      │                     │
     │                  │ (add sheet)        │                     │
     │                  │───────────────────▶│                     │
     │                  │                    │                     │
     │                  │ values.update()    │                     │
     │                  │ (write data)       │                     │
     │                  │───────────────────▶│                     │
     │                  │                    │                     │
     │  {sheets_created}│                    │                     │
     │◀─────────────────│                    │                     │
     │                  │                    │                     │
     │ POST /execute_task                    │                     │
     │ tool: "apply_sheet_formatting"        │                     │
     │─────────────────▶│                    │                     │
     │                  │                    │                     │
     │                  │ batchUpdate()      │                     │
     │                  │ (formatting)       │                     │
     │                  │───────────────────▶│                     │
     │                  │                    │                     │
     │  {formats_applied}                    │                     │
     │◀─────────────────│                    │                     │
     │                  │                    │                     │
```

---

## 7. Activity Diagram - Multi-Sheet Upload

```
                            ┌─────────────────┐
                            │     START       │
                            └────────┬────────┘
                                     │
                                     ▼
                       ┌─────────────────────────────┐
                       │  Receive upload request     │
                       │  {spreadsheet_id,           │
                       │   sheets_data,              │
                       │   credentials_dict}         │
                       └─────────────┬───────────────┘
                                     │
                                     ▼
                       ┌─────────────────────────────┐
                       │  Build OAuth2 credentials   │
                       │  from credentials_dict      │
                       └─────────────┬───────────────┘
                                     │
                                     ▼
                       ┌─────────────────────────────┐
                       │  Connect to Sheets API      │
                       └─────────────┬───────────────┘
                                     │
                              ┌──────┴──────┐
                              ▼             ▼
                        ┌──────────┐  ┌──────────────┐
                        │ Success  │  │   Failed     │
                        └────┬─────┘  └──────┬───────┘
                             │               │
                             │               ▼
                             │        ┌──────────────┐
                             │        │ Return Error │
                             │        │ "Auth failed"│
                             │        └──────────────┘
                             │
                             ▼
                ┌────────────────────────────────┐
                │  Get existing sheet names      │
                │  from spreadsheet              │
                └────────────────┬───────────────┘
                                 │
                                 ▼
            ┌────────────────────────────────────────┐
            │  LOOP: For each sheet in sheets_data  │◀──────┐
            └────────────────┬───────────────────────┘       │
                             │                               │
                             ▼                               │
            ┌────────────────────────────────────┐           │
            │  Does sheet already exist?         │           │
            └────────────────┬───────────────────┘           │
                             │                               │
                      ┌──────┴──────┐                        │
                      ▼             ▼                        │
                ┌──────────┐  ┌──────────────┐              │
                │   Yes    │  │     No       │              │
                │  (skip   │  │              │              │
                │  create) │  └──────┬───────┘              │
                └────┬─────┘         │                       │
                     │               ▼                       │
                     │    ┌────────────────────────────┐    │
                     │    │  batchUpdate: addSheet     │    │
                     │    │  (create new sheet)        │    │
                     │    └────────────────┬───────────┘    │
                     │                     │                 │
                     └─────────┬───────────┘                 │
                               │                             │
                               ▼                             │
            ┌────────────────────────────────────┐           │
            │  Prepare data for sheet:           │           │
            │  • Convert to 2D array             │           │
            │  • Handle null/None values         │           │
            │  • Format dates/numbers            │           │
            └────────────────┬───────────────────┘           │
                             │                               │
                             ▼                               │
            ┌────────────────────────────────────┐           │
            │  values.update():                  │           │
            │  Write data to sheet range         │           │
            └────────────────┬───────────────────┘           │
                             │                               │
                             ▼                               │
            ┌────────────────────────────────────┐           │
            │  More sheets?                      │───Yes─────┘
            └────────────────┬───────────────────┘
                             │ No
                             ▼
            ┌────────────────────────────────────┐
            │  Compile results:                  │
            │  • sheets_created[]                │
            │  • rows_per_sheet{}                │
            │  • total_cells_updated             │
            └────────────────┬───────────────────┘
                             │
                             ▼
            ┌────────────────────────────────────┐
            │  Return success response           │
            └────────────────┬───────────────────┘
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
    """Request to execute a Sheets tool"""
    tool: str                              # Tool name from registry
    inputs: Dict[str, Any]                 # Tool-specific inputs
    credentials_dict: CredentialsDict      # OAuth credentials
```

### 8.2 ToolResponse

```python
class ToolResponse(BaseModel):
    """Response from tool execution"""
    success: bool
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
```

### 8.3 SheetData

```python
# For upload_multi_sheet_data
sheets_data = {
    "Sheet1 Name": [
        ["Header1", "Header2", "Header3"],  # Row 1 (headers)
        ["Value1", "Value2", "Value3"],      # Row 2
        ["Value4", "Value5", "Value6"],      # Row 3
    ],
    "Sheet2 Name": [
        ["Col A", "Col B"],
        ["Data1", "Data2"],
    ]
}
```

### 8.4 FormattingRules

```python
# For apply_sheet_formatting (ABC Analysis)
formatting_rules = {
    "header_row": {
        "background_color": "#4285F4",
        "font_color": "#FFFFFF",
        "bold": True
    },
    "category_a": {
        "background_color": "#90EE90"  # Light green
    },
    "category_b": {
        "background_color": "#FFFFE0"  # Light yellow
    },
    "category_c": {
        "background_color": "#FFB6C1"  # Light red/pink
    }
}
```

---

## 9. Tool Usage Examples

### 9.1 Create and Populate Spreadsheet

```python
import requests

SHEETS_AGENT = "http://localhost:8003"
credentials = {...}  # OAuth credentials dict

# Step 1: Create spreadsheet
response = requests.post(
    f"{SHEETS_AGENT}/execute_task",
    json={
        "tool": "create_sheet",
        "inputs": {
            "spreadsheet_name": "Sales Report Q1 2024"
        },
        "credentials_dict": credentials
    }
)
spreadsheet_id = response.json()["result"]["spreadsheet_id"]

# Step 2: Upload multi-sheet data
response = requests.post(
    f"{SHEETS_AGENT}/execute_task",
    json={
        "tool": "upload_multi_sheet_data",
        "inputs": {
            "spreadsheet_id": spreadsheet_id,
            "sheets_data": {
                "January": [
                    ["Product", "Quantity", "Revenue"],
                    ["Product A", 100, 5000],
                    ["Product B", 200, 8000],
                ],
                "February": [
                    ["Product", "Quantity", "Revenue"],
                    ["Product A", 150, 7500],
                    ["Product B", 180, 7200],
                ]
            }
        },
        "credentials_dict": credentials
    }
)
```

### 9.2 Check for Existing Data Before Update

```python
# Check if dates already have data
response = requests.post(
    f"{SHEETS_AGENT}/execute_task",
    json={
        "tool": "check_dates_have_data",
        "inputs": {
            "spreadsheet_id": spreadsheet_id,
            "sheet_name": "Daily Sales",
            "date_column": "A",
            "dates": ["2024-01-15", "2024-01-16", "2024-01-17"]
        },
        "credentials_dict": credentials
    }
)

result = response.json()["result"]
if result["existing_dates"]:
    print(f"Warning: These dates already have data: {result['existing_dates']}")
```

### 9.3 Update by Date Match

```python
# Update existing rows by matching dates
response = requests.post(
    f"{SHEETS_AGENT}/execute_task",
    json={
        "tool": "update_by_date_match",
        "inputs": {
            "spreadsheet_id": spreadsheet_id,
            "sheet_name": "Daily Sales",
            "date_column": "A",
            "updates": [
                {
                    "date": "2024-01-15",
                    "values": {
                        "B": 250,   # Quantity column
                        "C": 12500  # Revenue column
                    }
                },
                {
                    "date": "2024-01-16",
                    "values": {
                        "B": 180,
                        "C": 9000
                    }
                }
            ]
        },
        "credentials_dict": credentials
    }
)
```

---

## 10. ABC Analysis Formatting

The `apply_sheet_formatting` tool is specifically designed for ABC Analysis output:

```python
response = requests.post(
    f"{SHEETS_AGENT}/execute_task",
    json={
        "tool": "apply_sheet_formatting",
        "inputs": {
            "spreadsheet_id": spreadsheet_id,
            "sheets": ["January 2024", "February 2024"],
            "category_column": "F",  # Column containing A/B/C values
            "formatting": {
                "freeze_header": True,
                "header_style": {
                    "background": "#1a73e8",
                    "font_color": "#ffffff",
                    "bold": True
                },
                "category_colors": {
                    "A": "#b7e1cd",  # Green
                    "B": "#fce8b2",  # Yellow
                    "C": "#f4c7c3"   # Red
                },
                "auto_resize_columns": True
            }
        },
        "credentials_dict": credentials
    }
)
```

---

## 11. Error Handling

| Error Type | HTTP Status | Description | Resolution |
|------------|-------------|-------------|------------|
| Unknown tool | 400 | Tool not in registry | Check `/tools` endpoint |
| Invalid credentials | 401 | OAuth token invalid/expired | Refresh OAuth token |
| Spreadsheet not found | 404 | spreadsheet_id doesn't exist | Verify ID |
| Permission denied | 403 | User lacks sheet access | Share sheet with user |
| Rate limit | 429 | Too many API requests | Implement backoff |
| API error | 502 | Google API failure | Retry with backoff |

---

## 12. Configuration

```python
# Environment Variables
SHEETS_AGENT_PORT = 8003
MONITORING_URL = "http://localhost:8009"

# Google API Quotas (default)
READ_REQUESTS_PER_MINUTE = 100
WRITE_REQUESTS_PER_MINUTE = 100
CELLS_PER_UPDATE = 10000000  # 10 million cells per update
```

---

## 13. Integration with Other Agents

### 13.1 ABC Analysis Agent Integration

```
ABC Analysis Agent (8007)  ──HTTP──▶  Sheets Agent (8003)
         │                                    │
         │  1. create_sheet                   │
         │  2. upload_multi_sheet_data        │
         │  3. apply_sheet_formatting         │
         │                                    │
         ▼                                    ▼
    Analysis Results  ──────────────▶  Google Spreadsheet
```

### 13.2 Mapping Agent Integration

```
Mapping Agent (8004)  ──────▶  transforms data  ──────▶  Sheets Agent (8003)
         │                                                     │
         │  parse_file()                                       │
         │  smart_column_mapping()                             │
         │  transform_data()                                   │
         ▼                                                     ▼
    Source File  ────────────────────────────────────▶  Google Spreadsheet
```

---

## 14. Performance Considerations

| Operation | Typical Latency | Max Batch Size |
|-----------|-----------------|----------------|
| create_sheet | 500-1000ms | N/A |
| read_sheet | 200-500ms | 10,000 rows |
| update_sheet | 300-700ms | 100,000 cells |
| append_rows | 300-500ms | 10,000 rows |
| upload_multi_sheet | 1-5s | Depends on data |
| apply_formatting | 500-2000ms | Per sheet |

**Best Practices**:
- Batch writes when possible (use `upload_multi_sheet_data`)
- Use `check_*` tools before writing to avoid conflicts
- Implement exponential backoff for rate limits
