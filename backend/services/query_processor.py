# services/query_processor.py
import os
import openai
from typing import Dict, List
from dotenv import load_dotenv

# Ensure environment variables are loaded
load_dotenv()

class QueryProcessor:
    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is not set")
        self.openai_client = openai.OpenAI(api_key=api_key)
    
    def enhance_query(self, query: str, context: List[Dict]) -> Dict:
        """
        Enhance user query with context and extract search terms
        """
        # If there's context, check for follow-up patterns
        if context and self._is_followup(query):
            # Resolve references like "it", "that", "this"
            resolved_query = self._resolve_references(query, context)
        else:
            resolved_query = query
        
        # Extract key search terms (for now just use the resolved query)
        search_query = resolved_query
        
        return {
            'original_query': query,
            'resolved_query': resolved_query,
            'search_query': search_query
        }
    
    def _is_followup(self, query: str) -> bool:
        """Check if query is a follow-up"""
        # Expanded pattern list for better detection
        followup_patterns = [
            # Original patterns
            'what about', 'how about', 'tell me more',
            'can you explain', 'what does that mean',
            'elaborate', 'more details', 'continue',
            'and that', 'about it', 'about that',
            'the same', 'similar',
            
            # Questions asking for more
            'explain further', 'go deeper', 'more on',
            'expand on', 'clarify', 'break down',
            
            # Comparative follow-ups
            'compared to', 'versus', 'difference between',
            'what\'s the difference', 'how does that differ',
            
            # Continuation patterns
            'also', 'additionally', 'furthermore',
            'what else', 'anything else', 'what more',
            
            # Specific aspect requests
            'what part', 'which section', 'where in',
            'show me the', 'find the part where',
            
            # Clarification requests
            'i don\'t understand', 'confused about',
            'what did you mean', 'can you rephrase'
        ]
        query_lower = query.lower()
        
        # Enhanced pronoun detection (including possessives)
        pronouns = ['it', 'that', 'this', 'those', 'these', 'they', 'them', 'its', 'their', 'theirs']
        words = query_lower.split()
        has_pronoun = any(word in pronouns for word in words)
        
        # Check for follow-up patterns
        has_pattern = any(pattern in query_lower for pattern in followup_patterns)
        
        # Detect very short questions (likely follow-ups)
        is_very_short = len(words) <= 4 and ('?' in query or has_pronoun)
        
        return has_pronoun or has_pattern or is_very_short
    
    def _resolve_references(self, query: str, context: List[Dict]) -> str:
        """Resolve ambiguous references using context"""
        # Get last few messages to understand what "it" refers to
        last_messages = context[-4:] if len(context) >= 4 else context
        
        if not last_messages:
            return query
        
        context_text = "\n".join([
            f"{msg['role']}: {msg['content']}"
            for msg in last_messages
        ])
        
        try:
            # Use OpenAI to resolve
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "Rewrite the user's query to be standalone by resolving pronouns and references using the conversation context. Keep it concise and preserve the question's intent."
                    },
                    {
                        "role": "user",
                        "content": f"Conversation context:\n{context_text}\n\nQuery to resolve: {query}\n\nStandalone query:"
                    }
                ],
                temperature=0,
                max_tokens=100
            )
            
            resolved = response.choices[0].message.content.strip()
            print(f"[QueryProcessor] Resolved '{query}' to '{resolved}'")
            return resolved
        except Exception as e:
            print(f"[QueryProcessor] Error resolving query: {e}")
            return query
    
    def rerank_results(
        self,
        query: str,
        results: List[Dict],
        top_k: int = 5
    ) -> List[Dict]:
        """
        Rerank search results by relevance score
        Results already have scores from Weaviate, so just sort and return top_k
        """
        if not results:
            return []
        
        # Sort by score (descending)
        sorted_results = sorted(results, key=lambda x: x.get('score', 0), reverse=True)
        
        return sorted_results[:top_k]
