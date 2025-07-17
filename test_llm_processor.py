"""
Test the LLM-based agenda processor on a few files first
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

class LLMAgendaProcessorTest:
    def __init__(self):
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.source_dir = Path("./Agendas_COR")
        self.output_file = Path("./meetings_llm_test.json")
        
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
    
    def test_processing(self, num_files: int = 3):
        """Test processing on a few files."""
        print(f"🧪 Testing LLM-based processing on {num_files} files...")
        
        files = list(self.source_dir.glob("*.txt"))[:num_files]
        print(f"📁 Testing with: {[f.name for f in files]}")
        
        meetings = []
        
        for i, file_path in enumerate(files, 1):
            print(f"🔄 Processing {file_path.name} ({i}/{len(files)})")
            
            try:
                # Read file content
                with open(file_path, 'r', encoding='utf-8') as f:
                    text = f.read()
                
                # Extract meeting info using LLM
                meeting_data = self.extract_meeting_info(text, file_path.name)
                
                if not meeting_data.get('processing_error'):
                    print(f"✅ Successfully processed {file_path.name}")
                    print(f"   📅 Date: {meeting_data.get('meeting_date', 'N/A')}")
                    print(f"   🏛️ Type: {meeting_data.get('meeting_type', 'N/A')}")
                    print(f"   👥 Attendees: {len(meeting_data.get('attendees', []))}")
                    print(f"   📋 Agenda items: {len(meeting_data.get('agenda_items', []))}")
                    print(f"   🏷️ Keywords: {len(meeting_data.get('keywords', []))}")
                else:
                    print(f"⚠️  Processing failed for {file_path.name}")
                
                meetings.append(meeting_data)
                
                # Add small delay to avoid rate limiting
                time.sleep(1)
                
            except Exception as e:
                print(f"❌ Error reading {file_path.name}: {e}")
                meetings.append(self.create_fallback_structure(file_path.name))
        
        # Save test results
        result = {
            "metadata": {
                "test_run": True,
                "total_files": len(files),
                "processing_date": datetime.now().isoformat(),
                "method": "LLM-based extraction"
            },
            "meetings": meetings
        }
        
        with open(self.output_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        
        print(f"💾 Test results saved to {self.output_file}")
        return result

def main():
    """Test the LLM-based processing."""
    processor = LLMAgendaProcessorTest()
    
    # Test on 3 files first
    processor.test_processing(3)
    
    print("🎉 LLM-based test complete!")

if __name__ == "__main__":
    main()
