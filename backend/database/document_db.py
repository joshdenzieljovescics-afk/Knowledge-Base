# database/document_db.py
import sqlite3
import json
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional

class DocumentDatabase:
    def __init__(self, db_path: str = "database/documents.db"):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """Initialize document tracking database tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Documents table - tracks all uploaded files
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                doc_id TEXT PRIMARY KEY,
                file_name TEXT NOT NULL,
                upload_date TEXT NOT NULL,
                file_size_bytes INTEGER NOT NULL,
                chunks INTEGER NOT NULL,
                uploaded_by TEXT,
                content_hash TEXT UNIQUE NOT NULL,
                page_count INTEGER,
                weaviate_doc_id TEXT,
                metadata TEXT
            )
        """)
        
        # Indexes for fast lookups
        cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_file_name ON documents(file_name)")
        cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_content_hash ON documents(content_hash)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_uploaded_by ON documents(uploaded_by)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_upload_date ON documents(upload_date)")
        
        conn.commit()
        conn.close()
    
    def check_duplicate_by_filename(self, filename: str) -> Optional[Dict]:
        """
        Check if a document with this filename already exists.
        
        Args:
            filename: Name of the file to check
            
        Returns:
            Document info dict if exists, None otherwise
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT doc_id, file_name, upload_date, file_size_bytes, 
                   chunks, uploaded_by, content_hash
            FROM documents 
            WHERE file_name = ?
        """, (filename,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                "doc_id": row["doc_id"],
                "file_name": row["file_name"],
                "upload_date": row["upload_date"],
                "file_size_bytes": row["file_size_bytes"],
                "chunks": row["chunks"],
                "uploaded_by": row["uploaded_by"],
                "content_hash": row["content_hash"]
            }
        return None
    
    def check_duplicate_by_hash(self, content_hash: str) -> Optional[Dict]:
        """
        Check if a document with this content hash already exists.
        This detects renamed duplicates.
        
        Args:
            content_hash: SHA256 hash of file content
            
        Returns:
            Document info dict if exists, None otherwise
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT doc_id, file_name, upload_date, file_size_bytes, 
                   chunks, uploaded_by, content_hash
            FROM documents 
            WHERE content_hash = ?
        """, (content_hash,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                "doc_id": row["doc_id"],
                "file_name": row["file_name"],
                "upload_date": row["upload_date"],
                "file_size_bytes": row["file_size_bytes"],
                "chunks": row["chunks"],
                "uploaded_by": row["uploaded_by"],
                "content_hash": row["content_hash"]
            }
        return None
    
    def insert_document(self, doc_data: Dict) -> str:
        """
        Insert a new document record.
        
        Args:
            doc_data: Dictionary containing document information
            Required fields: doc_id, file_name, file_size_bytes, chunks, content_hash
            Optional fields: uploaded_by, page_count, weaviate_doc_id, metadata
            
        Returns:
            doc_id of inserted document
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Use Philippine time (UTC+8)
        ph_tz = timezone(timedelta(hours=8))
        upload_date = datetime.now(ph_tz).isoformat()
        
        cursor.execute("""
            INSERT INTO documents 
            (doc_id, file_name, upload_date, file_size_bytes, chunks, 
             uploaded_by, content_hash, page_count, weaviate_doc_id, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            doc_data.get("doc_id"),
            doc_data.get("file_name"),
            upload_date,
            doc_data.get("file_size_bytes"),
            doc_data.get("chunks"),
            doc_data.get("uploaded_by"),
            doc_data.get("content_hash"),
            doc_data.get("page_count"),
            doc_data.get("weaviate_doc_id"),
            json.dumps(doc_data.get("metadata", {}))
        ))
        
        conn.commit()
        conn.close()
        
        return doc_data.get("doc_id")
    
    def update_document(self, doc_id: str, updates: Dict) -> bool:
        """
        Update an existing document record.
        
        Args:
            doc_id: Document ID to update
            updates: Dictionary of fields to update
            
        Returns:
            True if updated successfully
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Build dynamic UPDATE query
        set_clauses = []
        values = []
        
        allowed_fields = [
            "file_name", "file_size_bytes", "chunks", "uploaded_by",
            "content_hash", "page_count", "weaviate_doc_id"
        ]
        
        for field in allowed_fields:
            if field in updates:
                set_clauses.append(f"{field} = ?")
                values.append(updates[field])
        
        if "metadata" in updates:
            set_clauses.append("metadata = ?")
            values.append(json.dumps(updates["metadata"]))
        
        if not set_clauses:
            conn.close()
            return False
        
        values.append(doc_id)
        query = f"UPDATE documents SET {', '.join(set_clauses)} WHERE doc_id = ?"
        
        cursor.execute(query, values)
        conn.commit()
        affected = cursor.rowcount
        conn.close()
        
        return affected > 0
    
    def delete_document(self, doc_id: str) -> bool:
        """
        Delete a document record.
        
        Args:
            doc_id: Document ID to delete
            
        Returns:
            True if deleted successfully
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM documents WHERE doc_id = ?", (doc_id,))
        conn.commit()
        affected = cursor.rowcount
        conn.close()
        
        return affected > 0
    
    def get_document(self, doc_id: str) -> Optional[Dict]:
        """
        Get a document by ID.
        
        Args:
            doc_id: Document ID
            
        Returns:
            Document info dict if found, None otherwise
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT doc_id, file_name, upload_date, file_size_bytes, 
                   chunks, uploaded_by, content_hash, page_count,
                   weaviate_doc_id, metadata
            FROM documents 
            WHERE doc_id = ?
        """, (doc_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                "doc_id": row["doc_id"],
                "file_name": row["file_name"],
                "upload_date": row["upload_date"],
                "file_size_bytes": row["file_size_bytes"],
                "chunks": row["chunks"],
                "uploaded_by": row["uploaded_by"],
                "content_hash": row["content_hash"],
                "page_count": row["page_count"],
                "weaviate_doc_id": row["weaviate_doc_id"],
                "metadata": json.loads(row["metadata"]) if row["metadata"] else {}
            }
        return None
    
    def list_documents(
        self, 
        limit: int = 100, 
        offset: int = 0,
        uploaded_by: Optional[str] = None,
        order_by: str = "upload_date",
        order_dir: str = "DESC"
    ) -> List[Dict]:
        """
        List all documents with pagination and filtering.
        
        Args:
            limit: Maximum number of results
            offset: Number of results to skip
            uploaded_by: Filter by user (optional)
            order_by: Field to sort by (default: upload_date)
            order_dir: Sort direction (ASC or DESC)
            
        Returns:
            List of document info dicts
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Build query with optional filter
        query = """
            SELECT doc_id, file_name, upload_date, file_size_bytes, 
                   chunks, uploaded_by, content_hash, page_count
            FROM documents
        """
        params = []
        
        if uploaded_by:
            query += " WHERE uploaded_by = ?"
            params.append(uploaded_by)
        
        # Add ordering
        allowed_order_fields = ["upload_date", "file_name", "file_size_bytes", "chunks"]
        if order_by not in allowed_order_fields:
            order_by = "upload_date"
        
        if order_dir.upper() not in ["ASC", "DESC"]:
            order_dir = "DESC"
        
        query += f" ORDER BY {order_by} {order_dir} LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        return [
            {
                "doc_id": row["doc_id"],
                "file_name": row["file_name"],
                "upload_date": row["upload_date"],
                "file_size_bytes": row["file_size_bytes"],
                "chunks": row["chunks"],
                "uploaded_by": row["uploaded_by"],
                "content_hash": row["content_hash"],
                "page_count": row["page_count"]
            }
            for row in rows
        ]
    
    def get_document_count(self, uploaded_by: Optional[str] = None) -> int:
        """
        Get total count of documents.
        
        Args:
            uploaded_by: Filter by user (optional)
            
        Returns:
            Total number of documents
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if uploaded_by:
            cursor.execute("SELECT COUNT(*) FROM documents WHERE uploaded_by = ?", (uploaded_by,))
        else:
            cursor.execute("SELECT COUNT(*) FROM documents")
        
        count = cursor.fetchone()[0]
        conn.close()
        
        return count
