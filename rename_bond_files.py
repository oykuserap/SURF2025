#!/usr/bin/env python3
"""
Script to rename bond data files with a consistent naming convention.
Format: bond_YYYYMMDD_description.txt
"""

import os
import re
from pathlib import Path
from datetime import datetime

def extract_date_from_filename(filename: str) -> str:
    """Extract date from various filename formats."""
    
    # Common date patterns in the filenames
    patterns = [
        r'(\d{2})(\d{2})(\d{4})',  # MMDDYYYY like 02062023
        r'(\d{8})',               # YYYYMMDD like 20230612
        r'(\d{2})-(\d{2})-(\d{2})', # MM-DD-YY like 03-05-25
        r'(\d{2})(\d{2})(\d{2})',   # MMDDYY like 081623
        r'(\d{1,2})(\d{2})(\d{2})', # MDDYY like 011723
        r'(\d{4})',               # Just year like 2024
        r'(\d{2})(\d{2})(\d{4})',  # DDMMYYYY like 020724
    ]
    
    # Try to extract dates from filename
    for pattern in patterns:
        matches = re.findall(pattern, filename)
        if matches:
            match = matches[0]
            
            # Handle different formats
            if len(match) == 3:  # MM/DD/YYYY or similar
                if len(match[2]) == 4:  # YYYY format
                    month, day, year = match
                    if int(month) <= 12 and int(day) <= 31:
                        return f"{year}{month.zfill(2)}{day.zfill(2)}"
                elif len(match[2]) == 2:  # YY format
                    month, day, year_short = match
                    year = f"20{year_short}"
                    if int(month) <= 12 and int(day) <= 31:
                        return f"{year}{month.zfill(2)}{day.zfill(2)}"
            elif len(match) == 1 and len(match[0]) == 8:  # YYYYMMDD
                return match[0]
            elif len(match) == 1 and len(match[0]) == 4:  # Just year
                return f"{match[0]}0101"  # Default to Jan 1
    
    # Handle special cases manually
    filename_lower = filename.lower()
    if "august 21, 2024" in filename_lower:
        return "20240821"
    elif "june 21, 2023" in filename_lower:
        return "20230621"
    elif "february 24, 2025" in filename_lower:
        return "20250224"
    elif "october 16, 2024" in filename_lower:
        return "20241016"
    
    # Default fallback
    return "20240101"

def generate_clean_filename(original_filename: str) -> str:
    """Generate a clean filename based on content and date."""
    
    # Extract date
    date_str = extract_date_from_filename(original_filename)
    
    # Create description based on content
    base_name = original_filename.lower().replace('.txt', '')
    
    # Key terms for categorization
    if any(term in base_name for term in ['police', 'law enforcement', 'public safety']):
        if 'training' in base_name:
            description = "police_training"
        else:
            description = "police_public_safety"
    elif any(term in base_name for term in ['park', 'recreation', 'pkr']):
        description = "parks_recreation"
    elif any(term in base_name for term in ['cultural', 'culture', 'arts', 'libraries']):
        description = "cultural_facilities"
    elif any(term in base_name for term in ['homeless', 'housing']):
        description = "homeless_solutions"
    elif any(term in base_name for term in ['infrastructure', 'trni']):
        description = "infrastructure"
    elif any(term in base_name for term in ['economic', 'development']):
        description = "economic_development"
    elif any(term in base_name for term in ['environment', 'sustainability', 'cecap']):
        description = "environmental"
    elif any(term in base_name for term in ['quarterly', 'reporting']):
        description = "quarterly_report"
    elif any(term in base_name for term in ['technical', 'criteria', 'scoring']):
        description = "technical_criteria"
    elif any(term in base_name for term in ['final', 'proposed']):
        description = "final_proposal"
    elif any(term in base_name for term in ['update', 'briefing']):
        description = "program_update"
    elif any(term in base_name for term in ['past', 'history', '2006', '2012', '2017']):
        description = "historical_programs"
    else:
        # Generic bond program
        description = "bond_program"
    
    return f"bond_{date_str}_{description}.txt"

def main():
    bond_data_dir = Path("/Users/serap/SURF2025/bond_data")
    
    if not bond_data_dir.exists():
        print("Bond data directory not found!")
        return
    
    # Get all txt files
    txt_files = list(bond_data_dir.glob("*.txt"))
    
    print(f"Found {len(txt_files)} bond files to rename:")
    print("=" * 80)
    
    rename_map = {}
    
    # Generate new names
    for file_path in txt_files:
        old_name = file_path.name
        new_name = generate_clean_filename(old_name)
        
        # Handle duplicates
        counter = 1
        original_new_name = new_name
        while new_name in rename_map.values():
            base = original_new_name.replace('.txt', '')
            new_name = f"{base}_{counter:02d}.txt"
            counter += 1
        
        rename_map[old_name] = new_name
        print(f"{old_name}")
        print(f"  → {new_name}")
        print()
    
    # Ask for confirmation
    print("=" * 80)
    response = input("Proceed with renaming? (y/N): ").strip().lower()
    
    if response == 'y':
        success_count = 0
        for old_name, new_name in rename_map.items():
            try:
                old_path = bond_data_dir / old_name
                new_path = bond_data_dir / new_name
                old_path.rename(new_path)
                success_count += 1
                print(f"✅ Renamed: {old_name} → {new_name}")
            except Exception as e:
                print(f"❌ Error renaming {old_name}: {e}")
        
        print(f"\n🎉 Successfully renamed {success_count}/{len(txt_files)} files!")
        
        # Also suggest renaming agenda files
        print("\n" + "=" * 80)
        print("SUGGESTION: You might also want to clean up agenda filenames.")
        print("Current agenda files use 'Agenda_123.txt' format.")
        print("Consider: 'agenda_123.txt' for consistency.")
        
    else:
        print("❌ Renaming cancelled.")

if __name__ == "__main__":
    main()