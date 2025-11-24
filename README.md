# Knowledge Base - PDF Processing & Vector Search System

A full-stack application for uploading, processing, and querying PDF documents using AI-powered semantic search. Built with React, Flask, and Weaviate vector database.

## 🚀 Features

### PDF Processing
- **Smart PDF Upload**: Drag-and-drop interface for PDF files
- **Duplicate Detection**: SHA256 hash-based duplicate prevention
- **AI-Powered Chunking**: GPT-4 semantic chunking for optimal context
- **Image Analysis**: GPT-4 Vision for image description and understanding
- **Coordinate Anchoring**: Maps AI chunks back to exact PDF positions
- **Real-time Preview**: Side-by-side PDF preview with chunk highlighting

### Knowledge Base
- **Vector Search**: Semantic search using OpenAI embeddings (1536 dimensions)
- **Hybrid Search**: Combines vector similarity with keyword matching (BM25)
- **Document Management**: List, view, and delete uploaded documents
- **Chat Interface**: AI-powered Q&A over your document collection
- **History Tracking**: Local SQLite database for upload history

### User Interface
- **Modern React UI**: Clean, responsive design with Vite
- **Document Extraction View**: Interactive PDF viewer with chunk editing
- **Markdown Support**: Rich text rendering with ReactMarkdown
- **TipTap Editor**: WYSIWYG editing for chunk content
- **Upload History**: Toggle-able table view of all uploaded files

## 📋 Prerequisites

- **Python 3.8+** (Backend)
- **Node.js 16+** (Frontend)
- **OpenAI API Key** (Required)
- **Weaviate Cloud Account** (Optional - for KB features)

## 🛠️ Installation

### Backend Setup

1. **Navigate to backend directory:**
```powershell
cd backend
```

2. **Create virtual environment:**
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

3. **Install dependencies:**
```powershell
pip install -r requirements.txt
```

4. **Create `.env` file:**
```env
OPENAI_API_KEY=your-openai-api-key-here
WEAVIATE_URL=your-weaviate-cluster-url
WEAVIATE_API_KEY=your-weaviate-api-key
```

5. **Run the backend server:**
```powershell
python app.py
```

Backend will run on `http://127.0.0.1:8009`

### Frontend Setup

1. **Navigate to frontend directory:**
```powershell
cd frontend
```

2. **Install dependencies:**
```powershell
npm install
```

3. **Start development server:**
```powershell
npm run dev
```

Frontend will run on `http://localhost:5173`

## 📦 Project Structure

```
Knowledge-Base/
├── backend/
│   ├── api/                    # API routes
│   │   ├── chat_routes.py      # Chat endpoints
│   │   ├── kb_routes.py        # Knowledge base endpoints
│   │   ├── pdf_routes.py       # PDF processing endpoints
│   │   └── routes.py           # Route registration
│   ├── core/                   # Core processing modules
│   │   ├── pdf_extractor.py    # PDF parsing logic
│   │   └── table_processor.py  # Table detection
│   ├── database/               # Database operations
│   │   ├── operations.py       # CRUD operations
│   │   └── weaviate_client.py  # Vector DB client
│   ├── services/               # Business logic
│   │   ├── anchoring_service.py    # Chunk anchoring
│   │   ├── chunking_service.py     # AI chunking
│   │   ├── openai_service.py       # OpenAI integration
│   │   └── pdf_service.py          # PDF orchestration
│   ├── utils/                  # Utility functions
│   ├── app.py                  # Flask application entry
│   ├── config.py               # Configuration
│   └── requirements.txt        # Python dependencies
│
└── frontend/
    ├── src/
    │   ├── components/         # React components
    │   │   ├── DocumentExtraction.jsx  # Main PDF viewer
    │   │   ├── ChatInterface.jsx       # Chat UI
    │   │   ├── Dashboard.jsx           # Dashboard
    │   │   └── ...
    │   ├── css/                # Stylesheets
    │   ├── App.jsx             # Root component
    │   └── main.jsx            # Entry point
    ├── package.json            # Node dependencies
    └── vite.config.js          # Vite configuration
```

## 🔧 Configuration

### Backend Configuration (`backend/config.py`)

```python
# OpenAI Settings
OPENAI_MODEL = "gpt-4o"
EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSIONS = 1536

# PDF Processing
MAX_FILE_SIZE_MB = 10
LINE_TOLERANCE = 5
BATCH_SIZE = 100

# Server
DEBUG = True
PORT = 8009
```

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `OPENAI_API_KEY` | OpenAI API key for GPT-4 and embeddings | ✅ Yes |
| `WEAVIATE_URL` | Weaviate cluster URL | ⚠️ For KB features |
| `WEAVIATE_API_KEY` | Weaviate API key | ⚠️ For KB features |

## 🎯 Usage

### 1. Upload a PDF

1. Click "Upload a PDF" button
2. Select or drag-drop a PDF file (max 10MB)
3. Click "Upload" to process
4. Wait for AI chunking (10-25 seconds)
5. Review chunks in the parse view

### 2. View Upload History

1. Click "History" button in top right
2. View table of uploaded files with:
   - File name
   - Original filename
   - Upload date
   - File size
   - Delete action

### 3. Upload to Knowledge Base

1. After parsing, click "Upload to Knowledge Base"
2. Chunks are vectorized and stored in Weaviate
3. Documents become searchable via semantic search

### 4. Search Documents

1. Navigate to Chat Interface
2. Ask questions about your documents
3. AI retrieves relevant chunks and generates answers

## 📊 API Endpoints

### PDF Processing

```http
POST /pdf/parse-pdf
Content-Type: multipart/form-data

# Parses PDF and returns AI-generated chunks
# Includes duplicate detection
```

### Knowledge Base

```http
POST /kb/upload-to-kb
Content-Type: application/json

# Uploads chunks to vector database
```

```http
GET /kb/list-kb

# Lists all uploaded documents
```

```http
POST /kb/query
Content-Type: application/json

# Queries knowledge base with semantic search
```

## 🔍 How It Works

### System Sequence Diagram (SSD)

#### PDF Upload & Processing Flow

```
┌──────┐          ┌──────────┐          ┌──────────┐          ┌─────────┐          ┌──────────┐
│ User │          │ Frontend │          │ Backend  │          │ OpenAI  │          │ Weaviate │
└───┬──┘          └────┬─────┘          └────┬─────┘          └────┬────┘          └────┬─────┘
    │                  │                     │                     │                     │
    │ 1. Select PDF    │                     │                     │                     │
    │─────────────────>│                     │                     │                     │
    │                  │                     │                     │                     │
    │                  │ 2. POST /pdf/parse-pdf (file)             │                     │
    │                  │────────────────────>│                     │                     │
    │                  │                     │                     │                     │
    │                  │                     │ 3. Validate file    │                     │
    │                  │                     │ (type, size, hash)  │                     │
    │                  │                     │─────────┐           │                     │
    │                  │                     │         │           │                     │
    │                  │                     │<────────┘           │                     │
    │                  │                     │                     │                     │
    │                  │                     │ 4. Check duplicates │                     │
    │                  │                     │ (SQLite DB)         │                     │
    │                  │                     │─────────┐           │                     │
    │                  │                     │         │           │                     │
    │                  │                     │<────────┘           │                     │
    │                  │                     │                     │                     │
    │                  │                     │ 5. Extract PDF      │                     │
    │                  │                     │ (pdfplumber/PyMuPDF)│                     │
    │                  │                     │─────────┐           │                     │
    │                  │                     │         │           │                     │
    │                  │                     │<────────┘           │                     │
    │                  │                     │                     │                     │
    │                  │                     │ 6. AI Text Chunking │                     │
    │                  │                     │────────────────────>│                     │
    │                  │                     │                     │                     │
    │                  │                     │ 7. Return chunks    │                     │
    │                  │                     │<────────────────────│                     │
    │                  │                     │                     │                     │
    │                  │                     │ 8. AI Image Analysis│                     │
    │                  │                     │────────────────────>│                     │
    │                  │                     │                     │                     │
    │                  │                     │ 9. Return analysis  │                     │
    │                  │                     │<────────────────────│                     │
    │                  │                     │                     │                     │
    │                  │                     │ 10. Anchor to PDF   │                     │
    │                  │                     │─────────┐           │                     │
    │                  │                     │         │           │                     │
    │                  │                     │<────────┘           │                     │
    │                  │                     │                     │                     │
    │                  │ 11. Return chunks + metadata              │                     │
    │                  │<────────────────────│                     │                     │
    │                  │                     │                     │                     │
    │ 12. Display chunks│                    │                     │                     │
    │<─────────────────│                     │                     │                     │
    │                  │                     │                     │                     │
    │ 13. Click "Upload to KB"               │                     │                     │
    │─────────────────>│                     │                     │                     │
    │                  │                     │                     │                     │
    │                  │ 14. POST /kb/upload-to-kb (chunks)        │                     │
    │                  │────────────────────>│                     │                     │
    │                  │                     │                     │                     │
    │                  │                     │ 15. Store metadata  │                     │
    │                  │                     │ (SQLite DB)         │                     │
    │                  │                     │─────────┐           │                     │
    │                  │                     │         │           │                     │
    │                  │                     │<────────┘           │                     │
    │                  │                     │                     │                     │
    │                  │                     │ 16. Create document │                     │
    │                  │                     │─────────────────────────────────────────>│
    │                  │                     │                     │                     │
    │                  │                     │ 17. Generate embeddings (per chunk)       │
    │                  │                     │────────────────────>│                     │
    │                  │                     │                     │                     │
    │                  │                     │ 18. Return vectors  │                     │
    │                  │                     │<────────────────────│                     │
    │                  │                     │                     │                     │
    │                  │                     │ 19. Store chunks + vectors                │
    │                  │                     │─────────────────────────────────────────>│
    │                  │                     │                     │                     │
    │                  │                     │ 20. Confirm storage │                     │
    │                  │                     │<─────────────────────────────────────────│
    │                  │                     │                     │                     │
    │                  │ 21. Success response│                     │                     │
    │                  │<────────────────────│                     │                     │
    │                  │                     │                     │                     │
    │ 22. Show success │                     │                     │                     │
    │<─────────────────│                     │                     │                     │
    │                  │                     │                     │                     │
```

#### Query & Search Flow

```
┌──────┐          ┌──────────┐          ┌──────────┐          ┌─────────┐          ┌──────────┐
│ User │          │ Frontend │          │ Backend  │          │ OpenAI  │          │ Weaviate │
└───┬──┘          └────┬─────┘          └────┬─────┘          └────┬────┘          └────┬─────┘
    │                  │                     │                     │                     │
    │ 1. Ask question  │                     │                     │                     │
    │─────────────────>│                     │                     │                     │
    │                  │                     │                     │                     │
    │                  │ 2. POST /kb/query (question)              │                     │
    │                  │────────────────────>│                     │                     │
    │                  │                     │                     │                     │
    │                  │                     │ 3. Generate query embedding               │
    │                  │                     │────────────────────>│                     │
    │                  │                     │                     │                     │
    │                  │                     │ 4. Return vector    │                     │
    │                  │                     │<────────────────────│                     │
    │                  │                     │                     │                     │
    │                  │                     │ 5. Hybrid search (vector + keyword)       │
    │                  │                     │─────────────────────────────────────────>│
    │                  │                     │                     │                     │
    │                  │                     │ 6. Return top chunks│                     │
    │                  │                     │<─────────────────────────────────────────│
    │                  │                     │                     │                     │
    │                  │                     │ 7. Generate answer from context           │
    │                  │                     │────────────────────>│                     │
    │                  │                     │                     │                     │
    │                  │                     │ 8. Return AI response                     │
    │                  │                     │<────────────────────│                     │
    │                  │                     │                     │                     │
    │                  │ 9. Return answer + sources                │                     │
    │                  │<────────────────────│                     │                     │
    │                  │                     │                     │                     │
    │ 10. Display answer│                    │                     │                     │
    │<─────────────────│                     │                     │                     │
    │                  │                     │                     │                     │
```

### PDF Processing Pipeline

1. **Upload & Validation** → Security checks, file type validation
2. **Duplicate Detection** → SHA256 hash comparison (saves API costs)
3. **PDF Extraction** → Text, images, tables with coordinates
4. **AI Chunking** → GPT-4 semantic chunking (2 passes)
5. **Coordinate Anchoring** → Maps chunks to PDF positions
6. **Return Chunks** → Ready for KB upload

### Vector Search

1. **Upload to KB** → Chunks stored in Weaviate with embeddings
2. **Query** → User question converted to vector
3. **Hybrid Search** → Vector similarity + keyword matching
4. **Retrieval** → Top relevant chunks returned
5. **AI Response** → GPT-4 generates answer from context

## 🔒 Security Features

- ✅ File type validation (PDF only)
- ✅ File size limits (10MB default)
- ✅ Filename sanitization
- ✅ Content hash duplicate detection
- ✅ Rate limiting (20 uploads/hour)
- ✅ Input validation with Pydantic schemas

## 🐛 Troubleshooting

### Backend won't start

**Error:** `ModuleNotFoundError: No module named 'flask'`
```powershell
# Make sure virtual environment is activated
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

**Error:** `RuntimeError: OPENAI_API_KEY not set`
```powershell
# Create .env file in backend directory with your API key
```

### Frontend build errors

```powershell
# Clear node_modules and reinstall
Remove-Item -Recurse -Force node_modules
npm install
```

### Connection refused (ERR_CONNECTION_REFUSED)

```powershell
# Make sure backend is running on port 8009
cd backend
python app.py
```

### Weaviate errors

If you don't need Knowledge Base features:
- The backend will run without Weaviate (PDF parsing still works)
- You'll see a warning: "⚠️ Weaviate configuration not found"
- Upload to KB button will not function

## 📈 Performance

- **PDF Parsing**: 10-25 seconds (typical document)
- **Duplicate Check**: ~10ms (SQLite)
- **AI Chunking**: 3-8 seconds (GPT-4)
- **Image Analysis**: 2-5 seconds per image
- **Vector Search**: ~50-200ms (Weaviate)

## 🔮 Future Enhancements

- [ ] Support for Word, PowerPoint, Excel files
- [ ] Batch PDF uploads
- [ ] Advanced chunk editing (merge/split)
- [ ] Export search results
- [ ] User authentication
- [ ] Custom chunking strategies
- [ ] OCR for scanned PDFs

## 📝 License

This project is private and not licensed for public use.

## 🤝 Contributing

This is a private project. Contact the repository owner for contribution guidelines.

## 📧 Support

For issues or questions, please contact the project maintainer.

---

**Built with:**
- React + Vite
- Flask + Python
- OpenAI GPT-4 & Embeddings
- Weaviate Vector Database
- PyMuPDF & pdfplumber
- TipTap Editor
- ReactMarkdown

**Last Updated:** November 24, 2025
