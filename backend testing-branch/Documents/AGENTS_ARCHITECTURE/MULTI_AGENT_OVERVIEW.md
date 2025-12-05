# Multi-Agent System Architecture - Overview

## Executive Summary

This document provides a comprehensive overview of the multi-agent system architecture comprising four specialized microservices that work together to provide data processing, analysis, and Google Sheets integration capabilities.

---

## 1. System Overview

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                    MULTI-AGENT SYSTEM ARCHITECTURE                                   │
├─────────────────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                                      │
│                                         ┌───────────────────┐                                        │
│                                         │   CLIENT / UI     │                                        │
│                                         │   (Frontend)      │                                        │
│                                         └─────────┬─────────┘                                        │
│                                                   │                                                  │
│                                                   ▼                                                  │
│    ┌─────────────────────────────────────────────────────────────────────────────────────────────┐  │
│    │                                     AGENT LAYER                                              │  │
│    │                                                                                              │  │
│    │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────────┐ │  │
│    │  │ ABC Analysis    │  │ Mapping Agent   │  │ Sheets Agent    │  │ Workload Agent          │ │  │
│    │  │ Agent           │  │                 │  │                 │  │                         │ │  │
│    │  │ Port: 8007      │  │ Port: 8004      │  │ Port: 8003      │  │ Port: 8008              │ │  │
│    │  │                 │  │                 │  │                 │  │                         │ │  │
│    │  │ Monthly ABC/    │  │ • File Parsing  │  │ • Google Sheets │  │ • Time Study Analysis   │ │  │
│    │  │ Pareto Analysis │  │ • Smart Column  │  │   CRUD          │  │ • Workforce Planning    │ │  │
│    │  │                 │  │   Mapping       │  │ • Multi-sheet   │  │ • Capacity Analysis     │ │  │
│    │  │                 │  │ • Data Transform│  │   Support       │  │                         │ │  │
│    │  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘  └────────┬────────────────┘ │  │
│    │           │                    │                    │                    │                  │  │
│    │           │                    │                    │                    │                  │  │
│    │           └──────────┬─────────┴─────────┬──────────┴────────────────────┘                  │  │
│    │                      │                   │                                                   │  │
│    │                      ▼                   ▼                                                   │  │
│    │           ┌─────────────────────────────────────────┐                                        │  │
│    │           │          MONITORING AGENT               │                                        │  │
│    │           │          Port: 8009                     │                                        │  │
│    │           │                                         │                                        │  │
│    │           │  • Task tracking (started/completed)    │                                        │  │
│    │           │  • Performance metrics                  │                                        │  │
│    │           │  • Error logging                        │                                        │  │
│    │           └─────────────────────────────────────────┘                                        │  │
│    │                                                                                              │  │
│    └──────────────────────────────────────────────────────────────────────────────────────────────┘  │
│                                                   │                                                  │
│                                                   ▼                                                  │
│    ┌─────────────────────────────────────────────────────────────────────────────────────────────┐  │
│    │                                     EXTERNAL SERVICES                                        │  │
│    │                                                                                              │  │
│    │  ┌─────────────────────────────┐    ┌─────────────────────────────────────────────────────┐ │  │
│    │  │        OpenAI API           │    │              Google Cloud                            │ │  │
│    │  │  (LLM for smart mapping)    │    │  • Google Sheets API v4                             │ │  │
│    │  │                             │    │  • Google Drive API v3                               │ │  │
│    │  └─────────────────────────────┘    └─────────────────────────────────────────────────────┘ │  │
│    │                                                                                              │  │
│    └──────────────────────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                                      │
└──────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Agent Summary

| Agent | Port | Primary Function | Key Capabilities |
|-------|------|------------------|------------------|
| **ABC Analysis Agent** | 8007 | Monthly Pareto Analysis | ABC categorization, multi-month analysis, Sheets integration |
| **Mapping Agent** | 8004 | Data Intelligence | File parsing, AI column mapping, data transformation |
| **Sheets Agent** | 8003 | Google Sheets CRUD | Create, read, update, multi-sheet, formatting |
| **Workload Agent** | 8008 | Workforce Planning | Time study, capacity analysis, FTE calculation |
| **Monitoring Agent** | 8009 | System Monitoring | Task tracking, metrics, error logging |

---

## 3. Inter-Agent Communication

### 3.1 Communication Pattern

All agents use **HTTP REST** for inter-agent communication:

```python
# Standard request pattern
response = requests.post(
    f"http://localhost:{AGENT_PORT}/execute_task",
    json={
        "tool": "tool_name",
        "inputs": {...},
        "credentials_dict": {...}  # For Sheets Agent only
    }
)
```

### 3.2 Agent Dependencies

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                          AGENT DEPENDENCY GRAPH                                  │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│                    ┌───────────────────────────────────┐                         │
│                    │       ABC Analysis Agent          │                         │
│                    │          (Port 8007)              │                         │
│                    └───────────────┬───────────────────┘                         │
│                                    │                                             │
│                                    │ 1. create_sheet                             │
│                                    │ 2. upload_multi_sheet_data                  │
│                                    │ 3. apply_sheet_formatting                   │
│                                    │                                             │
│                                    ▼                                             │
│                    ┌───────────────────────────────────┐                         │
│                    │        Sheets Agent               │◀─────────────────┐      │
│                    │          (Port 8003)              │                  │      │
│                    └───────────────────────────────────┘                  │      │
│                                                                           │      │
│                                                                           │      │
│                    ┌───────────────────────────────────┐                  │      │
│                    │        Mapping Agent              │──── (potential) ─┘      │
│                    │          (Port 8004)              │    upload_mapped_data   │
│                    └───────────────────────────────────┘                         │
│                                    │                                             │
│                                    │ smart_column_mapping                        │
│                                    │ (Tier 3 fallback)                           │
│                                    ▼                                             │
│                    ┌───────────────────────────────────┐                         │
│                    │          OpenAI API               │                         │
│                    └───────────────────────────────────┘                         │
│                                                                                  │
│                                                                                  │
│                    ┌───────────────────────────────────┐                         │
│                    │       Workload Agent              │                         │
│                    │          (Port 8008)              │                         │
│                    └───────────────────────────────────┘                         │
│                              (Standalone - no dependencies)                      │
│                                                                                  │
│                                                                                  │
│     ┌─────────────────────────────────────────────────────────────────────┐     │
│     │                    ALL AGENTS                                        │     │
│     │                       │                                              │     │
│     │                       │ @monitor_task()                              │     │
│     │                       │ task_started / task_completed / task_failed  │     │
│     │                       ▼                                              │     │
│     │            ┌───────────────────────────────────┐                     │     │
│     │            │       Monitoring Agent            │                     │     │
│     │            │          (Port 8009)              │                     │     │
│     │            └───────────────────────────────────┘                     │     │
│     └─────────────────────────────────────────────────────────────────────┘     │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Common Patterns

### 4.1 Monitoring Decorator

All agents use the `@monitor_task()` decorator for automatic task tracking:

```python
@app.post("/analyze")
@monitor_task()
async def analyze(request: AnalysisRequest):
    # Task automatically tracked:
    # 1. task_started event sent to Monitoring Agent
    # 2. On success: task_completed event sent
    # 3. On failure: task_failed event sent
    pass
```

### 4.2 Standard Response Pattern

```python
class ToolResponse(BaseModel):
    success: bool
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
```

### 4.3 Health Check Endpoint

All agents expose a `/health` endpoint:

```python
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "agent-name",
        "version": "X.Y.Z"
    }
```

---

## 5. Data Flow Examples

### 5.1 ABC Analysis Workflow

```
User Upload → ABC Agent → Parse File → Analyze by Month → Sheets Agent → Google Sheets
                              ↓
                        Calculate:
                        • Item Score = Qty × Frequency
                        • Cumulative %
                        • A/B/C Category
```

### 5.2 Smart Mapping Workflow

```
Source File → Mapping Agent → Parse → Smart Mapping Engine → Transformed Data
                                              ↓
                                   Tier 1: Exact Match
                                        ↓ (no match)
                                   Tier 2: Rule-Based
                                        ↓ (no match)
                                   Tier 3: OpenAI LLM
```

### 5.3 Workload Analysis Workflow

```
Excel Upload → Workload Agent → Parse Sheets → Calculate Times → Project FTE
                                     ↓
                              Extract:
                              • Time Studies
                              • Volumes
                              • Resources
```

---

## 6. Deployment Configuration

### 6.1 Port Assignments

| Agent | Default Port | Environment Variable |
|-------|-------------|----------------------|
| Sheets Agent | 8003 | `SHEETS_AGENT_PORT` |
| Mapping Agent | 8004 | `MAPPING_AGENT_PORT` |
| ABC Analysis Agent | 8007 | `ABC_AGENT_PORT` |
| Workload Agent | 8008 | `WORKLOAD_AGENT_PORT` |
| Monitoring Agent | 8009 | `MONITORING_PORT` |

### 6.2 Environment Variables

```bash
# Common
MONITORING_URL=http://localhost:8009

# Sheets Agent
SHEETS_AGENT_PORT=8003

# Mapping Agent
MAPPING_AGENT_PORT=8004
OPENAI_API_KEY=sk-...

# ABC Analysis Agent
ABC_AGENT_PORT=8007
SHEETS_AGENT_URL=http://localhost:8003

# Workload Agent
WORKLOAD_AGENT_PORT=8008
```

### 6.3 Startup Order

```
1. Monitoring Agent (8009)     ← Start first (other agents depend on it)
2. Sheets Agent (8003)         ← Required by ABC Agent
3. Mapping Agent (8004)        ← Can start independently
4. Workload Agent (8008)       ← Can start independently
5. ABC Analysis Agent (8007)   ← Start last (depends on Sheets Agent)
```

---

## 7. Technology Stack

| Component | Technology |
|-----------|------------|
| **Framework** | FastAPI (Python) |
| **Data Processing** | Pandas |
| **File Parsing** | openpyxl, csv |
| **Google APIs** | google-auth, google-api-python-client |
| **HTTP Client** | requests |
| **LLM Integration** | OpenAI API |
| **Validation** | Pydantic |

---

## 8. Security Considerations

### 8.1 OAuth Credentials

- Google OAuth credentials passed per-request (not stored)
- Credentials validated by Google API on each call
- Token refresh handled automatically

### 8.2 API Security

- All inter-agent communication is HTTP (consider HTTPS in production)
- No authentication between agents (internal network assumption)
- Rate limiting recommended for production

### 8.3 Data Handling

- Files processed in memory, not persisted
- No sensitive data logging
- Credentials excluded from logs

---

## 9. Monitoring & Observability

### 9.1 Metrics Collected

| Metric | Description |
|--------|-------------|
| `task_started` | Task initiation with metadata |
| `task_completed` | Successful completion with duration |
| `task_failed` | Failure with error details |
| `duration_ms` | Processing time in milliseconds |

### 9.2 Log Format

```python
{
    "event": "task_completed",
    "agent": "abc-analysis-agent",
    "task_id": "uuid",
    "timestamp": "ISO-8601",
    "duration_ms": 5432,
    "metadata": {
        "file_name": "inventory.xlsx",
        "items_count": 500,
        "months_analyzed": 3
    }
}
```

---

## 10. Documentation Index

| Document | Description | Location |
|----------|-------------|----------|
| ABC Analysis Agent | Pareto analysis documentation | [ABC_ANALYSIS_AGENT.md](./ABC_ANALYSIS_AGENT.md) |
| Mapping Agent | Data transformation documentation | [MAPPING_AGENT.md](./MAPPING_AGENT.md) |
| Sheets Agent | Google Sheets CRUD documentation | [SHEETS_AGENT.md](./SHEETS_AGENT.md) |
| Workload Agent | Workforce planning documentation | [WORKLOAD_AGENT.md](./WORKLOAD_AGENT.md) |

---

## 11. Quick Reference

### Start All Agents (Windows)

```batch
:: Start Monitoring Agent
start /B python monitoring_agent_api.py

:: Start Sheets Agent
start /B python sheets_agent_api.py

:: Start Mapping Agent
start /B python mapping_agent_api.py

:: Start Workload Agent
start /B python workload_agent_api.py

:: Start ABC Analysis Agent
start /B python abc_analysis_agent_api.py
```

### Health Check All Agents

```batch
curl http://localhost:8009/health
curl http://localhost:8003/health
curl http://localhost:8004/health
curl http://localhost:8007/health
curl http://localhost:8008/health
```

---

## 12. Future Considerations

1. **Service Discovery**: Consider adding Consul or similar for dynamic agent discovery
2. **Message Queue**: Replace HTTP with RabbitMQ/Kafka for async processing
3. **API Gateway**: Add Kong or similar for centralized routing
4. **Container Orchestration**: Kubernetes deployment for scalability
5. **Distributed Tracing**: Add Jaeger/Zipkin for cross-agent tracing
