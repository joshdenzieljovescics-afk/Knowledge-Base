"""
DynamoDB adapter for AWS Lambda deployment.
Replaces SQLite database operations with DynamoDB.
"""
import boto3
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid
import os
from decimal import Decimal


class DynamoDBAdapter:
    """
    Adapter for DynamoDB operations.

    This class provides a similar interface to the SQLite operations
    but uses DynamoDB tables instead of local database files.

    Tables:
    - knowledge-base-documents: Document metadata and upload history
    - knowledge-base-chat-history: Chat conversation history
    """

    def __init__(self):
        """Initialize DynamoDB client and table references"""
        self.dynamodb = boto3.resource('dynamodb')

        # Get table names from environment or use defaults
        self.documents_table_name = os.environ.get(
            'DOCUMENTS_TABLE',
            'knowledge-base-documents'
        )
        self.chat_table_name = os.environ.get(
            'CHAT_TABLE',
            'knowledge-base-chat-history'
        )

        self.documents_table = self.dynamodb.Table(self.documents_table_name)
        self.chat_table = self.dynamodb.Table(self.chat_table_name)

    # ==================== Document Operations ====================

    def save_document(self, doc_data: Dict[str, Any]) -> str:
        """
        Save document metadata to DynamoDB.

        Args:
            doc_data: Dictionary containing document metadata
                - filename: Original filename
                - file_hash: SHA256 hash
                - file_size: Size in bytes
                - uploaded_by: User ID (optional)
                - chunk_count: Number of chunks
                - metadata: Additional metadata

        Returns:
            str: Generated document ID (UUID)
        """
        doc_id = str(uuid.uuid4())

        item = {
            'document_id': doc_id,
            'file_hash': doc_data.get('file_hash', ''),
            'filename': doc_data.get('filename', ''),
            'original_filename': doc_data.get('original_filename', doc_data.get('filename', '')),
            'file_size': Decimal(str(doc_data.get('file_size', 0))),
            'upload_date': datetime.utcnow().isoformat(),
            'uploaded_by': doc_data.get('uploaded_by', 'anonymous'),
            'chunk_count': Decimal(str(doc_data.get('chunk_count', 0))),
            'uploaded_to_kb': doc_data.get('uploaded_to_kb', False),
            's3_key': doc_data.get('s3_key', ''),
            'metadata': doc_data.get('metadata', {})
        }

        self.documents_table.put_item(Item=item)
        return doc_id

    def get_document_by_id(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """
        Get document by ID.

        Args:
            doc_id: Document UUID

        Returns:
            Document data or None if not found
        """
        try:
            response = self.documents_table.get_item(Key={'document_id': doc_id})
            return response.get('Item')
        except Exception as e:
            print(f"Error getting document {doc_id}: {e}")
            return None

    def get_document_by_hash(self, file_hash: str) -> Optional[Dict[str, Any]]:
        """
        Check if document exists by SHA256 hash.

        This is used for duplicate detection.

        Args:
            file_hash: SHA256 hash of the file

        Returns:
            Document data or None if not found
        """
        try:
            response = self.documents_table.query(
                IndexName='FileHashIndex',
                KeyConditionExpression='file_hash = :hash',
                ExpressionAttributeValues={':hash': file_hash}
            )
            items = response.get('Items', [])
            return items[0] if items else None
        except Exception as e:
            print(f"Error querying by hash: {e}")
            return None

    def list_documents(self, limit: int = 100, uploaded_by: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List all documents, optionally filtered by user.

        Args:
            limit: Maximum number of documents to return
            uploaded_by: Filter by user ID (optional)

        Returns:
            List of document dictionaries
        """
        try:
            if uploaded_by:
                response = self.documents_table.scan(
                    FilterExpression='uploaded_by = :user',
                    ExpressionAttributeValues={':user': uploaded_by},
                    Limit=limit
                )
            else:
                response = self.documents_table.scan(Limit=limit)

            items = response.get('Items', [])

            # Convert Decimal to int/float for JSON serialization
            return [self._convert_decimals(item) for item in items]
        except Exception as e:
            print(f"Error listing documents: {e}")
            return []

    def update_document_kb_status(self, doc_id: str, uploaded: bool = True) -> bool:
        """
        Update the uploaded_to_kb status for a document.

        Args:
            doc_id: Document UUID
            uploaded: Whether document is uploaded to knowledge base

        Returns:
            True if successful, False otherwise
        """
        try:
            self.documents_table.update_item(
                Key={'document_id': doc_id},
                UpdateExpression='SET uploaded_to_kb = :status',
                ExpressionAttributeValues={':status': uploaded}
            )
            return True
        except Exception as e:
            print(f"Error updating KB status: {e}")
            return False

    def delete_document(self, doc_id: str) -> bool:
        """
        Delete document by ID.

        Args:
            doc_id: Document UUID

        Returns:
            True if successful, False otherwise
        """
        try:
            self.documents_table.delete_item(Key={'document_id': doc_id})
            return True
        except Exception as e:
            print(f"Error deleting document {doc_id}: {e}")
            return False

    # ==================== Chat Operations ====================

    def save_chat_message(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Save a chat message to DynamoDB.

        Args:
            session_id: Chat session ID
            role: Message role (user/assistant)
            content: Message content
            metadata: Additional metadata (sources, token usage, etc.)

        Returns:
            True if successful, False otherwise
        """
        try:
            timestamp = int(datetime.utcnow().timestamp() * 1000)  # Milliseconds

            item = {
                'session_id': session_id,
                'timestamp': timestamp,
                'role': role,
                'content': content,
                'metadata': metadata or {},
                'ttl': int(datetime.utcnow().timestamp()) + (30 * 24 * 60 * 60)  # 30 days
            }

            self.chat_table.put_item(Item=item)
            return True
        except Exception as e:
            print(f"Error saving chat message: {e}")
            return False

    def get_chat_history(
        self,
        session_id: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get chat history for a session.

        Args:
            session_id: Chat session ID
            limit: Maximum number of messages to return

        Returns:
            List of chat messages, ordered by timestamp
        """
        try:
            response = self.chat_table.query(
                KeyConditionExpression='session_id = :sid',
                ExpressionAttributeValues={':sid': session_id},
                ScanIndexForward=True,  # Ascending order (oldest first)
                Limit=limit
            )

            items = response.get('Items', [])
            return [self._convert_decimals(item) for item in items]
        except Exception as e:
            print(f"Error getting chat history: {e}")
            return []

    def delete_chat_session(self, session_id: str) -> bool:
        """
        Delete all messages for a chat session.

        Args:
            session_id: Chat session ID

        Returns:
            True if successful, False otherwise
        """
        try:
            # Query all items for this session
            response = self.chat_table.query(
                KeyConditionExpression='session_id = :sid',
                ExpressionAttributeValues={':sid': session_id}
            )

            # Batch delete
            with self.chat_table.batch_writer() as batch:
                for item in response.get('Items', []):
                    batch.delete_item(
                        Key={
                            'session_id': item['session_id'],
                            'timestamp': item['timestamp']
                        }
                    )

            return True
        except Exception as e:
            print(f"Error deleting chat session: {e}")
            return False

    # ==================== Utility Methods ====================

    def _convert_decimals(self, obj: Any) -> Any:
        """
        Convert DynamoDB Decimal types to int/float for JSON serialization.

        Args:
            obj: Object to convert (can be dict, list, or Decimal)

        Returns:
            Converted object
        """
        if isinstance(obj, Decimal):
            # Convert to int if it's a whole number, otherwise float
            return int(obj) if obj % 1 == 0 else float(obj)
        elif isinstance(obj, dict):
            return {k: self._convert_decimals(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._convert_decimals(item) for item in obj]
        return obj

    def health_check(self) -> Dict[str, bool]:
        """
        Check DynamoDB connection health.

        Returns:
            Dictionary with connection status for each table
        """
        try:
            # Try to describe tables
            docs_status = self.documents_table.table_status == 'ACTIVE'
            chat_status = self.chat_table.table_status == 'ACTIVE'

            return {
                'documents_table': docs_status,
                'chat_table': chat_status,
                'overall': docs_status and chat_status
            }
        except Exception as e:
            print(f"Health check failed: {e}")
            return {
                'documents_table': False,
                'chat_table': False,
                'overall': False
            }


# Singleton instance
_db_adapter = None

def get_dynamodb_adapter() -> DynamoDBAdapter:
    """
    Get or create DynamoDB adapter singleton.

    Returns:
        DynamoDBAdapter instance
    """
    global _db_adapter
    if _db_adapter is None:
        _db_adapter = DynamoDBAdapter()
    return _db_adapter
