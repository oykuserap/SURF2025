#!/usr/bin/env python3
"""
Rename agenda files with proper zero-padding for chronological sorting.
Format: agenda_001.txt, agenda_002.txt, etc.

This fixes the sorting issue where Agenda_10.txt appears before Agenda_2.txt
"""

import os
import re
from pathlib import Path

def rename_agenda_files():
    """Rename agenda files with zero-padding."""
    
    agenda_dir = Path("/Users/serap/SURF2025/Agendas_COR")
    
    if not agenda_dir.exists():
        print("❌ Agendas_COR directory not found!")
        return
    
    # Get all agenda files
    agenda_files = []
    for file_path in agenda_dir.glob("Agenda_*.txt"):
        # Extract number from filename
        match = re.search(r'Agenda_(\d+)([a-z]*)', file_path.name)
        if match:
            number = int(match.group(1))
            suffix = match.group(2) if match.group(2) else ""
            agenda_files.append((file_path, number, suffix))
    
    # Sort by number
    agenda_files.sort(key=lambda x: x[1])
    
    print(f"Found {len(agenda_files)} agenda files to rename:")
    print("=" * 80)
    
    # Determine padding needed (3 digits should be enough: 001-999)
    max_number = max(item[1] for item in agenda_files) if agenda_files else 0
    padding = max(3, len(str(max_number)))
    
    rename_map = {}
    
    print(f"Using {padding}-digit padding (max number: {max_number})")
    print()
    
    # Generate new names
    for file_path, number, suffix in agenda_files[:20]:  # Show first 20
        old_name = file_path.name
        
        if suffix:
            # Handle special cases like Agenda_372b.txt
            new_name = f"agenda_{number:0{padding}d}{suffix}.txt"
        else:
            new_name = f"agenda_{number:0{padding}d}.txt"
        
        rename_map[old_name] = new_name
        print(f"{old_name} → {new_name}")
    
    if len(agenda_files) > 20:
        print(f"... and {len(agenda_files)-20} more similar renames")
    
    print()
    print("Example chronological sorting improvement:")
    print("Before: Agenda_1.txt, Agenda_10.txt, Agenda_2.txt, Agenda_20.txt")
    print("After:  agenda_001.txt, agenda_002.txt, agenda_010.txt, agenda_020.txt")
    print()
    
    # Show cost estimate
    print("💰 COST ESTIMATE:")
    print(f"   • {len(agenda_files)} agenda files need re-embedding")
    print(f"   • Estimated cost: ~${len(agenda_files) * 0.02:.2f} (at $0.02 per file)")
    print(f"   • Estimated time: ~{len(agenda_files) // 50} minutes")
    print()
    
    # Ask for confirmation
    response = input("❓ Proceed with agenda renaming? This will require re-embedding all agendas. (y/N): ").strip().lower()
    
    if response == 'y':
        success_count = 0
        
        # Complete the rename mapping for all files
        full_rename_map = {}
        for file_path, number, suffix in agenda_files:
            old_name = file_path.name
            if suffix:
                new_name = f"agenda_{number:0{padding}d}{suffix}.txt"
            else:
                new_name = f"agenda_{number:0{padding}d}.txt"
            full_rename_map[old_name] = new_name
        
        # Perform renames
        for file_path, number, suffix in agenda_files:
            try:
                old_name = file_path.name
                new_name = full_rename_map[old_name]
                new_path = agenda_dir / new_name
                
                file_path.rename(new_path)
                success_count += 1
                
                if success_count <= 10 or success_count % 50 == 0:
                    print(f"✅ Renamed: {old_name} → {new_name}")
            except Exception as e:
                print(f"❌ Error renaming {file_path.name}: {e}")
        
        print(f"\n🎉 Successfully renamed {success_count}/{len(agenda_files)} agenda files!")
        
        if success_count > 0:
            print("\n" + "="*60)
            print("⚠️  IMPORTANT NEXT STEPS:")
            print("1. Clear existing agenda embeddings:")
            print("   - Summaries collection")
            print("   - Structured data collection")
            print("2. Re-run the embedding pipeline:")
            print("   python main.py --step combined")
            print("   python main.py --step embeddings")
            print("3. This will regenerate all processed summaries and embeddings")
            print("="*60)
        
    else:
        print("❌ Renaming cancelled.")
        print("\n💡 Alternative: Keep current naming and accept the sorting quirk.")
        print("   The LLM can still work with Agenda_123.txt format.")

def create_cleanup_script():
    """Create a script to clean up old embeddings."""
    
    cleanup_script = '''#!/usr/bin/env python3
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
'''
    
    script_path = Path("/Users/serap/SURF2025/clear_agenda_embeddings.py")
    script_path.write_text(cleanup_script)
    print(f"\n📝 Created cleanup script: {script_path}")

if __name__ == "__main__":
    rename_agenda_files()
    create_cleanup_script()