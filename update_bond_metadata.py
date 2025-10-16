#!/usr/bin/env python3
"""
Update bond document metadata to reflect new clean filenames.
"""

import chromadb
from pathlib import Path

def update_bond_metadata():
    """Update bond document metadata with new clean filenames."""
    
    vector_db_dir = Path("/Users/serap/SURF2025/vector_db")
    bond_data_dir = Path("/Users/serap/SURF2025/bond_data")
    
    # Create mapping of old to new filenames
    old_to_new = {}
    
    # You'd need to run this after the bond renaming
    # For now, let's check what needs updating
    
    try:
        client = chromadb.PersistentClient(path=str(vector_db_dir))
        bond_collection = client.get_collection("bond_documents")
        
        # Get all bond documents
        results = bond_collection.get(include=['metadatas'])
        
        print("🔍 Current bond document metadata:")
        for i, metadata in enumerate(results['metadatas']):
            old_name = metadata.get('source_file', 'Unknown')
            print(f"{i+1:2d}. {old_name}")
            
            if i >= 5:  # Just show first few
                print(f"    ... and {len(results['metadatas'])-6} more")
                break
                
        print(f"\n📊 Total bond documents in vector DB: {len(results['metadatas'])}")
        print("\n💡 After renaming bond files, you'll need to:")
        print("1. Re-embed bond documents (only ~25 files)")
        print("2. Or update metadata mapping (more complex)")
        print("3. Keep agenda files as-is (saves $$$ and time)")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    update_bond_metadata()