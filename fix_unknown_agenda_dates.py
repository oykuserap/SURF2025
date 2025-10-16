#!/usr/bin/env python3
"""
Script to fix agenda files with 'unknown' dates by using enhanced date extraction.
"""

import re
from pathlib import Path
from datetime import datetime
import shutil

def extract_date_from_content(content: str) -> str:
    """Enhanced date extraction that looks for various date patterns."""
    
    # Clean up the content - remove excessive whitespace and page breaks
    content = re.sub(r'-+ Page \d+ -+', '', content)
    content = re.sub(r'\s+', ' ', content)
    
    # Date patterns to look for (in order of preference)
    date_patterns = [
        # Pattern 1: "January 13th, 2025" or "November 19th, 2024"
        (r'([A-Z][a-z]+ \d{1,2}(?:st|nd|rd|th)?, \d{4})', '%B %d, %Y'),
        
        # Pattern 2: "March 28, 2025" or "April 7, 2025" 
        (r'([A-Z][a-z]+ \d{1,2}, \d{4})', '%B %d, %Y'),
        
        # Pattern 3: "01/15/2025" or "1/15/25"
        (r'(\d{1,2}/\d{1,2}/\d{2,4})', None),
        
        # Pattern 4: "2025-01-15"
        (r'(\d{4}-\d{2}-\d{2})', '%Y-%m-%d'),
        
        # Pattern 5: Look for dates after keywords like "MEETING" or specific times
        (r'(?:MEETING|meeting).*?([A-Z][a-z]+ \d{1,2}(?:st|nd|rd|th)?, \d{4})', '%B %d, %Y'),
        
        # Pattern 6: Look for dates with day names
        (r'(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),?\s*([A-Z][a-z]+ \d{1,2}(?:st|nd|rd|th)?, \d{4})', '%B %d, %Y'),
    ]
    
    for pattern, date_format in date_patterns:
        matches = re.findall(pattern, content, re.IGNORECASE)
        if matches:
            for match in matches:
                try:
                    # Clean up ordinal suffixes (st, nd, rd, th)
                    cleaned_date = re.sub(r'(\d{1,2})(st|nd|rd|th)', r'\1', match)
                    
                    if date_format:
                        parsed_date = datetime.strptime(cleaned_date, date_format)
                    else:
                        # Handle various slash formats
                        if '/' in cleaned_date:
                            parts = cleaned_date.split('/')
                            if len(parts) == 3:
                                month, day, year = parts
                                if len(year) == 2:
                                    year = f"20{year}" if int(year) < 50 else f"19{year}"
                                parsed_date = datetime(int(year), int(month), int(day))
                    
                    # Return in YYYYMMDD format
                    return parsed_date.strftime('%Y%m%d')
                    
                except ValueError:
                    continue
    
    return None

def categorize_meeting_type(content: str) -> str:
    """Enhanced meeting type categorization."""
    content_upper = content.upper()
    
    # Check for specific patterns
    if any(term in content_upper for term in ["YOUTH COMMISSION", "YOUTH BOARD"]):
        return "youth"
    elif any(term in content_upper for term in ["BUDGET", "FISCAL"]):
        return "budget"
    elif any(term in content_upper for term in ["SPECIAL CALLED", "SPECIAL MEETING"]):
        return "special"
    elif any(term in content_upper for term in ["PUBLIC HEARING", "HEARING"]):
        return "hearing"
    elif any(term in content_upper for term in ["REGULAR MEETING", "REGULAR"]):
        return "regular"
    elif any(term in content_upper for term in ["COUNCIL", "CITY COUNCIL"]):
        return "council"
    else:
        return "meeting"

def main():
    agendas_dir = Path("/Users/serap/SURF2025/Agendas_COR")
    
    # Find all files with 'unknown' in the name
    unknown_files = list(agendas_dir.glob("*unknown*"))
    
    print(f"Found {len(unknown_files)} files with 'unknown' in the name")
    
    fixed_count = 0
    failed_files = []
    
    for file_path in unknown_files:
        print(f"\n Processing: {file_path.name}")
        
        try:
            # Read the file content
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Extract date
            extracted_date = extract_date_from_content(content)
            
            if extracted_date:
                # Extract meeting type from filename and content
                old_type = file_path.stem.split('_')[-1]  # Get the last part (hearing, regular, etc.)
                new_type = categorize_meeting_type(content)
                
                # Use the more specific type if available
                final_type = new_type if new_type != "meeting" else old_type
                
                # Create new filename
                new_filename = f"agenda_{extracted_date}_{final_type}.txt"
                new_path = file_path.parent / new_filename
                
                # Check if target file already exists
                if new_path.exists():
                    print(f"   ⚠️  Target file already exists: {new_filename}")
                    # Add a suffix to make it unique
                    counter = 1
                    while new_path.exists():
                        new_filename = f"agenda_{extracted_date}_{final_type}_{counter:02d}.txt"
                        new_path = file_path.parent / new_filename
                        counter += 1
                
                # Rename the file
                shutil.move(str(file_path), str(new_path))
                print(f"   ✅ Renamed to: {new_filename}")
                print(f"   📅 Extracted date: {extracted_date}")
                print(f"   📋 Meeting type: {final_type}")
                
                fixed_count += 1
            else:
                print(f"   ❌ Could not extract date from content")
                failed_files.append(file_path.name)
                
                # Show first few lines for manual inspection
                lines = content.split('\n')[:10]
                print(f"   📄 First few lines:")
                for i, line in enumerate(lines):
                    if line.strip():
                        print(f"      {i+1}: {line.strip()[:100]}")
        
        except Exception as e:
            print(f"   ❌ Error processing file: {e}")
            failed_files.append(file_path.name)
    
    print(f"\n📊 Summary:")
    print(f"   ✅ Successfully fixed: {fixed_count}")
    print(f"   ❌ Failed: {len(failed_files)}")
    
    if failed_files:
        print(f"\n📋 Failed files:")
        for filename in failed_files:
            print(f"   - {filename}")

if __name__ == "__main__":
    main()