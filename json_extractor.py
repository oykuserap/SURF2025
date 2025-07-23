"""
JSON Data Extractor for agenda text files.
Extracts structured data (date, attendees, agenda items, keywords) from meeting agendas.
"""
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
from openai import OpenAI
import json

from config import OPENAI_API_KEY, OPENAI_MODEL, AGENDAS_DIR, OUTPUT_DIR
from utils import setup_logging, clean_text, save_json, get_agenda_files, extract_agenda_number, extract_meeting_date, extract_meeting_type

logger = setup_logging()

class JSONExtractor:
    """Extract structured data from agenda text files using OpenAI."""
    
    def __init__(self):
        self.client = OpenAI(api_key=OPENAI_API_KEY)
        self.output_dir = OUTPUT_DIR / "json_data"
        
    def create_extraction_prompt(self, text: str) -> str:
        """Create a prompt for extracting structured data."""
        return f"""
Please extract the following structured information from this meeting agenda and return it as valid JSON:

{{
  "meeting_info": {{
    "date": "meeting date (e.g., 'March 28, 2025')",
    "time": "meeting time if specified",
    "type": "type of meeting (e.g., 'Special Called Meeting', 'Regular Meeting')",
    "organization": "name of the organizing body/committee",
    "location": "meeting location (physical and/or virtual)"
  }},
  "attendees": {{
    "chair": "name of the chair/president if mentioned",
    "presenters": ["list of presenters mentioned"],
    "participants": ["other key participants mentioned"]
  }},
  "agenda_items": [
    {{
      "item_number": "agenda item number",
      "title": "brief title of the item",
      "description": "detailed description",
      "presenter": "who is presenting this item",
      "action_required": "what action is needed (approve, discuss, etc.)"
    }}
  ],
  "keywords": ["list of 10-15 important keywords/topics from the meeting"],
  "financial_items": [
    {{
      "description": "description of financial item",
      "amount": "dollar amount if specified",
      "type": "budget/funding/expenditure/etc."
    }}
  ]
}}

Be thorough but accurate. If information is not available, use null or empty arrays as appropriate.

AGENDA TEXT:
{text}

JSON RESPONSE:
"""

    def extract_structured_data(self, text: str) -> Dict[str, Any]:
        """Extract structured data using OpenAI API."""
        try:
            cleaned_text = clean_text(text)
            prompt = self.create_extraction_prompt(cleaned_text)
            
            response = self.client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": "You are an expert at extracting structured data from government meeting agendas. Always return valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1500,
                temperature=0.1
            )
            
            # Parse the JSON response
            json_text = response.choices[0].message.content.strip()
            
            # Clean up the JSON text if needed
            if json_text.startswith('```json'):
                json_text = json_text.replace('```json', '').replace('```', '').strip()
            
            return json.loads(json_text)
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing error: {e}")
            return self.create_fallback_data(text)
        except Exception as e:
            logger.error(f"Error extracting data: {e}")
            return self.create_fallback_data(text)

    def create_fallback_data(self, text: str) -> Dict[str, Any]:
        """Create fallback structured data using basic text processing."""
        return {
            "meeting_info": {
                "date": extract_meeting_date(text),
                "time": None,
                "type": extract_meeting_type(text),
                "organization": self.extract_organization(text),
                "location": "Dallas City Hall"
            },
            "attendees": {
                "chair": None,
                "presenters": [],
                "participants": []
            },
            "agenda_items": self.extract_basic_agenda_items(text),
            "keywords": self.extract_basic_keywords(text),
            "financial_items": []
        }

    def extract_organization(self, text: str) -> str:
        """Extract organization name from text."""
        patterns = [
            r'([A-Z][A-Z\s]+(?:COMMISSION|BOARD|COMMITTEE|DISTRICT))',
            r'(TIF.*?DISTRICT)',
            r'(LANDMARK COMMISSION)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text.upper())
            if match:
                return match.group(1).title()
        
        return "City of Dallas"

    def extract_basic_agenda_items(self, text: str) -> List[Dict[str, Any]]:
        """Extract basic agenda items using regex."""
        items = []
        
        # Look for numbered items
        pattern = r'(\d+)\.\s+([^0-9]+?)(?=\d+\.|$)'
        matches = re.findall(pattern, text, re.DOTALL)
        
        for item_num, content in matches:
            content = content.strip()
            if len(content) > 10:  # Filter out very short items
                items.append({
                    "item_number": item_num,
                    "title": content[:100] + "..." if len(content) > 100 else content,
                    "description": content,
                    "presenter": None,
                    "action_required": "Review" if "review" in content.lower() else "Action"
                })
        
        return items

    def extract_basic_keywords(self, text: str) -> List[str]:
        """Extract basic keywords from text."""
        # Common important terms in city meetings
        keywords = []
        text_upper = text.upper()
        
        keyword_patterns = [
            'TIF', 'DISTRICT', 'BUDGET', 'FUNDING', 'APPROVAL', 'RECOMMENDATION',
            'PUBLIC', 'DEVELOPMENT', 'IMPROVEMENT', 'TRANSPORTATION', 'PLANNING',
            'ZONING', 'ORDINANCE', 'RESOLUTION', 'CONTRACT', 'AGREEMENT'
        ]
        
        for keyword in keyword_patterns:
            if keyword in text_upper:
                keywords.append(keyword.lower())
        
        return keywords[:10]  # Limit to 10 keywords

    def process_agenda_file(self, file_path: Path) -> Dict[str, Any]:
        """Process a single agenda file and extract JSON data."""
        logger.info(f"Extracting data from {file_path.name}")
        
        try:
            # Read the agenda file
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Extract structured data
            extracted_data = self.extract_structured_data(content)
            
            # Add metadata
            agenda_number = extract_agenda_number(file_path)
            output_data = {
                "agenda_number": agenda_number,
                "source_file": file_path.name,
                "extracted_data": extracted_data,
                "extraction_method": "openai_gpt",
                "original_length": len(content)
            }
            
            # Save JSON data
            output_file = self.output_dir / f"data_{agenda_number}.json"
            save_json(output_data, output_file)
            
            logger.info(f"Data extracted and saved for {file_path.name}")
            return output_data
            
        except Exception as e:
            logger.error(f"Error processing {file_path.name}: {e}")
            return {"error": str(e), "file": file_path.name}

    def get_already_processed_files(self) -> set:
        """Get set of agenda numbers that have already been processed."""
        processed = set()
        
        # Check existing JSON data files
        for json_file in self.output_dir.glob("data_*.json"):
            try:
                with open(json_file, 'r') as f:
                    data = json.load(f)
                    if "error" not in data and data.get("agenda_number"):
                        processed.add(data["agenda_number"])
            except:
                continue
                
        return processed

    def process_all_agendas(self, limit: int = None) -> List[Dict[str, Any]]:
        """Process all agenda files and extract JSON data with resume capability."""
        all_agenda_files = get_agenda_files(AGENDAS_DIR)
        
        # Filter out already processed files
        already_processed = self.get_already_processed_files()
        agenda_files = []
        
        for file_path in all_agenda_files:
            agenda_number = extract_agenda_number(file_path)
            if agenda_number not in already_processed:
                agenda_files.append(file_path)
        
        if limit:
            agenda_files = agenda_files[:limit]
        
        print(f"\n🔍 Found {len(all_agenda_files)} total agenda files")
        print(f"📋 {len(already_processed)} already processed")
        print(f"🆕 {len(agenda_files)} new files to process")
        
        if len(agenda_files) == 0:
            print("✅ All files already processed!")
            return []
            
        logger.info(f"Extracting data from {len(agenda_files)} new agenda files")
        
        results = []
        successful = 0
        failed = 0
        batch_size = 10
        
        # Process in batches of 10 with progress saving
        for i in range(0, len(agenda_files), batch_size):
            batch = agenda_files[i:i + batch_size]
            batch_num = (i // batch_size) + 1
            total_batches = (len(agenda_files) + batch_size - 1) // batch_size
            
            print(f"\n📦 Processing Batch {batch_num}/{total_batches} ({len(batch)} files)")
            print("=" * 60)
            
            batch_successful = 0
            batch_failed = 0
            
            for j, file_path in enumerate(batch, 1):
                print(f"📊 [{j}/{len(batch)}] Extracting data from {file_path.name}...")
                
                result = self.process_agenda_file(file_path)
                results.append(result)
                
                if "error" not in result:
                    successful += 1
                    batch_successful += 1
                    print(f"   ✅ Data extracted and saved")
                else:
                    failed += 1
                    batch_failed += 1
                    print(f"   ❌ Failed: {result.get('error', 'Unknown error')}")
            
            print(f"\n📦 Batch {batch_num} complete: ✅ {batch_successful} successful, ❌ {batch_failed} failed")
            print(f"📊 Overall progress: {successful + failed}/{len(agenda_files)} new files processed")
        
        # Save overall results
        results_file = self.output_dir / "extraction_results.json"
        save_json({
            "total_files_found": len(all_agenda_files),
            "already_processed": len(already_processed),
            "new_files_processed": len(agenda_files),
            "successful": successful,
            "failed": failed,
            "results": results
        }, results_file)
        
        print(f"\n🎉 JSON extraction complete!")
        print(f"   ✅ Total successful: {successful}")
        print(f"   ❌ Total failed: {failed}")
        print(f"   📋 Total in database: {len(already_processed) + successful}")
        
        logger.info(f"Data extraction complete. Results saved to {results_file}")
        return results

def main():
    """Main function to run JSON extraction."""
    extractor = JSONExtractor()
    
    # Process first 5 files as a test
    print("Extracting structured data from agenda files...")
    results = extractor.process_all_agendas(limit=5)
    
    successful = len([r for r in results if "error" not in r])
    failed = len([r for r in results if "error" in r])
    
    print(f"\nJSON Extraction Complete!")
    print(f"✅ Successful: {successful}")
    print(f"❌ Failed: {failed}")
    
    if successful > 0:
        print(f"\nStructured data saved in: {OUTPUT_DIR / 'json_data'}")

if __name__ == "__main__":
    main()
