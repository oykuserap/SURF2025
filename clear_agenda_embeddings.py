#!/usr/bin/env python3
"""
Clean up old agenda embeddings after renaming files.
"""

import chromadb
from pathlib import Path

def clear_agenda_embeddings():
    """Clear existing agenda embeddings before re-embedding with new names."""
    
    vector_db_dir = Path("/Users/serap/SURF2025/vector_db")
    
    try:
        client = chromadb.PersistentClient(path=str(vector_db_dir))
        
        # Delete and recreate agenda collections
        try:
            client.delete_collection("agenda_summaries")
            print("✅ Cleared agenda_summaries collection")
        except Exception:
            print("ℹ️  agenda_summaries collection not found")
        
        try:
            client.delete_collection("agenda_structured_data") 
            print("✅ Cleared agenda_structured_data collection")
        except Exception:
            print("ℹ️  agenda_structured_data collection not found")
        
        # Recreate collections
        client.create_collection("agenda_summaries")
        client.create_collection("agenda_structured_data")
        print("✅ Recreated collections for new embeddings")
        
    except Exception as e:
        print(f"❌ Error clearing embeddings: {e}")

if __name__ == "__main__":
    clear_agenda_embeddings()
