# database/dynamodb_chat.py (COMPLETE VERSION)
"""DynamoDB adapter for chat sessions and messages (replaces chat_sessions.db)."""
import boto3
import uuid
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional, Tuple
from botocore.exceptions import ClientError


class DynamoDBChatAdapter:
    def __init__(self):
        from config import Config

        self.dynamodb = boto3.resource("dynamodb", region_name=Config.AWS_REGION)
        self.sessions_table = self.dynamodb.Table(Config.CHAT_SESSIONS_TABLE)
        self.messages_table = self.dynamodb.Table(Config.CHAT_MESSAGES_TABLE)

    # ═══════════════════════════════════════════════════════════════
    # SESSION OPERATIONS
    # ═══════════════════════════════════════════════════════════════

    def create_session(self, user_id: str, title: str = None) -> Dict:
        """Create new chat session."""
        session_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()

        item = {
            "session_id": session_id,
            "user_id": user_id,
            "title": title or "New Chat",
            "created_at": now,
            "updated_at": now,
            "message_count": 0,
            "total_tokens_used": 0,
            "total_cost_usd": 0.0,
            "metadata": {},
        }

        try:
            self.sessions_table.put_item(Item=item)
            print(f"[DynamoDB] Created session: {session_id}")
            return {
                "session_id": session_id,
                "user_id": user_id,
                "title": title or "New Chat",
                "created_at": now,
                "message_count": 0,
            }
        except ClientError as e:
            print(f"[DynamoDB] Create session failed: {e}")
            raise

    def get_session(self, session_id: str) -> Optional[Dict]:
        """Get session by ID."""
        try:
            response = self.sessions_table.get_item(Key={"session_id": session_id})
            item = response.get("Item")
            if item:
                item["title"] = item.get("title") or "New Chat"
            return item
        except ClientError as e:
            print(f"[DynamoDB] Get session failed: {e}")
            return None

    def update_session_title(self, session_id: str, title: str) -> bool:
        """Update session title."""
        try:
            self.sessions_table.update_item(
                Key={"session_id": session_id},
                UpdateExpression="SET title = :title, updated_at = :now",
                ExpressionAttributeValues={
                    ":title": title,
                    ":now": datetime.utcnow().isoformat(),
                },
            )
            return True
        except ClientError as e:
            print(f"[DynamoDB] Update title failed: {e}")
            return False

    def delete_session(self, session_id: str) -> bool:
        """Delete a session and all its messages."""
        try:
            # Delete all messages first
            response = self.messages_table.query(
                IndexName="session-timestamp-index",
                KeyConditionExpression="session_id = :sid",
                ExpressionAttributeValues={":sid": session_id},
            )

            with self.messages_table.batch_writer() as batch:
                for item in response.get("Items", []):
                    batch.delete_item(Key={"message_id": item["message_id"]})

            # Delete session
            self.sessions_table.delete_item(Key={"session_id": session_id})
            print(f"[DynamoDB] Deleted session: {session_id}")
            return True

        except ClientError as e:
            print(f"[DynamoDB] Delete session failed: {e}")
            return False

    def get_user_sessions(
        self, user_id: str, limit: int = 20, offset: int = 0
    ) -> Tuple[List[Dict], int]:
        """Get all sessions for a user with pagination."""
        try:
            # Query using GSI
            response = self.sessions_table.query(
                IndexName="user-updated-index",
                KeyConditionExpression="user_id = :uid",
                ExpressionAttributeValues={":uid": user_id},
                ScanIndexForward=False,  # DESC order
                Limit=limit + offset,
            )

            items = response.get("Items", [])
            total = len(items)

            # Manual offset (DynamoDB doesn't support OFFSET)
            sessions = items[offset : offset + limit]

            # Format sessions
            formatted = []
            for item in sessions:
                formatted.append(
                    {
                        "session_id": item["session_id"],
                        "user_id": item["user_id"],
                        "title": item.get("title") or "New Chat",
                        "created_at": item["created_at"],
                        "updated_at": item["updated_at"],
                        "message_count": item.get("message_count", 0),
                        "metadata": item.get("metadata", {}),
                    }
                )

            return formatted, total

        except ClientError as e:
            print(f"[DynamoDB] Get user sessions failed: {e}")
            return [], 0

    def update_session_metadata(self, session_id: str, metadata: Dict) -> bool:
        """Update session metadata."""
        try:
            self.sessions_table.update_item(
                Key={"session_id": session_id},
                UpdateExpression="SET metadata = :meta, updated_at = :now",
                ExpressionAttributeValues={
                    ":meta": metadata,
                    ":now": datetime.utcnow().isoformat(),
                },
            )
            return True
        except ClientError as e:
            print(f"[DynamoDB] Update metadata failed: {e}")
            return False

    # ═══════════════════════════════════════════════════════════════
    # MESSAGE OPERATIONS
    # ═══════════════════════════════════════════════════════════════

    def save_message(
        self,
        session_id: str,
        role: str,
        content: str,
        sources: Optional[List[Dict]] = None,
        metadata: Optional[Dict] = None,
    ) -> Dict:
        """Save a message to the session."""
        message_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()

        item = {
            "message_id": message_id,
            "session_id": session_id,
            "role": role,
            "content": content,
            "timestamp": now,
            "sources": sources or [],
            "metadata": metadata or {},
        }

        try:
            # Save message
            self.messages_table.put_item(Item=item)

            # Update session
            update_expr = "SET updated_at = :now, message_count = message_count + :inc"
            expr_values = {":now": now, ":inc": 1}

            # Update tokens if this is an assistant message
            if role == "assistant" and metadata and "tokens_used" in metadata:
                tokens = metadata["tokens_used"]
                cost = (tokens / 1_000_000) * 10  # $10/1M tokens estimate

                update_expr += ", total_tokens_used = total_tokens_used + :tokens, total_cost_usd = total_cost_usd + :cost, last_token_update = :now"
                expr_values[":tokens"] = tokens
                expr_values[":cost"] = cost

            self.sessions_table.update_item(
                Key={"session_id": session_id},
                UpdateExpression=update_expr,
                ExpressionAttributeValues=expr_values,
            )

            # Auto-generate title from first user message
            if role == "user":
                session = self.get_session(session_id)
                if session and session.get("message_count", 0) == 1:
                    current_title = session.get("title", "New Chat")
                    if not current_title or current_title == "New Chat":
                        title = content[:50] + "..." if len(content) > 50 else content
                        self.update_session_title(session_id, title)

            return {
                "message_id": message_id,
                "session_id": session_id,
                "role": role,
                "content": content,
                "sources": sources or [],
                "metadata": metadata or {},
                "timestamp": now,
            }

        except ClientError as e:
            print(f"[DynamoDB] Save message failed: {e}")
            raise

    def get_session_messages(
        self, session_id: str, limit: Optional[int] = None, offset: int = 0
    ) -> List[Dict]:
        """Get all messages for a session."""
        try:
            params = {
                "IndexName": "session-timestamp-index",
                "KeyConditionExpression": "session_id = :sid",
                "ExpressionAttributeValues": {":sid": session_id},
                "ScanIndexForward": True,  # ASC order
            }

            if limit:
                params["Limit"] = limit + offset

            response = self.messages_table.query(**params)
            items = response.get("Items", [])

            # Apply offset
            messages = items[offset : offset + limit] if limit else items[offset:]

            return messages

        except ClientError as e:
            print(f"[DynamoDB] Get messages failed: {e}")
            return []

    # ═══════════════════════════════════════════════════════════════
    # TOKEN TRACKING
    # ═══════════════════════════════════════════════════════════════

    def get_session_token_usage(self, session_id: str) -> Optional[Dict]:
        """Get token usage statistics for a session."""
        try:
            response = self.sessions_table.get_item(
                Key={"session_id": session_id},
                ProjectionExpression="total_tokens_used, total_cost_usd, last_token_update",
            )

            item = response.get("Item")
            if not item:
                return None

            return {
                "total_tokens": item.get("total_tokens_used", 0),
                "total_cost_usd": float(item.get("total_cost_usd", 0.0)),
                "last_update": item.get("last_token_update"),
            }

        except ClientError as e:
            print(f"[DynamoDB] Get token usage failed: {e}")
            return None

    def get_user_total_tokens(self, user_id: str) -> Dict:
        """Get total token usage across all sessions for a user."""
        try:
            response = self.sessions_table.query(
                IndexName="user-updated-index",
                KeyConditionExpression="user_id = :uid",
                ExpressionAttributeValues={":uid": user_id},
                ProjectionExpression="total_tokens_used, total_cost_usd",
            )

            items = response.get("Items", [])

            total_tokens = sum(item.get("total_tokens_used", 0) for item in items)
            total_cost = sum(float(item.get("total_cost_usd", 0.0)) for item in items)

            return {
                "total_tokens": total_tokens,
                "total_cost_usd": total_cost,
                "session_count": len(items),
            }

        except ClientError as e:
            print(f"[DynamoDB] Get user tokens failed: {e}")
            return {"total_tokens": 0, "total_cost_usd": 0.0, "session_count": 0}


# Singleton
_chat_adapter_instance = None


def get_chat_adapter() -> DynamoDBChatAdapter:
    """Get or create DynamoDBChatAdapter instance."""
    global _chat_adapter_instance
    if _chat_adapter_instance is None:
        _chat_adapter_instance = DynamoDBChatAdapter()
    return _chat_adapter_instance
