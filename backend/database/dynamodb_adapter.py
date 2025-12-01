"""DynamoDB adapter for document tracking (replaces documents.db)."""

import boto3
import uuid
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional
from botocore.exceptions import ClientError


class DynamoDBDocumentsAdapter:
    def __init__(self):
        from config import Config

        self.dynamodb = boto3.resource("dynamodb", region_name=Config.AWS_REGION)
        self.documents_table = self.dynamodb.Table(Config.DOCUMENTS_TABLE)
        self.versions_table = self.dynamodb.Table(Config.DOCUMENT_VERSIONS_TABLE)

    def insert_document(self, doc_data: Dict, version: int = 1) -> str:
        """Insert a new document record."""
        ph_tz = timezone(timedelta(hours=8))
        upload_date = datetime.now(ph_tz).isoformat()

        item = {
            "doc_id": doc_data.get("doc_id"),
            "file_name": doc_data.get("file_name"),
            "upload_date": upload_date,
            "file_size_bytes": doc_data.get("file_size_bytes"),
            "chunks": doc_data.get("chunks"),
            "uploaded_by": doc_data.get("uploaded_by"),
            "content_hash": doc_data.get("content_hash"),
            "page_count": doc_data.get("page_count"),
            "weaviate_doc_id": doc_data.get("weaviate_doc_id"),
            "metadata": doc_data.get("metadata", {}),
            "current_version": version,
        }

        try:
            self.documents_table.put_item(Item=item)
            print(f"[DynamoDB] Inserted document: {doc_data.get('doc_id')}")
            return doc_data.get("doc_id")
        except ClientError as e:
            print(f"[DynamoDB] Insert failed: {e}")
            raise

    def get_document(self, doc_id: str) -> Optional[Dict]:
        """Get a document by ID."""
        try:
            response = self.documents_table.get_item(Key={"doc_id": doc_id})
            return response.get("Item")
        except ClientError as e:
            print(f"[DynamoDB] Get document failed: {e}")
            return None

    def get_document_by_filename(self, file_name: str) -> Optional[Dict]:
        """Get a document by filename using GSI."""
        try:
            response = self.documents_table.query(
                IndexName="filename-index",
                KeyConditionExpression="file_name = :fn",
                ExpressionAttributeValues={":fn": file_name},
                Limit=1,
            )
            items = response.get("Items", [])
            return items[0] if items else None
        except ClientError as e:
            print(f"[DynamoDB] Query by filename failed: {e}")
            return None

    def check_duplicate_by_filename(self, filename: str) -> Optional[Dict]:
        """Check if document with this filename exists."""
        return self.get_document_by_filename(filename)

    def check_duplicate_by_hash(self, content_hash: str) -> Optional[Dict]:
        """Check if document with this content hash exists."""
        if not content_hash or content_hash.startswith("temp-"):
            return None

        try:
            response = self.documents_table.query(
                IndexName="content-hash-index",
                KeyConditionExpression="content_hash = :ch",
                ExpressionAttributeValues={":ch": content_hash},
                Limit=1,
            )
            items = response.get("Items", [])
            return items[0] if items else None
        except ClientError as e:
            print(f"[DynamoDB] Query by hash failed: {e}")
            return None

    def check_duplicates(
        self, filename: str, content_hash: Optional[str] = None
    ) -> Dict:
        """Check for duplicates (filename or content)."""
        existing_by_filename = self.check_duplicate_by_filename(filename)
        existing_by_hash = (
            self.check_duplicate_by_hash(content_hash) if content_hash else None
        )

        is_duplicate = bool(existing_by_filename or existing_by_hash)
        duplicate_type = None
        existing_doc = None
        message = None

        if existing_by_filename and existing_by_hash:
            duplicate_type = "both"
            existing_doc = existing_by_filename
            if existing_by_filename["doc_id"] == existing_by_hash["doc_id"]:
                message = f"This exact file '{filename}' already exists in the knowledge base."
            else:
                message = f"Filename '{filename}' already exists, and content matches another file '{existing_by_hash['file_name']}'."
        elif existing_by_filename:
            duplicate_type = "filename"
            existing_doc = existing_by_filename
            message = f"A file named '{filename}' already exists in the knowledge base."
        elif existing_by_hash:
            duplicate_type = "content"
            existing_doc = existing_by_hash
            message = f"This file content already exists as '{existing_by_hash['file_name']}' in the knowledge base."

        return {
            "is_duplicate": is_duplicate,
            "duplicate_type": duplicate_type,
            "existing_doc": existing_doc,
            "message": message,
        }

    def delete_document(self, doc_id: str) -> bool:
        """Delete a document record."""
        try:
            self.documents_table.delete_item(Key={"doc_id": doc_id})
            print(f"[DynamoDB] Deleted document: {doc_id}")
            return True
        except ClientError as e:
            print(f"[DynamoDB] Delete failed: {e}")
            return False

    def list_documents(
        self,
        limit: int = 100,
        offset: int = 0,
        uploaded_by: Optional[str] = None,
        order_by: str = "upload_date",
        order_dir: str = "DESC",
    ) -> List[Dict]:
        """List documents with pagination."""
        try:
            # DynamoDB doesn't support offset, so we'll scan and skip
            params = {"Limit": limit + offset}

            if uploaded_by:
                params["FilterExpression"] = "uploaded_by = :ub"
                params["ExpressionAttributeValues"] = {":ub": uploaded_by}

            response = self.documents_table.scan(**params)
            items = response.get("Items", [])

            # Sort and paginate in memory (for small datasets)
            reverse = order_dir.upper() == "DESC"
            items.sort(key=lambda x: x.get(order_by, ""), reverse=reverse)

            return items[offset : offset + limit]

        except ClientError as e:
            print(f"[DynamoDB] List documents failed: {e}")
            return []

    def get_document_count(self, uploaded_by: Optional[str] = None) -> int:
        """Get total document count."""
        try:
            if uploaded_by:
                # Use query on GSI if available, otherwise scan
                response = self.documents_table.scan(
                    Select="COUNT",
                    FilterExpression="uploaded_by = :ub",
                    ExpressionAttributeValues={":ub": uploaded_by},
                )
            else:
                response = self.documents_table.scan(Select="COUNT")

            return response.get("Count", 0)
        except ClientError as e:
            print(f"[DynamoDB] Count failed: {e}")
            return 0

    def archive_document_version(
        self, doc_id: str, replaced_by: str = None
    ) -> Optional[str]:
        """Archive document to version history."""
        doc = self.get_document(doc_id)
        if not doc:
            return None

        ph_tz = timezone(timedelta(hours=8))
        archived_date = datetime.now(ph_tz).isoformat()
        version_id = str(uuid.uuid4())

        version_item = {
            "version_id": version_id,
            "doc_id": doc["doc_id"],
            "file_name": doc["file_name"],
            "version_number": doc.get("current_version", 1),
            "upload_date": doc["upload_date"],
            "archived_date": archived_date,
            "file_size_bytes": doc.get("file_size_bytes"),
            "chunks": doc.get("chunks"),
            "uploaded_by": doc.get("uploaded_by"),
            "content_hash": doc.get("content_hash"),
            "page_count": doc.get("page_count"),
            "replaced_by": replaced_by,
        }

        try:
            self.versions_table.put_item(Item=version_item)
            print(f"[DynamoDB] Archived version: {version_id}")
            return version_id
        except ClientError as e:
            print(f"[DynamoDB] Archive failed: {e}")
            return None


# Singleton
_documents_adapter_instance = None


def get_documents_adapter() -> DynamoDBDocumentsAdapter:
    """Get or create DynamoDBDocumentsAdapter instance."""
    global _documents_adapter_instance
    if _documents_adapter_instance is None:
        _documents_adapter_instance = DynamoDBDocumentsAdapter()
    return _documents_adapter_instance
