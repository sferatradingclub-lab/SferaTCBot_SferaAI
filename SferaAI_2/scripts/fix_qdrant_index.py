import os
import sys
from qdrant_client import QdrantClient
from qdrant_client.http import models

def fix_index():
    # Hardcoded URL from logs
    qdrant_url = "https://a87e8ae4-abef-45a9-8147-5e91d3d27b8f.eu-central-1-0.aws.cloud.qdrant.io:6333"
    
    # Try to find API key in .env manually
    qdrant_api_key = None
    try:
        with open('.env', 'r', encoding='utf-8') as f:
            for line in f:
                if line.startswith('QDRANT_API_KEY='):
                    qdrant_api_key = line.strip().split('=', 1)[1].strip().strip('"').strip("'")
                    break
    except Exception as e:
        print(f"Warning: Could not read .env file: {e}")

    if not qdrant_api_key:
        print("ERROR: Could not find QDRANT_API_KEY in .env file.")
        # Fallback: ask user to input it if needed, or just fail
        return

    print(f"Connecting to Qdrant at {qdrant_url}...")
    client = QdrantClient(
        url=qdrant_url,
        api_key=qdrant_api_key
    )

    collection_name = "global_knowledge_base"
    
    print(f"Creating payload index for 'step_number' in collection '{collection_name}'...")
    
    try:
        client.create_payload_index(
            collection_name=collection_name,
            field_name="step_number",
            field_schema=models.PayloadSchemaType.INTEGER
        )
        print("SUCCESS: Index creation request sent.")
    except Exception as e:
        print(f"ERROR: Failed to create index: {e}")

if __name__ == "__main__":
    fix_index()
