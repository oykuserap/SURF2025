"""
LLM-based JSON converter for City of Richardson council meeting documents
Uses OpenAI to extract structured information from agenda text files
"""
import os
import json
import time
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
import re

from openai import OpenAI
from settings import settings

class LLMAgendaProcessor:
    def __init__(self):
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.source_dir = Path("./Agendas_COR")
        self.output_file = Path("./meetings_llm.json")
        
    def extract_meeting_info(self, text: str, filename: str) -> Dict[str, Any]:
        """Use LLM to extract structured information from meeting text."""
        
        # Clean the text a bit for better LLM processing
        text = re.sub(r'-{10,}.*?-{10,}', '', text)  # Remove page separators
        text = re.sub(r'\s+', ' ', text)  # Normalize whitespace
        
        # Truncate if too long (OpenAI has token limits)
        if len(text) > 12000:  # Rough character limit
            text = text[:12000] + "..."
            
        prompt = f"""
You are an expert at analyzing municipal government meeting documents. Please extract the following information from this agenda text and format it as JSON:

REQUIRED FIELDS:
1. meeting_date: The date of the meeting (YYYY-MM-DD format, or null if not found)
2. meeting_type: Type of meeting (e.g., "City Council Meeting", "Planning Commission", "Landmark Commission", etc.)
3. attendees: List of people who attended or were expected to attend
4. agenda_items: List of agenda items, each with:
   - item_number: The agenda item number
   - title: The title/description of the item
   - type: The type of item (e.g., "regular", "consent", "public_hearing", "ordinance")
5. keywords: List of relevant keywords/topics discussed (e.g., "zoning", "budget", "infrastructure", "housing", etc.)

INSTRUCTIONS:
- Be thorough but concise
- Only include information that is clearly present in the text
- If information is not available, use null or empty array as appropriate
- For agenda items, focus on the main substantive items, not procedural ones
- For keywords, extract the main topics/themes discussed

TEXT TO ANALYZE:
{text}

SOURCE FILE: {filename}

Please respond with ONLY the JSON object, no additional text:
"""

        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are an expert at extracting structured information from municipal government documents. Always respond with valid JSON only."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1500,
                temperature=0.1
            )
            
            response_text = response.choices[0].message.content.strip()
            
            # Try to parse the JSON response
            try:
                meeting_data = json.loads(response_text)
                
                # Add metadata
                meeting_data['source_file'] = filename
                meeting_data['processed_date'] = datetime.now().isoformat()
                
                return meeting_data
                
            except json.JSONDecodeError as e:
                print(f"⚠️  JSON parsing error for {filename}: {e}")
                print(f"Response was: {response_text[:500]}...")
                return self.create_fallback_structure(filename)
                
        except Exception as e:
            print(f"❌ Error processing {filename}: {e}")
            return self.create_fallback_structure(filename)
    
    def create_fallback_structure(self, filename: str) -> Dict[str, Any]:
        """Create a fallback structure if LLM processing fails."""
        return {
            "source_file": filename,
            "meeting_date": None,
            "meeting_type": "Unknown",
            "attendees": [],
            "agenda_items": [],
            "keywords": [],
            "processed_date": datetime.now().isoformat(),
            "processing_error": True
        }
    
    def process_all_files(self) -> Dict[str, Any]:
        """Process all agenda files and create JSON structure."""
        print("🔄 Starting LLM-based agenda processing...")
        
        if not self.source_dir.exists():
            print(f"❌ Source directory {self.source_dir} not found!")
            return {"meetings": [], "metadata": {}}
        
        files = list(self.source_dir.glob("*.txt"))
        print(f"📁 Found {len(files)} agenda files")
        
        meetings = []
        successful_count = 0
        
        for i, file_path in enumerate(files, 1):
            print(f"🔄 Processing {file_path.name} ({i}/{len(files)})")
            
            try:
                # Read file content
                with open(file_path, 'r', encoding='utf-8') as f:
                    text = f.read()
                
                # Extract meeting info using LLM
                meeting_data = self.extract_meeting_info(text, file_path.name)
                
                if not meeting_data.get('processing_error'):
                    successful_count += 1
                    print(f"✅ Successfully processed {file_path.name}")
                else:
                    print(f"⚠️  Partial processing for {file_path.name}")
                
                meetings.append(meeting_data)
                
                # Add small delay to avoid rate limiting
                time.sleep(0.5)
                
            except Exception as e:
                print(f"❌ Error reading {file_path.name}: {e}")
                meetings.append(self.create_fallback_structure(file_path.name))
        
        # Create final structure
        result = {
            "metadata": {
                "total_files": len(files),
                "successful_processing": successful_count,
                "processing_date": datetime.now().isoformat(),
                "source_directory": str(self.source_dir),
                "method": "LLM-based extraction"
            },
            "meetings": meetings
        }
        
        print(f"📊 Processing complete: {successful_count}/{len(files)} files processed successfully")
        return result
    
    def save_to_json(self, data: Dict[str, Any]) -> None:
        """Save the processed data to JSON file."""
        try:
            with open(self.output_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print(f"💾 Saved to {self.output_file}")
            
            # Print summary
            meetings = data.get('meetings', [])
            total_agenda_items = sum(len(m.get('agenda_items', [])) for m in meetings)
            
            print(f"\n📊 Summary:")
            print(f"- Total meetings: {len(meetings)}")
            print(f"- Total agenda items: {total_agenda_items}")
            print(f"- Average items per meeting: {total_agenda_items/len(meetings):.1f}")
            
        except Exception as e:
            print(f"❌ Error saving JSON: {e}")

def main():
    """Main function to run the LLM-based processing."""
    processor = LLMAgendaProcessor()
    
    # Process all files
    data = processor.process_all_files()
    
    # Save to JSON
    processor.save_to_json(data)
    
    print("🎉 LLM-based agenda processing complete!")

if __name__ == "__main__":
    main()
