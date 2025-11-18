# services/weaviate_search_service.py
from typing import List, Dict, Optional
import weaviate
from database.weaviate_client import get_weaviate_client

class WeaviateSearchService:
    def __init__(self):
        self.client = get_weaviate_client()
        self.collection_name = "DocumentChunk"
    
    def hybrid_search(
        self,
        query: str,
        limit: int = 10,
        filters: Optional[Dict] = None
    ) -> List[Dict]:
        """
        Perform hybrid search (semantic + keyword) on Weaviate
        """
        try:
            collection = self.client.collections.get(self.collection_name)
            
            # Build where filter if provided
            where_filter = None
            if filters:
                if 'document_ids' in filters and filters['document_ids']:
                    where_filter = {
                        "path": ["document_id"],
                        "operator": "ContainsAny",
                        "valueTextArray": filters['document_ids']
                    }
            
            # Hybrid search (combines vector and BM25)
            response = collection.query.hybrid(
                query=query,
                limit=limit,
                where=where_filter,
                return_metadata=["score", "distance"],
                return_properties=[
                    "chunk_id",
                    "text",
                    "chunk_type",
                    "document_id",
                    "document_name",
                    "page",
                    "section",
                    "metadata"
                ]
            )
            
            # Format results
            results = []
            for obj in response.objects:
                results.append({
                    'chunk_id': obj.properties.get('chunk_id'),
                    'text': obj.properties.get('text'),
                    'chunk_type': obj.properties.get('chunk_type'),
                    'document_id': obj.properties.get('document_id'),
                    'document_name': obj.properties.get('document_name'),
                    'page': obj.properties.get('page'),
                    'section': obj.properties.get('section'),
                    'metadata': obj.properties.get('metadata', {}),
                    'score': obj.metadata.score if hasattr(obj.metadata, 'score') else 0.5,
                })
            
            return results
            
        except Exception as e:
            print(f"Error in hybrid search: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def semantic_search(
        self,
        query: str,
        limit: int = 10,
        filters: Optional[Dict] = None
    ) -> List[Dict]:
        """
        Perform pure semantic (vector) search
        """
        try:
            collection = self.client.collections.get(self.collection_name)
            
            where_filter = None
            if filters and 'document_ids' in filters and filters['document_ids']:
                where_filter = {
                    "path": ["document_id"],
                    "operator": "ContainsAny",
                    "valueTextArray": filters['document_ids']
                }
            
            response = collection.query.near_text(
                query=query,
                limit=limit,
                where=where_filter,
                return_metadata=["distance"],
                return_properties=[
                    "chunk_id", "text", "chunk_type", "document_id",
                    "document_name", "page", "section", "metadata"
                ]
            )
            
            results = []
            for obj in response.objects:
                # Convert distance to similarity score (0-1)
                distance = obj.metadata.distance if hasattr(obj.metadata, 'distance') else 1.0
                score = 1 / (1 + distance)
                
                results.append({
                    'chunk_id': obj.properties.get('chunk_id'),
                    'text': obj.properties.get('text'),
                    'chunk_type': obj.properties.get('chunk_type'),
                    'document_id': obj.properties.get('document_id'),
                    'document_name': obj.properties.get('document_name'),
                    'page': obj.properties.get('page'),
                    'section': obj.properties.get('section'),
                    'metadata': obj.properties.get('metadata', {}),
                    'score': score
                })
            
            return results
            
        except Exception as e:
            print(f"Error in semantic search: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def get_chunk_by_id(self, chunk_id: str) -> Optional[Dict]:
        """Get a specific chunk by ID"""
        try:
            collection = self.client.collections.get(self.collection_name)
            
            response = collection.query.fetch_objects(
                where={
                    "path": ["chunk_id"],
                    "operator": "Equal",
                    "valueText": chunk_id
                },
                limit=1
            )
            
            if response.objects:
                obj = response.objects[0]
                return {
                    'chunk_id': obj.properties.get('chunk_id'),
                    'text': obj.properties.get('text'),
                    'chunk_type': obj.properties.get('chunk_type'),
                    'document_id': obj.properties.get('document_id'),
                    'document_name': obj.properties.get('document_name'),
                    'page': obj.properties.get('page'),
                    'section': obj.properties.get('section'),
                    'metadata': obj.properties.get('metadata', {})
                }
            
            return None
            
        except Exception as e:
            print(f"Error getting chunk by ID: {e}")
            return None
