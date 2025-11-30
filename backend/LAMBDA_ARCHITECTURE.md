# Lambda Architecture Diagrams

## Complete System Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           CLIENT LAYER                                  │
│                                                                         │
│  ┌──────────────┐         ┌──────────────┐         ┌──────────────┐   │
│  │   Web App    │         │    Mobile    │         │   Desktop    │   │
│  │  (React)     │         │     App      │         │     App      │   │
│  └──────┬───────┘         └──────┬───────┘         └──────┬───────┘   │
│         │                        │                        │            │
│         └────────────────────────┴────────────────────────┘            │
│                                  │                                     │
│                            HTTPS Requests                              │
└──────────────────────────────────┼──────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        AWS API GATEWAY                                  │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  HTTPS Endpoint: https://xxx.execute-api.us-east-1.amazonaws.com│   │
│  │                                                                  │   │
│  │  ✓ SSL/TLS Termination                                          │   │
│  │  ✓ Request Validation                                           │   │
│  │  ✓ CORS Configuration                                           │   │
│  │  ✓ Rate Limiting                                                │   │
│  │  ✓ API Key Management                                           │   │
│  │  ✓ Request/Response Transformation                              │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└──────────────────────────────────┼──────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        AWS LAMBDA FUNCTION                              │
│                                                                         │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │                    Lambda: knowledge-base-api                    │  │
│  │  ┌────────────────────────────────────────────────────────────┐  │  │
│  │  │  Runtime: Python 3.11                                      │  │  │
│  │  │  Memory: 3008 MB (3GB)                                     │  │  │
│  │  │  Timeout: 900 seconds (15 minutes)                         │  │  │
│  │  │  Handler: lambda_handler.handler                           │  │  │
│  │  └────────────────────────────────────────────────────────────┘  │  │
│  │                                                                  │  │
│  │  ┌────────────────────────────────────────────────────────────┐  │  │
│  │  │              FastAPI Application                           │  │  │
│  │  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  │  │  │
│  │  │  │   PDF    │  │    KB    │  │   Chat   │  │  Health  │  │  │  │
│  │  │  │  Routes  │  │  Routes  │  │  Routes  │  │  Routes  │  │  │  │
│  │  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘  │  │  │
│  │  │                                                            │  │  │
│  │  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  │  │  │
│  │  │  │   PDF    │  │Chunking  │  │  OpenAI  │  │  Query   │  │  │  │
│  │  │  │ Service  │  │ Service  │  │ Service  │  │Processor │  │  │  │
│  │  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘  │  │  │
│  │  │                                                            │  │  │
│  │  │  Wrapped by Mangum (ASGI → Lambda adapter)                │  │  │
│  │  └────────────────────────────────────────────────────────────┘  │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                                                         │
│  Environment Variables:                                                │
│  • OPENAI_API_KEY (from Secrets Manager or Parameter)                 │
│  • WEAVIATE_URL                                                        │
│  • WEAVIATE_API_KEY                                                    │
│  • JWT_SECRET_KEY                                                      │
│  • PDF_BUCKET_NAME                                                     │
│  • DOCUMENTS_TABLE                                                     │
│  • CHAT_TABLE                                                          │
└────────┬───────────────────┬──────────────────┬─────────────────────────┘
         │                   │                  │
         │                   │                  │
         ▼                   ▼                  ▼
┌─────────────────┐  ┌──────────────┐  ┌──────────────────┐
│   Amazon S3     │  │  DynamoDB    │  │    Weaviate      │
│                 │  │              │  │  (External SaaS) │
│  ┌───────────┐  │  │ ┌──────────┐ │  │                  │
│  │   PDFs    │  │  │ │Documents │ │  │  Vector Database │
│  │           │  │  │ │  Table   │ │  │                  │
│  │ Storage   │  │  │ └──────────┘ │  │  ┌────────────┐  │
│  └───────────┘  │  │              │  │  │  Chunks    │  │
│                 │  │ ┌──────────┐ │  │  │+ Vectors   │  │
│  Encryption:    │  │ │   Chat   │ │  │  └────────────┘  │
│  AES-256        │  │ │  Table   │ │  │                  │
│                 │  │ └──────────┘ │  │  Hybrid Search   │
│  Versioning:    │  │              │  │  (Vector + BM25) │
│  Enabled        │  │ On-Demand    │  │                  │
└─────────────────┘  │ Pricing      │  └──────────────────┘
                     │              │
                     │ TTL Enabled  │
                     └──────────────┘
                            │
                            ▼
                    ┌──────────────┐
                    │   OpenAI     │
                    │     API      │
                    │              │
                    │  GPT-4o      │
                    │  Embeddings  │
                    │  Vision      │
                    └──────────────┘

         ┌────────────────────────────────────┐
         │     CloudWatch Logs & Metrics      │
         │                                    │
         │  • Lambda Execution Logs           │
         │  • API Gateway Access Logs         │
         │  • Error Monitoring                │
         │  • Performance Metrics             │
         │  • Custom Alarms                   │
         └────────────────────────────────────┘
```

## Request Flow Diagram

```
User Request → API Gateway → Lambda → External Services → Response

Detailed Flow:

1. Client Request
   │
   ▼
2. API Gateway
   │ • Validates request
   │ • Checks rate limits
   │ • Handles CORS
   │ • Transforms to Lambda event
   ▼
3. Lambda Cold Start (if needed)
   │ • Download deployment package
   │ • Initialize runtime
   │ • Import dependencies
   │ • Initialize FastAPI app
   ▼
4. Lambda Execution
   │
   ├─► Mangum Adapter
   │   │ • Convert API Gateway event to ASGI
   │   │ • Route to FastAPI
   │   ▼
   │   FastAPI Application
   │   │ • Parse request
   │   │ • Validate input
   │   │ • Route to handler
   │   ▼
   │   Business Logic
   │   │
   │   ├─► PDF Processing
   │   │   │ • Download from S3
   │   │   │ • Extract text/images
   │   │   │ • Chunk content
   │   │   │ • Upload back to S3
   │   │   └─► OpenAI API
   │   │       │ • Generate embeddings
   │   │       │ • Chunk semantically
   │   │       └─► Return
   │   │
   │   ├─► Knowledge Base
   │   │   │ • Save to DynamoDB
   │   │   │ • Store in Weaviate
   │   │   └─► Return
   │   │
   │   └─► Chat
   │       │ • Query Weaviate
   │       │ • Get chat history (DynamoDB)
   │       │ • Generate response (OpenAI)
   │       │ • Save message (DynamoDB)
   │       └─► Return
   │
   ├─► Convert response to API Gateway format
   │   │ • Status code
   │   │ • Headers
   │   │ • Body
   │   └─► Return
   │
   ▼
5. API Gateway
   │ • Transform Lambda response
   │ • Add CORS headers
   │ • Log access
   │
   ▼
6. Client Response
```

## Deployment Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                Development Environment                      │
│                                                             │
│  Developer's Machine                                        │
│  ┌────────────────────────────────────────────────────┐    │
│  │  1. Write Code                                     │    │
│  │  2. Test Locally: sam local start-api              │    │
│  │  3. Build: sam build                               │    │
│  │  4. Deploy: sam deploy                             │    │
│  └────────────────┬───────────────────────────────────┘    │
│                   │                                         │
└───────────────────┼─────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────┐
│                   AWS CloudFormation                        │
│                                                             │
│  1. Read template.yaml                                      │
│  2. Create/Update Stack                                     │
│  3. Provision Resources:                                    │
│     ┌──────────────────────────────────────────────┐       │
│     │  • Lambda Function                           │       │
│     │  • API Gateway                               │       │
│     │  • DynamoDB Tables                           │       │
│     │  • S3 Bucket                                 │       │
│     │  • CloudWatch Log Groups                     │       │
│     │  • IAM Roles & Policies                      │       │
│     └──────────────────────────────────────────────┘       │
│  4. Configure Integrations                                  │
│  5. Return Outputs (API endpoint, etc.)                     │
└─────────────────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────┐
│               Production Environment (AWS)                  │
│                                                             │
│  All resources running and integrated                       │
│  Ready to handle requests                                   │
└─────────────────────────────────────────────────────────────┘
```

## Storage Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Data Flow                                │
└─────────────────────────────────────────────────────────────────┘

PDF Upload:
┌──────┐    ┌─────────┐    ┌──────┐    ┌──────────┐    ┌─────────┐
│Client│───>│API Gate │───>│Lambda│───>│    S3    │───>│OpenAI   │
└──────┘    │         │    │      │    │          │    │ GPT-4   │
            └─────────┘    │      │    │ /pdfs/   │    └────┬────┘
                           │      │    │ file.pdf │         │
                           │      │    └──────────┘         │
                           │      │                         │
                           │      │◄────────────────────────┘
                           │      │   Chunks + Embeddings
                           │      │
                           │      ├──>┌──────────┐
                           │      │   │DynamoDB  │ (Metadata)
                           │      │   └──────────┘
                           │      │
                           │      └──>┌──────────┐
                           │          │Weaviate  │ (Vectors)
                           │          └──────────┘
                           └──────┘

Query Flow:
┌──────┐    ┌─────────┐    ┌──────┐    ┌─────────┐    ┌──────────┐
│Client│───>│API Gate │───>│Lambda│───>│Weaviate │───>│  OpenAI  │
└──────┘    │         │    │      │    │         │    │          │
            └─────────┘    │      │    │ Search  │    │ Generate │
                           │      │    └─────────┘    │ Answer   │
                           │      │                   └────┬─────┘
                           │      │                        │
                           │      │◄───────────────────────┘
                           │      │   AI Response
                           │      │
                           │      └──>┌──────────┐
                           │          │DynamoDB  │ (Save Chat)
                           │          └──────────┘
                           └──────┘
```

## Scalability Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Auto-Scaling Behavior                        │
└─────────────────────────────────────────────────────────────────┘

Low Traffic:
┌──────┐      ┌────────────┐
│ User │─────>│ Lambda (1) │  Single instance
└──────┘      └────────────┘

Medium Traffic:
┌──────┐      ┌────────────┐
│User 1│─────>│ Lambda (1) │
└──────┘      └────────────┘
┌──────┐      ┌────────────┐
│User 2│─────>│ Lambda (2) │  AWS auto-scales
└──────┘      └────────────┘
┌──────┐      ┌────────────┐
│User 3│─────>│ Lambda (3) │
└──────┘      └────────────┘

High Traffic:
┌──────┐      ┌────────────┐
│User 1│─────>│ Lambda (1) │
└──────┘      └────────────┘
┌──────┐      ┌────────────┐
│User 2│─────>│ Lambda (2) │
└──────┘      └────────────┘
    ⋮              ⋮
┌──────┐      ┌────────────┐
│UserN │─────>│ Lambda (N) │  Up to 1000 concurrent
└──────┘      └────────────┘  (default limit)

Idle Period:
(No Lambda instances running - zero cost)
```

## Security Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Security Layers                              │
└─────────────────────────────────────────────────────────────────┘

Layer 1: Network Security
┌──────────────────────────────────────────────────────────────┐
│  • HTTPS/TLS 1.2+ (API Gateway)                              │
│  • VPC Integration (Optional)                                │
│  • Private Subnets for Lambda (Optional)                     │
│  • Security Groups                                           │
└──────────────────────────────────────────────────────────────┘

Layer 2: Access Control
┌──────────────────────────────────────────────────────────────┐
│  • IAM Roles & Policies                                      │
│  • API Key Authentication                                    │
│  • JWT Token Validation                                      │
│  • CORS Restrictions                                         │
│  • Rate Limiting                                             │
└──────────────────────────────────────────────────────────────┘

Layer 3: Data Protection
┌──────────────────────────────────────────────────────────────┐
│  • S3 Server-Side Encryption (AES-256)                       │
│  • DynamoDB Encryption at Rest                               │
│  • Environment Variables Encryption (KMS)                    │
│  • Secrets Manager for API Keys                              │
│  • SSL in Transit                                            │
└──────────────────────────────────────────────────────────────┘

Layer 4: Application Security
┌──────────────────────────────────────────────────────────────┐
│  • Input Validation (Pydantic)                               │
│  • File Type Validation                                      │
│  • File Size Limits                                          │
│  • SQL Injection Prevention (NoSQL)                          │
│  • XSS Protection                                            │
└──────────────────────────────────────────────────────────────┘

Layer 5: Monitoring & Auditing
┌──────────────────────────────────────────────────────────────┐
│  • CloudWatch Logs (All requests)                            │
│  • CloudTrail (API calls to AWS services)                    │
│  • X-Ray Tracing (Request path analysis)                     │
│  • Custom Metrics & Alarms                                   │
│  • Error Tracking                                            │
└──────────────────────────────────────────────────────────────┘
```

## Cost Optimization Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                  Cost Components                                │
└─────────────────────────────────────────────────────────────────┘

Lambda Costs:
• Requests: $0.20 per 1M requests
• Compute: $0.0000166667 per GB-second
└─► Optimization: Right-size memory, minimize execution time

DynamoDB Costs:
• On-Demand: $1.25 per million writes, $0.25 per million reads
└─► Optimization: Use TTL, batch operations, efficient queries

S3 Costs:
• Storage: $0.023 per GB
• Requests: $0.0004 per 1000 PUT, $0.0004 per 10,000 GET
└─► Optimization: Lifecycle policies, compression

API Gateway Costs:
• HTTP API: $1.00 per million requests
└─► Optimization: Caching, minimize requests

Total Estimated Cost (10K requests/month):
┌────────────────────┬──────────┐
│ Service            │   Cost   │
├────────────────────┼──────────┤
│ Lambda             │  $15.00  │
│ DynamoDB           │   $2.00  │
│ S3                 │   $1.00  │
│ API Gateway        │   $0.01  │
│ CloudWatch         │   $0.50  │
├────────────────────┼──────────┤
│ Total              │  $18.51  │
└────────────────────┴──────────┘
```

## Disaster Recovery Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                  Backup & Recovery Strategy                     │
└─────────────────────────────────────────────────────────────────┘

S3 (PDFs):
┌──────────────────────────────────────────────────────────┐
│  • Versioning: Enabled                                   │
│  • Cross-Region Replication: Optional                    │
│  • Lifecycle: Archive to Glacier after 90 days           │
│  • Recovery: Instant (retrieve any version)              │
└──────────────────────────────────────────────────────────┘

DynamoDB:
┌──────────────────────────────────────────────────────────┐
│  • Point-in-Time Recovery: Enabled                       │
│  • Backups: Daily automatic backups                      │
│  • Global Tables: Multi-region replication (Optional)    │
│  • Recovery: Restore to any point in last 35 days        │
└──────────────────────────────────────────────────────────┘

Lambda:
┌──────────────────────────────────────────────────────────┐
│  • Code: Stored in S3 deployment bucket                  │
│  • Infrastructure: Defined in template.yaml (Git)        │
│  • Recovery: Redeploy from Git + SAM                     │
└──────────────────────────────────────────────────────────┘

Weaviate:
┌──────────────────────────────────────────────────────────┐
│  • Backup: Weaviate Cloud handles backups                │
│  • Recovery: Re-index from source documents if needed    │
└──────────────────────────────────────────────────────────┘
```

---

**Note**: All diagrams represent the production architecture when deployed to AWS Lambda. Local development uses the original architecture (FastAPI + SQLite + local files).
