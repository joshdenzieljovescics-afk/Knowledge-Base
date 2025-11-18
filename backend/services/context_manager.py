# services/context_manager.py
from typing import List, Dict

class ContextManager:
    def __init__(self):
        self.max_context_tokens = 2000  # Rough estimate
    
    def get_recent_context(
        self,
        messages: List[Dict],
        max_messages: int = 10,
        max_tokens: int = 2000
    ) -> List[Dict]:
        """
        Get recent conversation context for query processing
        
        Args:
            messages: List of message dicts with role and content
            max_messages: Maximum number of messages to include
            max_tokens: Maximum token estimate for context
        
        Returns:
            List of message dicts suitable for OpenAI API
        """
        if not messages:
            return []
        
        # Take the most recent messages
        recent_messages = messages[-max_messages:] if len(messages) > max_messages else messages
        
        # Estimate tokens (rough: ~4 chars per token)
        context = []
        total_chars = 0
        max_chars = max_tokens * 4
        
        # Go backwards to prioritize recent messages
        for msg in reversed(recent_messages):
            content = msg.get('content', '')
            chars = len(content)
            
            if total_chars + chars > max_chars and context:
                # Stop adding more messages
                break
            
            context.insert(0, {
                'role': msg['role'],
                'content': content
            })
            total_chars += chars
        
        return context
    
    def build_kb_context(self, chunks: List[Dict]) -> str:
        """
        Build context string from knowledge base chunks
        
        Args:
            chunks: List of chunk dicts from Weaviate
        
        Returns:
            Formatted context string with sources
        """
        if not chunks:
            return "No relevant information found in the knowledge base."
        
        context_parts = []
        for i, chunk in enumerate(chunks, 1):
            doc_name = chunk.get('document_name', 'Unknown')
            page = chunk.get('page', 'N/A')
            text = chunk.get('text', '')
            
            # Truncate very long chunks
            if len(text) > 500:
                text = text[:500] + "..."
            
            context_parts.append(
                f"[Source {i}: {doc_name}, Page {page}]\n{text}"
            )
        
        return "\n\n".join(context_parts)
    
    def format_sources(self, chunks: List[Dict]) -> List[Dict]:
        """
        Format chunks into source citations
        
        Args:
            chunks: List of chunk dicts from Weaviate
        
        Returns:
            List of formatted source dicts
        """
        sources = []
        for chunk in chunks:
            sources.append({
                'chunk_id': chunk.get('chunk_id'),
                'document_name': chunk.get('document_name', 'Unknown'),
                'page': chunk.get('page', 0),
                'relevance_score': chunk.get('score', 0),
                'text': chunk.get('text', '')[:200] + "..." if len(chunk.get('text', '')) > 200 else chunk.get('text', ''),
                'metadata': chunk.get('metadata', {})
            })
        
        return sources
