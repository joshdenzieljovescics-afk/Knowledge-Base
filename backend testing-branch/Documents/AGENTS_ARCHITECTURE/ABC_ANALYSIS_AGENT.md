# ABC Analysis Agent - System Architecture Documentation

## 1. Overview

The **ABC Analysis Agent** is a specialized microservice that performs Monthly ABC/Pareto inventory analysis. It categorizes items into A, B, and C classes based on their cumulative contribution to total value, enabling inventory optimization and prioritization strategies.

| Property | Value |
|----------|-------|
| **Service Name** | ABC Analysis Agent |
| **Default Port** | 8007 |
| **Version** | 1.0.0 |
| **Technology** | FastAPI (Python) |
| **Primary Function** | Monthly Pareto Inventory Analysis |

---

## 2. System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                            ABC ANALYSIS AGENT (Port 8007)                        │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  ┌──────────────────┐    ┌──────────────────────┐    ┌──────────────────────┐   │
│  │   API Endpoints  │───▶│ MonthlyABCAnalysis   │───▶│   Sheets Agent       │   │
│  │                  │    │     Engine           │    │   Integration        │   │
│  │ • POST /analyze  │    │                      │    │                      │   │
│  │ • GET /health    │    │ • process_data()     │    │ • Create Sheet       │   │
│  │ • GET /sample    │    │ • categorize_abc()   │    │ • Upload Data        │   │
│  └──────────────────┘    │ • analyze_month()    │    │ • Apply Formatting   │   │
│                          └──────────────────────┘    └──────────────────────┘   │
│                                     │                          │                 │
│                                     ▼                          ▼                 │
│  ┌──────────────────────────────────────────────────────────────────────────┐   │
│  │                         MONITORING DECORATOR                              │   │
│  │                         @monitor_task()                                   │   │
│  │                    Reports to MONITORING_URL (Port 8009)                  │   │
│  └──────────────────────────────────────────────────────────────────────────┘   │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
              ┌───────────────────────────────────────────────────┐
              │              EXTERNAL SERVICES                     │
              ├───────────────────────────────────────────────────┤
              │  ┌─────────────────┐    ┌─────────────────────┐   │
              │  │  Sheets Agent   │    │  Monitoring Agent   │   │
              │  │   (Port 8003)   │    │     (Port 8009)     │   │
              │  │                 │    │                     │   │
              │  │ • create_sheet  │    │ • task_started      │   │
              │  │ • upload_multi  │    │ • task_completed    │   │
              │  │ • formatting    │    │ • task_failed       │   │
              │  └─────────────────┘    └─────────────────────┘   │
              └───────────────────────────────────────────────────┘
```

---

## 3. Core Algorithm: ABC/Pareto Classification

### 3.1 Item Score Formula

```
Item Score = Total Quantity × Order Frequency
```

Where:
- **Total Quantity**: Sum of all quantities ordered for the item across the analysis period
- **Order Frequency**: Number of distinct orders containing the item

### 3.2 ABC Classification Thresholds

| Category | Cumulative % Threshold | Typical Items | Priority Level |
|----------|------------------------|---------------|----------------|
| **A** | 0% - 70% | ~20% of items | HIGH - Critical for business |
| **B** | 70% - 90% | ~30% of items | MEDIUM - Important |
| **C** | 90% - 100% | ~50% of items | LOW - Minimal impact |

### 3.3 Pareto Principle (80/20 Rule)

The ABC Analysis is based on the Pareto Principle:
- **~20% of items** (Category A) typically account for **~80% of value**
- **~80% of items** (Categories B+C) account for **~20% of value**

---

## 4. API Endpoints

### 4.1 POST /analyze

**Purpose**: Upload file and perform ABC analysis

**Request**:
```python
{
    "file": UploadFile,                    # Excel/CSV file
    "credentials_dict": CredentialsDict,   # Google OAuth credentials
    "spreadsheet_name": str,               # Name for output spreadsheet
    "item_column": str,                    # Column containing item identifiers
    "quantity_column": str,                # Column containing quantities
    "date_column": Optional[str],          # Column for date (monthly grouping)
    "start_date": Optional[str],           # Filter start date
    "end_date": Optional[str]              # Filter end date
}
```

**Response**:
```python
{
    "success": bool,
    "spreadsheet_id": str,
    "spreadsheet_url": str,
    "summary": {
        "total_items": int,
        "category_a_count": int,
        "category_b_count": int,
        "category_c_count": int,
        "months_analyzed": list
    },
    "sheets_created": list
}
```

### 4.2 GET /health

```python
{
    "status": "healthy",
    "service": "abc-analysis-agent",
    "version": "1.0.0"
}
```

### 4.3 GET /sample

Returns sample data format for testing.

---

## 5. Data Flow Sequence Diagram (SSD)

```
┌──────────┐     ┌─────────────┐     ┌───────────────────┐     ┌──────────────┐     ┌──────────────┐
│  Client  │     │ ABC Agent   │     │ MonthlyABCEngine  │     │ Sheets Agent │     │ Monitoring   │
│          │     │  (8007)     │     │                   │     │   (8003)     │     │   (8009)     │
└────┬─────┘     └──────┬──────┘     └─────────┬─────────┘     └──────┬───────┘     └──────┬───────┘
     │                  │                      │                      │                    │
     │  POST /analyze   │                      │                      │                    │
     │  (file + creds)  │                      │                      │                    │
     │─────────────────▶│                      │                      │                    │
     │                  │                      │                      │                    │
     │                  │  @monitor_task()     │                      │                    │
     │                  │  task_started        │                      │                    │
     │                  │──────────────────────┼──────────────────────┼───────────────────▶│
     │                  │                      │                      │                    │
     │                  │  parse_file()        │                      │                    │
     │                  │─────────────────────▶│                      │                    │
     │                  │                      │                      │                    │
     │                  │  process_data()      │                      │                    │
     │                  │─────────────────────▶│                      │                    │
     │                  │                      │                      │                    │
     │                  │     ┌────────────────┴────────────────┐     │                    │
     │                  │     │ FOR each month:                 │     │                    │
     │                  │     │  1. Filter data by month        │     │                    │
     │                  │     │  2. Calculate item scores       │     │                    │
     │                  │     │  3. Sort by score DESC          │     │                    │
     │                  │     │  4. Calculate cumulative %      │     │                    │
     │                  │     │  5. Assign A/B/C category       │     │                    │
     │                  │     └────────────────┬────────────────┘     │                    │
     │                  │                      │                      │                    │
     │                  │  POST /execute_task  │                      │                    │
     │                  │  (create_sheet)      │                      │                    │
     │                  │──────────────────────┼─────────────────────▶│                    │
     │                  │                      │                      │                    │
     │                  │    spreadsheet_id    │                      │                    │
     │                  │◀─────────────────────┼──────────────────────│                    │
     │                  │                      │                      │                    │
     │                  │  POST /execute_task  │                      │                    │
     │                  │  (upload_multi_sheet)│                      │                    │
     │                  │──────────────────────┼─────────────────────▶│                    │
     │                  │                      │                      │                    │
     │                  │  POST /execute_task  │                      │                    │
     │                  │  (apply_formatting)  │                      │                    │
     │                  │──────────────────────┼─────────────────────▶│                    │
     │                  │                      │                      │                    │
     │                  │  task_completed      │                      │                    │
     │                  │──────────────────────┼──────────────────────┼───────────────────▶│
     │                  │                      │                      │                    │
     │    Response      │                      │                      │                    │
     │  (spreadsheet_   │                      │                      │                    │
     │   url + summary) │                      │                      │                    │
     │◀─────────────────│                      │                      │                    │
     │                  │                      │                      │                    │
```

---

## 6. Activity Diagram

```
                            ┌─────────────────┐
                            │     START       │
                            └────────┬────────┘
                                     │
                                     ▼
                       ┌─────────────────────────────┐
                       │  Receive file + credentials │
                       └─────────────┬───────────────┘
                                     │
                                     ▼
                       ┌─────────────────────────────┐
                       │  Validate file format       │
                       │  (Excel/CSV)                │
                       └─────────────┬───────────────┘
                                     │
                              ┌──────┴──────┐
                              ▼             ▼
                        ┌──────────┐  ┌──────────────┐
                        │  Valid   │  │   Invalid    │
                        └────┬─────┘  └──────┬───────┘
                             │               │
                             │               ▼
                             │        ┌──────────────┐
                             │        │ Return Error │
                             │        └──────┬───────┘
                             │               │
                             ▼               │
                ┌────────────────────────┐   │
                │  Parse file to         │   │
                │  DataFrame             │   │
                └────────────┬───────────┘   │
                             │               │
                             ▼               │
                ┌────────────────────────┐   │
                │  Extract unique months │   │
                │  from date column      │   │
                └────────────┬───────────┘   │
                             │               │
                             ▼               │
            ┌────────────────────────────────┐
            │  LOOP: For each month          │◀──────┐
            └────────────────┬───────────────┘       │
                             │                       │
                             ▼                       │
            ┌────────────────────────────────┐       │
            │  Filter data for current month │       │
            └────────────────┬───────────────┘       │
                             │                       │
                             ▼                       │
            ┌────────────────────────────────┐       │
            │  Group by item:                │       │
            │  • Sum quantities              │       │
            │  • Count order frequency       │       │
            └────────────────┬───────────────┘       │
                             │                       │
                             ▼                       │
            ┌────────────────────────────────┐       │
            │  Calculate Item Score:         │       │
            │  Score = Qty × Frequency       │       │
            └────────────────┬───────────────┘       │
                             │                       │
                             ▼                       │
            ┌────────────────────────────────┐       │
            │  Sort items by Score DESC      │       │
            └────────────────┬───────────────┘       │
                             │                       │
                             ▼                       │
            ┌────────────────────────────────┐       │
            │  Calculate cumulative %        │       │
            └────────────────┬───────────────┘       │
                             │                       │
                             ▼                       │
            ┌────────────────────────────────┐       │
            │  Assign ABC Category:          │       │
            │  A: 0-70%, B: 70-90%, C: 90%+  │       │
            └────────────────┬───────────────┘       │
                             │                       │
                             ▼                       │
            ┌────────────────────────────────┐       │
            │  More months?                  │───Yes─┘
            └────────────────┬───────────────┘
                             │ No
                             ▼
            ┌────────────────────────────────┐
            │  Call Sheets Agent:            │
            │  1. Create spreadsheet         │
            │  2. Upload all month sheets    │
            │  3. Apply ABC formatting       │
            └────────────────┬───────────────┘
                             │
                             ▼
            ┌────────────────────────────────┐
            │  Return spreadsheet URL        │
            │  and analysis summary          │
            └────────────────┬───────────────┘
                             │
                             ▼
                       ┌───────────┐
                       │    END    │
                       └───────────┘
```

---

## 7. Data Models

### 7.1 CredentialsDict

```python
class CredentialsDict(BaseModel):
    """Google OAuth credentials structure"""
    token: str
    refresh_token: str
    token_uri: str
    client_id: str
    client_secret: str
    scopes: List[str]
    expiry: Optional[str] = None
```

### 7.2 AnalysisRequest

```python
class AnalysisRequest(BaseModel):
    """Request structure for ABC analysis"""
    spreadsheet_name: str
    item_column: str
    quantity_column: str
    date_column: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
```

### 7.3 MonthlyAnalysisResult

```python
{
    "month": "2024-01",
    "items": [
        {
            "item_code": "SKU-001",
            "total_quantity": 5000,
            "order_frequency": 45,
            "item_score": 225000,
            "cumulative_percentage": 15.5,
            "category": "A"
        },
        # ... more items
    ],
    "summary": {
        "total_items": 500,
        "category_a": 95,
        "category_b": 155,
        "category_c": 250
    }
}
```

---

## 8. Integration with Sheets Agent

The ABC Analysis Agent communicates with the Sheets Agent via HTTP POST requests:

### 8.1 Create Spreadsheet

```python
response = requests.post(
    f"{SHEETS_AGENT_URL}/execute_task",
    json={
        "tool": "create_sheet",
        "inputs": {
            "spreadsheet_name": "ABC Analysis - January 2024"
        },
        "credentials_dict": credentials
    }
)
```

### 8.2 Upload Multi-Sheet Data

```python
response = requests.post(
    f"{SHEETS_AGENT_URL}/execute_task",
    json={
        "tool": "upload_multi_sheet_data",
        "inputs": {
            "spreadsheet_id": spreadsheet_id,
            "sheets_data": {
                "Jan 2024": [headers] + jan_data,
                "Feb 2024": [headers] + feb_data,
                "Summary": [headers] + summary_data
            }
        },
        "credentials_dict": credentials
    }
)
```

### 8.3 Apply Formatting

```python
response = requests.post(
    f"{SHEETS_AGENT_URL}/execute_task",
    json={
        "tool": "apply_sheet_formatting",
        "inputs": {
            "spreadsheet_id": spreadsheet_id,
            "formatting_rules": {
                "category_a_color": "#90EE90",  # Green
                "category_b_color": "#FFFFE0",  # Yellow
                "category_c_color": "#FFB6C1"   # Red
            }
        },
        "credentials_dict": credentials
    }
)
```

---

## 9. Monitoring Integration

All API endpoints are decorated with `@monitor_task()` which automatically reports to the Monitoring Agent:

```python
# Events sent to Monitoring Agent (Port 8009)
{
    "event": "task_started" | "task_completed" | "task_failed",
    "agent": "abc-analysis-agent",
    "task_id": "uuid",
    "timestamp": "ISO-8601",
    "metadata": {
        "file_name": str,
        "items_count": int,
        "months_analyzed": int
    },
    "duration_ms": int  # Only on completion
}
```

---

## 10. Error Handling

| Error Type | HTTP Status | Description |
|------------|-------------|-------------|
| Invalid file format | 400 | File must be .xlsx, .xls, or .csv |
| Missing columns | 400 | Required columns not found in data |
| Invalid credentials | 401 | Google OAuth credentials invalid |
| Sheets API error | 502 | Failed to communicate with Sheets Agent |
| Processing error | 500 | Internal error during analysis |

---

## 11. Configuration

```python
# Environment Variables
ABC_AGENT_PORT = 8007
SHEETS_AGENT_URL = "http://localhost:8003"
MONITORING_URL = "http://localhost:8009"

# ABC Thresholds (configurable)
CATEGORY_A_THRESHOLD = 0.70  # 70%
CATEGORY_B_THRESHOLD = 0.90  # 90%
```

---

## 12. Sample Output

### Google Sheets Structure

```
📊 ABC Analysis - Q1 2024
├── 📄 January 2024
│   ├── Item Code | Quantity | Frequency | Score | Cumulative % | Category
│   └── [Data rows with color coding by category]
├── 📄 February 2024
│   └── [Same structure]
├── 📄 March 2024
│   └── [Same structure]
└── 📄 Summary
    ├── Month | Total Items | A Count | B Count | C Count | A Value %
    └── [Monthly summary rows]
```

---

## 13. Usage Example

```python
import requests

# Prepare the request
files = {"file": open("inventory_data.xlsx", "rb")}
data = {
    "spreadsheet_name": "ABC Analysis - Q1 2024",
    "item_column": "SKU",
    "quantity_column": "Qty Ordered",
    "date_column": "Order Date"
}
credentials = {
    "token": "ya29...",
    "refresh_token": "1//...",
    # ... other OAuth fields
}

# Call the ABC Analysis Agent
response = requests.post(
    "http://localhost:8007/analyze",
    files=files,
    data={"request": json.dumps(data), "credentials": json.dumps(credentials)}
)

result = response.json()
print(f"Spreadsheet URL: {result['spreadsheet_url']}")
print(f"Items analyzed: {result['summary']['total_items']}")
```
