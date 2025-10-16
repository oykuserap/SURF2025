#!/usr/bin/env python3
"""
Option: Update embedding metadata to normalize agenda references 
without renaming files or re-embedding.
"""

from pathlib import Path
import chromadb

def update_agenda_metadata():
    """Update metadata to use consistent naming without re-embedding."""
    
    print("🔍 Checking if we can update metadata without re-embedding...")
    
    # Connect to vector DB
    try:
        vector_db_dir = Path("/Users/serap/SURF2025/vector_db")
        client = chromadb.PersistentClient(path=str(vector_db_dir))
        
        # Check collections
        collections = client.list_collections()
        for collection in collections:
            print(f"📊 Collection: {collection.name}")
            
            # Get sample entries to see metadata structure
            results = collection.get(limit=3, include=['metadatas'])
            
            if results['metadatas']:
                print("   Sample metadata:")
                for meta in results['metadatas'][:2]:
                    print(f"   - {meta}")
            print()
            
    except Exception as e:
        print(f"❌ Error checking vector DB: {e}")

if __name__ == "__main__":
    update_agenda_metadata()