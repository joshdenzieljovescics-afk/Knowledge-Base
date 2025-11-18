"""Weaviate client initialization and management."""
import weaviate
from weaviate.classes.config import Configure, Property, DataType
from config import Config


# Initialize configuration
Config.validate()

# Create Weaviate client
headers = {
    "X-OpenAI-Api-Key": Config.OPENAI_API_KEY,
}

weaviate_client = weaviate.connect_to_weaviate_cloud(
    cluster_url=Config.WEAVIATE_URL,
    auth_credentials=weaviate.auth.AuthApiKey(Config.WEAVIATE_API_KEY),
    headers=headers
)

# Connect the client
if not weaviate_client.is_connected():
    print("🔌 Connecting to Weaviate...")
    weaviate_client.connect()
    print("✅ Connected to Weaviate")


def ensure_collections_exist():
    """Ensure Document and KnowledgeBase collections exist in Weaviate."""
    
    # Reconnect if disconnected
    if not weaviate_client.is_connected():
        print("🔌 Reconnecting to Weaviate...")
        weaviate_client.connect()
        print("✅ Reconnected to Weaviate")
    
    # Create Document collection if not exists
    if "Document" not in weaviate_client.collections.list_all():
        weaviate_client.collections.create(
            name="Document",
            properties=[
                Property(name="file_name", data_type=DataType.TEXT),
                Property(name="page_count", data_type=DataType.NUMBER),
            ]
        )
        print("✅ Created Document collection")

    # Create KnowledgeBase collection if not exists
    if "KnowledgeBase" not in weaviate_client.collections.list_all():
        weaviate_client.collections.create(
            name="KnowledgeBase",
            vector_config=[
                Configure.Vectors.text2vec_openai(
                    name="text_vector",
                    source_properties=["text"],
                    model=Config.EMBEDDING_MODEL,
                    dimensions=Config.EMBEDDING_DIMENSIONS
                )
            ],
            generative_config=Configure.Generative.openai(
                model=Config.OPENAI_MODEL,
                temperature=Config.TEMPERATURE,
            ),
            properties=[
                Property(name="text", data_type=DataType.TEXT),
                Property(name="type", data_type=DataType.TEXT),
                Property(name="section", data_type=DataType.TEXT),
                Property(name="context", data_type=DataType.TEXT),
                Property(name="tags", data_type=DataType.TEXT_ARRAY),
                Property(name="page", data_type=DataType.NUMBER),
                Property(name="chunk_id", data_type=DataType.TEXT),
                Property(name="created_at", data_type=DataType.TEXT),
                Property(name="ofDocument", data_type=DataType.REFERENCE, reference_to="Document"),
            ]
        )
        print("✅ Created KnowledgeBase collection")


def get_weaviate_client():
    """Get the Weaviate client instance."""
    return weaviate_client
