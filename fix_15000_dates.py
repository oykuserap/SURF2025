#!/usr/bin/env python3
"""
Fix agenda files with incorrect 15000xxx dates by re-extracting proper dates.
"""

import re
from pathlib import Path
from datetime import datetime
import shutil

def extract_proper_date_from_content(content: str) -> str:
    """Enhanced date extraction that avoids addresses and looks for meeting dates."""
    
    # Clean up the content - remove excessive whitespace and page breaks
    content = re.sub(r'-+ Page \d+ -+', '', content)
    content = re.sub(r'\s+', ' ', content)
    
    # Skip addresses like "1500 Marilla Street"
    content = re.sub(r'1500 Marilla Street', '', content, flags=re.IGNORECASE)
    
    # Date patterns to look for (in order of preference)
    date_patterns = [
        # Pattern 1: "February 8, 2024" 
        (r'([A-Z][a-z]+ \d{1,2}, \d{4})', '%B %d, %Y'),
        
        # Pattern 2: "January 13th, 2025" or "November 19th, 2024"
        (r'([A-Z][a-z]+ \d{1,2}(?:st|nd|rd|th)?, \d{4})', '%B %d, %Y'),
        
        # Pattern 3: Look for dates after meeting-related keywords
        (r'(?:meeting|committee|session|briefing).*?([A-Z][a-z]+ \d{1,2}(?:st|nd|rd|th)?, \d{4})', '%B %d, %Y'),
        
        # Pattern 4: "01/15/2024" or "1/15/24"
        (r'(\d{1,2}/\d{1,2}/\d{2,4})', None),
        
        # Pattern 5: "2024-01-15"
        (r'(\d{4}-\d{2}-\d{2})', '%Y-%m-%d'),
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
                    
                    # Only accept reasonable years (2020-2030)
                    if 2020 <= parsed_date.year <= 2030:
                        return parsed_date.strftime('%Y%m%d')
                    
                except ValueError:
                    continue
    
    return None

def categorize_meeting_type(content: str, filename: str) -> str:
    """Enhanced meeting type categorization."""
    content_upper = content.upper()
    
    # Check for specific patterns
    if any(term in content_upper for term in ["YOUTH COMMISSION", "YOUTH BOARD"]):
        return "youth"
    elif any(term in content_upper for term in ["AD HOC", "PENSION"]):
        return "committee"
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
    elif any(term in content_upper for term in ["BRIEFING"]):
        return "briefing"
    else:
        # Fall back to original type from filename
        parts = filename.split('_')
        if len(parts) > 2:
            return parts[-1].replace('.txt', '')
        return "meeting"

def main():
    agendas_dir = Path("/Users/serap/SURF2025/Agendas_COR")
    
    # Find all files with 15000xxx dates (clearly wrong)
    problem_files = list(agendas_dir.glob("agenda_15000*"))
    
    print(f"Found {len(problem_files)} files with incorrect 15000xxx dates")
    
    fixed_count = 0
    failed_files = []
    
    for file_path in problem_files:
        print(f"\nProcessing: {file_path.name}")
        
        try:
            # Read the file content
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Extract proper date
            extracted_date = extract_proper_date_from_content(content)
            
            if extracted_date:
                # Extract meeting type
                meeting_type = categorize_meeting_type(content, file_path.name)
                
                # Create new filename
                new_filename = f"agenda_{extracted_date}_{meeting_type}.txt"
                new_path = file_path.parent / new_filename
                
                # Check if target file already exists
                if new_path.exists():
                    print(f"   ⚠️  Target file already exists: {new_filename}")
                    # Add a suffix to make it unique
                    counter = 1
                    while new_path.exists():
                        new_filename = f"agenda_{extracted_date}_{meeting_type}_{counter:02d}.txt"
                        new_path = file_path.parent / new_filename
                        counter += 1
                
                # Rename the file
                shutil.move(str(file_path), str(new_path))
                print(f"   ✅ Renamed to: {new_filename}")
                print(f"   📅 Extracted date: {extracted_date}")
                print(f"   📋 Meeting type: {meeting_type}")
                
                fixed_count += 1
            else:
                print(f"   ❌ Could not extract proper date from content")
                failed_files.append(file_path.name)
                
                # Show some content for manual inspection
                lines = [line.strip() for line in content.split('\n')[:15] if line.strip()]
                print(f"   📄 Content sample:")
                for i, line in enumerate(lines[:5]):
                    print(f"      {i+1}: {line[:80]}")
        
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