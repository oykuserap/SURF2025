#!/usr/bin/env python3
"""
Update summary and JSON filenames to match the new agenda naming scheme.
Also update the pipeline to work with date-based filenames instead of numbers.
"""

import os
import re
import json
from pathlib import Path

def create_agenda_mapping():
    """Create mapping from old agenda numbers to new filenames."""
    
    agenda_dir = Path("/Users/serap/SURF2025/Agendas_COR")
    
    # Create mapping of agenda numbers to new filenames
    number_to_new_name = {}
    
    for agenda_file in agenda_dir.glob("agenda_*.txt"):
        # Try to find original agenda number from content or pattern
        # This is tricky since we already renamed the files
        
        # For now, let's check if there are any old-format files left
        pass
    
    return number_to_new_name

def fix_summary_and_json_naming():
    """Update summary and JSON files to match new agenda naming."""
    
    output_dir = Path("/Users/serap/SURF2025/processed_data")
    summaries_dir = output_dir / "summaries"
    json_dir = output_dir / "json_data"
    
    print("🔍 Current processed files:")
    
    # Check what we have
    summary_files = list(summaries_dir.glob("summary_*.json")) if summaries_dir.exists() else []
    json_files = list(json_dir.glob("data_*.json")) if json_dir.exists() else []
    
    print(f"📄 Summary files: {len(summary_files)}")
    print(f"📊 JSON files: {len(json_files)}")
    
    if summary_files:
        print("\nFirst few summary files:")
        for f in summary_files[:5]:
            print(f"  {f.name}")
    
    if json_files:
        print("\nFirst few JSON files:")
        for f in json_files[:5]:
            print(f"  {f.name}")
    
    print("\n💡 RECOMMENDATION:")
    print("Since we completely changed the agenda naming system, the easiest approach is:")
    print("1. Delete existing processed_data/ folder")
    print("2. Re-run the entire pipeline with new agenda filenames")
    print("3. This will generate new summary/JSON files with proper names")
    print("\nThis ensures everything is consistent and avoids complex mapping issues.")
    
    response = input("\n❓ Delete processed_data/ and start fresh? (y/N): ").strip().lower()
    
    if response == 'y':
        import shutil
        
        try:
            if output_dir.exists():
                shutil.rmtree(output_dir)
                print("✅ Deleted processed_data/ folder")
            
            # Recreate structure
            summaries_dir.mkdir(parents=True, exist_ok=True)
            json_dir.mkdir(parents=True, exist_ok=True)
            print("✅ Recreated processed_data/ structure")
            
            print("\n🚀 Now run the full pipeline:")
            print("1. python main.py --step combined")
            print("2. python main.py --step embeddings")
            
        except Exception as e:
            print(f"❌ Error: {e}")
    else:
        print("❌ Keeping existing files. You'll need to handle mapping manually.")

def check_pipeline_compatibility():
    """Check if the pipeline code needs updates for new naming scheme."""
    
    print("\n🔧 PIPELINE CODE UPDATES NEEDED:")
    print("\nThe pipeline currently expects:")
    print("- agenda_number based processing (Agenda_123.txt)")
    print("- summary_123.json and data_123.json naming")
    print("\nWith new date-based naming, we need to update:")
    print("- File discovery logic")
    print("- Summary/JSON naming scheme")
    print("- Metadata extraction")
    
    print("\n💡 Two options:")
    print("1. SIMPLE: Delete processed_data/ and regenerate (RECOMMENDED)")
    print("2. COMPLEX: Update all pipeline code to handle date-based naming")

if __name__ == "__main__":
    print("🎯 Summary and JSON File Naming Update")
    print("=" * 50)
    
    fix_summary_and_json_naming()
    check_pipeline_compatibility()