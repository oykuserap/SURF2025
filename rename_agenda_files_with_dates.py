#!/usr/bin/env python3
"""
Rename agenda files with dates and descriptions extracted from content.
Format: agenda_YYYYMMDD_description.txt (similar to bond files)
"""

import os
import re
from pathlib import Path
from datetime import datetime

def extract_date_and_info_from_agenda(file_path: Path) -> tuple:
    """Extract date and meeting type from agenda content."""
    
    try:
        content = file_path.read_text(encoding='utf-8', errors='replace')[:2000]  # First 2000 chars
        content_lower = content.lower()
        
        # Common date patterns in agenda files
        date_patterns = [
            r'(\w+)\s+(\d{1,2}),?\s+(\d{4})',  # "January 15, 2024" or "January 15 2024"
            r'(\d{1,2})/(\d{1,2})/(\d{4})',     # "01/15/2024"
            r'(\d{1,2})-(\d{1,2})-(\d{4})',     # "01-15-2024"
            r'(\d{4})-(\d{1,2})-(\d{1,2})',     # "2024-01-15"
        ]
        
        extracted_date = None
        
        for pattern in date_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            if matches:
                match = matches[0]
                
                if len(match) == 3:
                    try:
                        # Handle different formats
                        if pattern == date_patterns[0]:  # Month name format
                            month_name, day, year = match
                            month_map = {
                                'january': '01', 'february': '02', 'march': '03', 'april': '04',
                                'may': '05', 'june': '06', 'july': '07', 'august': '08',
                                'september': '09', 'october': '10', 'november': '11', 'december': '12'
                            }
                            month = month_map.get(month_name.lower(), '01')
                            extracted_date = f"{year}{month}{day.zfill(2)}"
                            
                        elif pattern == date_patterns[1]:  # MM/DD/YYYY
                            month, day, year = match
                            extracted_date = f"{year}{month.zfill(2)}{day.zfill(2)}"
                            
                        elif pattern == date_patterns[2]:  # MM-DD-YYYY
                            month, day, year = match
                            extracted_date = f"{year}{month.zfill(2)}{day.zfill(2)}"
                            
                        elif pattern == date_patterns[3]:  # YYYY-MM-DD
                            year, month, day = match
                            extracted_date = f"{year}{month.zfill(2)}{day.zfill(2)}"
                        
                        # Validate date makes sense
                        if extracted_date and len(extracted_date) == 8:
                            year_int = int(extracted_date[:4])
                            if 2020 <= year_int <= 2025:  # Reasonable range
                                break
                    except:
                        continue
        
        # Determine meeting type/description from content
        description = "regular"  # default
        
        if any(term in content_lower for term in ['special', 'emergency']):
            description = "special"
        elif any(term in content_lower for term in ['public hearing', 'hearing']):
            description = "hearing"
        elif any(term in content_lower for term in ['budget', 'financial']):
            description = "budget"
        elif any(term in content_lower for term in ['zoning', 'planning', 'development']):
            description = "planning"
        elif any(term in content_lower for term in ['board of adjustment', 'adjustment']):
            description = "adjustment"
        elif any(term in content_lower for term in ['work session', 'workshop']):
            description = "workshop"
        elif any(term in content_lower for term in ['council', 'city council']):
            description = "council"
        
        return extracted_date, description
        
    except Exception as e:
        return None, "regular"

def rename_agenda_files_with_dates():
    """Rename agenda files with extracted dates and descriptions."""
    
    agenda_dir = Path("/Users/serap/SURF2025/Agendas_COR")
    
    if not agenda_dir.exists():
        print("❌ Agendas_COR directory not found!")
        return
    
    # Get all agenda files
    agenda_files = []
    for file_path in agenda_dir.glob("Agenda_*.txt"):
        # Extract original number for fallback
        match = re.search(r'Agenda_(\d+)', file_path.name)
        if match:
            original_number = int(match.group(1))
            agenda_files.append((file_path, original_number))
    
    print(f"Found {len(agenda_files)} agenda files to analyze and rename...")
    print("=" * 80)
    print("Analyzing first 10 files to extract dates and descriptions...")
    print()
    
    sample_renames = []
    
    # Analyze first 10 files to show the pattern
    for file_path, original_number in agenda_files[:10]:
        old_name = file_path.name
        
        # Extract date and description from content
        extracted_date, description = extract_date_and_info_from_agenda(file_path)
        
        if extracted_date:
            new_name = f"agenda_{extracted_date}_{description}.txt"
        else:
            # Fallback to sequential numbering with padding
            new_name = f"agenda_unknown_{original_number:03d}_{description}.txt"
        
        sample_renames.append((old_name, new_name, extracted_date, description))
        print(f"{old_name}")
        print(f"  → {new_name}")
        print(f"  📅 Date: {extracted_date or 'Not found'} | Type: {description}")
        print()
    
    if len(agenda_files) > 10:
        print(f"... and {len(agenda_files)-10} more files will be similarly processed")
        print()
    
    # Show benefits
    print("🎯 Benefits of this approach:")
    print("✅ Chronological sorting by actual meeting dates")
    print("✅ Consistent with bond file naming (agenda_YYYYMMDD_type.txt)")
    print("✅ Meeting type information in filename")
    print("✅ LLM can better understand temporal relationships")
    print()
    
    # Show cost estimate
    print("💰 COST ESTIMATE:")
    print(f"   • {len(agenda_files)} agenda files need re-embedding")
    print(f"   • Estimated cost: ~${len(agenda_files) * 0.02:.2f}")
    print(f"   • Estimated time: ~{len(agenda_files) // 50} minutes")
    print(f"   • Processing time: ~{len(agenda_files) // 10} minutes to analyze content")
    print()
    
    # Ask for confirmation
    response = input("❓ Proceed with date-based agenda renaming? (y/N): ").strip().lower()
    
    if response == 'y':
        print("\n🔄 Processing all files...")
        
        success_count = 0
        rename_map = {}
        date_conflicts = {}
        
        # Process all files
        for i, (file_path, original_number) in enumerate(agenda_files):
            if i % 50 == 0:
                print(f"📊 Processing file {i+1}/{len(agenda_files)}...")
            
            old_name = file_path.name
            extracted_date, description = extract_date_and_info_from_agenda(file_path)
            
            if extracted_date:
                base_name = f"agenda_{extracted_date}_{description}"
            else:
                base_name = f"agenda_unknown_{original_number:03d}_{description}"
            
            # Handle duplicate names
            new_name = f"{base_name}.txt"
            counter = 1
            while new_name in rename_map.values():
                new_name = f"{base_name}_{counter:02d}.txt"
                counter += 1
            
            rename_map[old_name] = new_name
        
        # Perform renames
        print("\n🔄 Renaming files...")
        for file_path, original_number in agenda_files:
            try:
                old_name = file_path.name
                new_name = rename_map[old_name]
                new_path = agenda_dir / new_name
                
                file_path.rename(new_path)
                success_count += 1
                
                if success_count <= 10 or success_count % 100 == 0:
                    print(f"✅ {old_name} → {new_name}")
            except Exception as e:
                print(f"❌ Error renaming {file_path.name}: {e}")
        
        print(f"\n🎉 Successfully renamed {success_count}/{len(agenda_files)} agenda files!")
        
        if success_count > 0:
            print("\n" + "="*60)
            print("⚠️  IMPORTANT NEXT STEPS:")
            print("1. Clear existing agenda embeddings:")
            print("   python clear_agenda_embeddings.py")
            print("2. Re-run the full pipeline:")
            print("   python main.py --step combined")
            print("   python main.py --step embeddings")
            print("="*60)
        
    else:
        print("❌ Renaming cancelled.")

if __name__ == "__main__":
    rename_agenda_files_with_dates()