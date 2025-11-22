# services/weaviate_search_service.py
from typing import List, Dict, Optional
import weaviate
from database.weaviate_client import get_weaviate_client

class WeaviateSearchService:
    def __init__(self):
        self.client = get_weaviate_client()
        self.collection_name = "KnowledgeBase"  # Changed from DocumentChunk to match actual collection
    
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
            print(f"\n[WeaviateSearch] 🔍 HYBRID SEARCH STARTING")
            print(f"[WeaviateSearch] Query: {query}")
            print(f"[WeaviateSearch] Limit: {limit}")
            print(f"[WeaviateSearch] Filters: {filters}")
            print(f"[WeaviateSearch] Collection: {self.collection_name}")
            
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
                    print(f"[WeaviateSearch] Applied document filter: {filters['document_ids']}")
            
            # Hybrid search (combines vector and BM25)
            print(f"[WeaviateSearch] Executing hybrid search (vector + BM25)...")
            
            # Note: Some Weaviate versions don't support 'where' in hybrid queries
            # Apply filters after retrieval if needed
            if where_filter:
                print(f"[WeaviateSearch] Note: Filters will be applied post-query")
                response = collection.query.hybrid(
                    query=query,
                    limit=limit * 2,  # Get more to account for filtering
                    return_metadata=["score", "distance"],
                    return_properties=[
                        "chunk_id",
                        "text",
                        "type",  # Changed from chunk_type
                        "page",
                        "section",
                        "context",
                        "tags"
                    ],
                    return_references=[
                        weaviate.classes.query.QueryReference(
                            link_on="ofDocument",
                            return_properties=["file_name"]
                        )
                    ]
                )
            else:
                response = collection.query.hybrid(
                    query=query,
                    limit=limit,
                    return_metadata=["score", "distance"],
                    return_properties=[
                        "chunk_id",
                        "text",
                        "type",  # Changed from chunk_type
                        "page",
                        "section",
                        "context",
                        "tags"
                    ],
                    return_references=[
                        weaviate.classes.query.QueryReference(
                            link_on="ofDocument",
                            return_properties=["file_name"]
                        )
                    ]
                )
            
            # Format results
            results = []
            for obj in response.objects:
                # Get document name from reference
                document_name = "Unknown"
                document_id = None
                if hasattr(obj, 'references') and obj.references.get('ofDocument'):
                    doc_ref = obj.references['ofDocument'].objects[0] if obj.references['ofDocument'].objects else None
                    if doc_ref:
                        document_name = doc_ref.properties.get('file_name', 'Unknown')
                        document_id = str(doc_ref.uuid) if hasattr(doc_ref, 'uuid') else None
                
                result = {
                    'chunk_id': obj.properties.get('chunk_id'),
                    'text': obj.properties.get('text'),
                    'chunk_type': obj.properties.get('type', 'text'),  # Map 'type' to 'chunk_type'
                    'document_id': document_id,
                    'document_name': document_name,
                    'page': obj.properties.get('page'),
                    'section': obj.properties.get('section', ''),
                    'context': obj.properties.get('context', ''),
                    'tags': obj.properties.get('tags', []),
                    'score': obj.metadata.score if hasattr(obj.metadata, 'score') else 0.5,
                }
                
                # Apply document filter if specified
                if where_filter and document_id:
                    if document_id in filters.get('document_ids', []):
                        results.append(result)
                else:
                    results.append(result)
            
            # Trim to requested limit if we got extra for filtering
            if where_filter and len(results) > limit:
                results = results[:limit]
            
            print(f"[WeaviateSearch] ✅ Hybrid search returned {len(results)} results")
            if results:
                print(f"[WeaviateSearch] Top result: {results[0].get('document_name')} (score: {results[0].get('score'):.3f})")
            
            return results
            
        except Exception as e:
            print(f"[WeaviateSearch] ❌ Error in hybrid search: {e}")
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
                # Use reference path for filtering
                where_filter = {
                    "path": ["ofDocument"],
                    "operator": "ContainsAny",
                    "valueTextArray": filters['document_ids']
                }
            
            response = collection.query.near_text(
                query=query,
                limit=limit,
                where=where_filter,
                return_metadata=["distance"],
                return_properties=[
                    "chunk_id", "text", "type", "page", "section", "context", "tags"
                ],
                return_references=[
                    weaviate.classes.query.QueryReference(
                        link_on="ofDocument",
                        return_properties=["file_name"]
                    )
                ]
            )
            
            results = []
            for obj in response.objects:
                # Convert distance to similarity score (0-1)
                distance = obj.metadata.distance if hasattr(obj.metadata, 'distance') else 1.0
                score = 1 / (1 + distance)
                
                # Get document name from reference
                document_name = "Unknown"
                document_id = None
                if hasattr(obj, 'references') and obj.references.get('ofDocument'):
                    doc_ref = obj.references['ofDocument'].objects[0] if obj.references['ofDocument'].objects else None
                    if doc_ref:
                        document_name = doc_ref.properties.get('file_name', 'Unknown')
                        document_id = str(doc_ref.uuid) if hasattr(doc_ref, 'uuid') else None
                
                results.append({
                    'chunk_id': obj.properties.get('chunk_id'),
                    'text': obj.properties.get('text'),
                    'chunk_type': obj.properties.get('type', 'text'),
                    'document_id': document_id,
                    'document_name': document_name,
                    'page': obj.properties.get('page'),
                    'section': obj.properties.get('section', ''),
                    'context': obj.properties.get('context', ''),
                    'tags': obj.properties.get('tags', []),
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
                limit=1,
                return_properties=["chunk_id", "text", "type", "page", "section", "context", "tags"],
                return_references=[
                    weaviate.classes.query.QueryReference(
                        link_on="ofDocument",
                        return_properties=["file_name"]
                    )
                ]
            )
            
            if response.objects:
                obj = response.objects[0]
                
                # Get document name from reference
                document_name = "Unknown"
                document_id = None
                if hasattr(obj, 'references') and obj.references.get('ofDocument'):
                    doc_ref = obj.references['ofDocument'].objects[0] if obj.references['ofDocument'].objects else None
                    if doc_ref:
                        document_name = doc_ref.properties.get('file_name', 'Unknown')
                        document_id = str(doc_ref.uuid) if hasattr(doc_ref, 'uuid') else None
                
                return {
                    'chunk_id': obj.properties.get('chunk_id'),
                    'text': obj.properties.get('text'),
                    'chunk_type': obj.properties.get('type', 'text'),
                    'document_id': document_id,
                    'document_name': document_name,
                    'page': obj.properties.get('page'),
                    'section': obj.properties.get('section', ''),
                    'context': obj.properties.get('context', ''),
                    'tags': obj.properties.get('tags', [])
                }
            
            return None
            
        except Exception as e:
            print(f"Error getting chunk by ID: {e}")
            return None
