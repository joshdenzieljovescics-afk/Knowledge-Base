# services/chat_service.py
import os
import openai
from typing import List, Dict, Optional
from dotenv import load_dotenv
from database.chat_db import ChatDatabase
from services.weaviate_search_service import WeaviateSearchService
from services.query_processor import QueryProcessor
from services.context_manager import ContextManager

# Ensure environment variables are loaded
load_dotenv()

class ChatService:
    def __init__(self):
        self.chat_db = ChatDatabase()
        self.search_service = WeaviateSearchService()
        self.query_processor = QueryProcessor()
        self.context_manager = ContextManager()
        
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is not set")
        self.openai_client = openai.OpenAI(api_key=api_key)
    
    def process_message(
        self,
        session_id: str,
        user_message: str,
        options: Optional[Dict] = None
    ) -> Dict:
        """
        Main chat processing pipeline
        
        Args:
            session_id: Chat session ID
            user_message: User's message
            options: Optional settings (max_sources, include_context, document_filter)
        
        Returns:
            Dict with assistant message details
        """
        options = options or {}
        max_sources = options.get('max_sources', 5)
        include_context = options.get('include_context', True)
        document_filter = options.get('document_filter', [])
        
        print(f"[ChatService] Processing message: {user_message}")
        
        # 1. Save user message
        user_msg = self.chat_db.save_message(
            session_id=session_id,
            role="user",
            content=user_message
        )
        print(f"[ChatService] Saved user message: {user_msg['message_id']}")
        
        # 2. Get conversation context
        context = []
        if include_context:
            all_messages = self.chat_db.get_session_messages(session_id)
            # Exclude the just-saved user message for context
            context = self.context_manager.get_recent_context(
                messages=all_messages[:-1],  # All except last (current message)
                max_messages=10,
                max_tokens=2000
            )
            print(f"[ChatService] Retrieved {len(context)} context messages")
        
        # 3. Process query (expand, resolve references)
        processed_query = self.query_processor.enhance_query(
            query=user_message,
            context=context
        )
        print(f"[ChatService] Processed query: {processed_query['search_query']}")
        
        # 4. Search Weaviate knowledge base
        search_filters = None
        if document_filter:
            search_filters = {'document_ids': document_filter}
        
        search_results = self.search_service.hybrid_search(
            query=processed_query['search_query'],
            limit=max_sources * 2,  # Get more, then rerank
            filters=search_filters
        )
        print(f"[ChatService] Found {len(search_results)} search results")
        
        # 5. Rerank results
        top_chunks = self.query_processor.rerank_results(
            query=user_message,
            results=search_results,
            top_k=max_sources
        )
        print(f"[ChatService] Using top {len(top_chunks)} chunks")
        
        # 6. Generate response with OpenAI
        assistant_response = self._generate_response(
            user_message=user_message,
            context=context,
            knowledge_chunks=top_chunks
        )
        print(f"[ChatService] Generated response ({assistant_response['tokens_used']} tokens)")
        
        # 7. Save assistant message with sources
        sources = self.context_manager.format_sources(top_chunks)
        
        assistant_msg = self.chat_db.save_message(
            session_id=session_id,
            role="assistant",
            content=assistant_response['content'],
            sources=sources,
            metadata={
                'tokens_used': assistant_response['tokens_used'],
                'chunks_retrieved': len(search_results),
                'chunks_used': len(top_chunks),
                'search_query': processed_query['search_query']
            }
        )
        print(f"[ChatService] Saved assistant message: {assistant_msg['message_id']}")
        
        # 8. Update session metadata
        session = self.chat_db.get_session(session_id)
        if session:
            metadata = session.get('metadata', {})
            docs_referenced = metadata.get('documents_referenced', [])
            
            # Add new document IDs
            for chunk in top_chunks:
                doc_id = chunk.get('document_id')
                if doc_id and doc_id not in docs_referenced:
                    docs_referenced.append(doc_id)
            
            metadata['documents_referenced'] = docs_referenced
            metadata['total_chunks_used'] = metadata.get('total_chunks_used', 0) + len(top_chunks)
            
            self.chat_db.update_session_metadata(session_id, metadata)
        
        return assistant_msg
    
    def _generate_response(
        self,
        user_message: str,
        context: List[Dict],
        knowledge_chunks: List[Dict]
    ) -> Dict:
        """
        Generate response using OpenAI with KB context
        """
        # Build context from knowledge base chunks
        kb_context = self.context_manager.build_kb_context(knowledge_chunks)
        
        # Build messages for OpenAI
        messages = [
            {
                "role": "system",
                "content": f"""You are a helpful assistant that answers questions based on uploaded documents in a knowledge base.

IMPORTANT RULES:
1. Base your answers ONLY on the provided document excerpts below
2. Always cite sources using [Source: filename, Page X] format in your response
3. If the information needed to answer the question is not in the provided excerpts, say "I don't have enough information in the uploaded documents to answer that question fully."
4. Be conversational but accurate
5. Use direct quotes when appropriate
6. If asked about something not in the documents, politely say so and suggest what topics the documents do cover

Available Document Context:
{kb_context}
"""
            }
        ]
        
        # Add conversation history
        for msg in context:
            messages.append({
                "role": msg['role'],
                "content": msg['content']
            })
        
        # Add current user message
        messages.append({
            "role": "user",
            "content": user_message
        })
        
        try:
            # Call OpenAI
            response = self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                temperature=0.7,
                max_tokens=1000
            )
            
            return {
                'content': response.choices[0].message.content,
                'tokens_used': response.usage.total_tokens
            }
        except Exception as e:
            print(f"[ChatService] Error generating response: {e}")
            import traceback
            traceback.print_exc()
            
            # Fallback response
            return {
                'content': "I apologize, but I encountered an error while processing your question. Please try again.",
                'tokens_used': 0
            }
    
    def create_session(self, user_id: str, title: str = None) -> Dict:
        """Create a new chat session"""
        return self.chat_db.create_session(user_id, title)
    
    def get_session_history(self, session_id: str, limit: Optional[int] = None) -> Dict:
        """Get session with message history"""
        session = self.chat_db.get_session(session_id)
        if not session:
            return None
        
        messages = self.chat_db.get_session_messages(session_id, limit=limit)
        
        return {
            'session': session,
            'messages': messages
        }
    
    def get_user_sessions(self, user_id: str, limit: int = 20, offset: int = 0) -> Dict:
        """Get all sessions for a user"""
        sessions, total = self.chat_db.get_user_sessions(user_id, limit, offset)
        
        return {
            'sessions': sessions,
            'total': total,
            'limit': limit,
            'offset': offset,
            'has_more': offset + len(sessions) < total
        }
    
    def delete_session(self, session_id: str) -> bool:
        """Delete a session"""
        return self.chat_db.delete_session(session_id)
