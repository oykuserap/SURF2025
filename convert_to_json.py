"""
Text to JSON Converter for City Council Meetings
Converts raw text agenda files to structured JSON format
"""
import json
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AgendaParser:
    def __init__(self, input_dir: str = "./Agendas_COR", output_file: str = "./meetings.json"):
        self.input_dir = Path(input_dir)
        self.output_file = Path(output_file)
        self.meetings = []
        
    def extract_date(self, text: str) -> Optional[str]:
        """Extract date from agenda text"""
        date_patterns = [
            r'(\w+\s+\d{1,2},\s+\d{4})',  # April 9, 2025
            r'(\d{4}\s+\w+\s+\d{1,2})',   # 2025 APR 2
            r'(\w+\s+\d{1,2},\s+\d{4})',  # April 7, 2025
        ]
        
        for pattern in date_patterns:
            matches = re.findall(pattern, text[:500])  # Check first 500 chars
            if matches:
                try:
                    # Try to parse the date
                    date_str = matches[0]
                    # Handle different formats
                    if 'APR' in date_str:
                        date_str = date_str.replace('APR', 'April').replace('-', ' ')
                    
                    # Try to parse with different formats
                    for fmt in ['%B %d, %Y', '%Y %B %d', '%B %d %Y']:
                        try:
                            parsed_date = datetime.strptime(date_str, fmt)
                            return parsed_date.strftime('%Y-%m-%d')
                        except ValueError:
                            continue
                except:
                    continue
        
        return None
    
    def extract_meeting_type(self, text: str) -> str:
        """Extract meeting type from agenda text"""
        text_upper = text.upper()
        
        if 'LANDMARK COMMISSION' in text_upper:
            return 'Landmark Commission Meeting'
        elif 'PARK AND RECREATION' in text_upper or 'PARKS BOARD' in text_upper:
            return 'Parks and Recreation Board Meeting'
        elif 'COMMUNITY DEVELOPMENT' in text_upper:
            return 'Community Development Commission Meeting'
        elif 'BRIEFING' in text_upper:
            return 'Council Briefing Meeting'
        elif 'COUNCIL AGENDA' in text_upper:
            return 'Regular Council Meeting'
        else:
            return 'Council Meeting'
    
    def extract_attendees(self, text: str) -> Dict[str, List[str]]:
        """Extract attendees from agenda text"""
        attendees = {"present": [], "absent": [], "staff": []}
        
        # Look for attendee patterns
        attendee_patterns = [
            r'PRESENT[:\s]+(.+?)(?=ABSENT|STAFF|$)',
            r'MEMBERS PRESENT[:\s]+(.+?)(?=ABSENT|STAFF|$)',
            r'COMMISSIONERS PRESENT[:\s]+(.+?)(?=ABSENT|STAFF|$)',
        ]
        
        for pattern in attendee_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE | re.DOTALL)
            if matches:
                # Parse names from the match
                names_text = matches[0]
                # Split by common delimiters
                names = re.split(r'[,;\n]+', names_text)
                for name in names:
                    name = name.strip()
                    if name and len(name) > 2:
                        attendees["present"].append(name)
        
        return attendees
    
    def extract_agenda_items(self, text: str) -> List[Dict[str, Any]]:
        """Extract agenda items from text"""
        items = []
        
        # Look for numbered items or consent agenda items
        item_patterns = [
            r'(\d+)\.\s*([^\n]+)',  # 1. Item description
            r'Item\s+(\d+)[:\s]+([^\n]+)',  # Item 1: Description
            r'([A-Z]+\s+AGENDA)[:\s]*(.+?)(?=\n\n|\Z)',  # CONSENT AGENDA: items
        ]
        
        item_counter = 1
        for pattern in item_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE | re.DOTALL)
            for match in matches:
                if len(match) == 2:
                    number, description = match
                    
                    # Extract financial information
                    financial_amount = self.extract_financial_amount(description)
                    
                    # Determine item type
                    item_type = self.classify_item_type(description)
                    
                    # Extract keywords
                    keywords = self.extract_keywords(description)
                    
                    items.append({
                        "item_number": str(number) if number.isdigit() else str(item_counter),
                        "title": description.strip()[:200],  # Limit length
                        "type": item_type,
                        "financial_impact": financial_amount,
                        "keywords": keywords
                    })
                    
                    item_counter += 1
        
        return items
    
    def extract_agenda_items_improved(self, text: str) -> List[Dict[str, Any]]:
        """Improved extraction of agenda items with better context awareness"""
        items = []
        
        # More specific patterns for actual agenda items
        item_patterns = [
            # Standard agenda items (1. Description, 2. Description, etc.)
            r'^\s*(\d+)\.\s+(.+?)(?=^\s*\d+\.|$)',
            # Items with prefixes like "Item 1:", "A-1:", etc.
            r'^\s*(?:Item\s+)?([A-Z]?-?\d+)[:\s]+(.+?)(?=^\s*(?:Item\s+)?[A-Z]?-?\d+[:\s]|$)',
            # Resolution/Ordinance items (24-1234 format)
            r'^\s*(\d{2}-\d{4})\s+(.+?)(?=^\s*\d{2}-\d{4}|$)',
        ]
        
        item_counter = 1
        
        for pattern in item_patterns:
            matches = re.findall(pattern, text, re.MULTILINE | re.DOTALL)
            for match in matches:
                if len(match) == 2:
                    number, description = match
                    
                    # Clean up description
                    description = ' '.join(description.split())  # Normalize whitespace
                    
                    # Skip if description is too short or looks like a fragment
                    if len(description.strip()) < 10:
                        continue
                    
                    # Skip if it's just numbers/sections (like "2, 28-130.5, 28-130.12")
                    if re.match(r'^[\d\s,.-]+$', description.strip()):
                        continue
                    
                    # Extract financial information
                    financial_amount = self.extract_financial_amount(description)
                    
                    # Determine item type
                    item_type = self.classify_item_type(description)
                    
                    # Extract keywords
                    keywords = self.extract_keywords(description)
                    
                    items.append({
                        "item_number": str(number),
                        "title": description.strip()[:500],  # Longer limit for full context
                        "type": item_type,
                        "financial_impact": financial_amount,
                        "keywords": keywords
                    })
                    
                    item_counter += 1
        
        return items

    def extract_financial_amount(self, text: str) -> Optional[float]:
        """Extract financial amounts from text"""
        # Look for dollar amounts
        money_patterns = [
            r'\$[\d,]+\.?\d*',
            r'(\d+,?\d+)\s*dollars?',
            r'amount.*?(\d+,?\d+)',
        ]
        
        for pattern in money_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                try:
                    amount_str = matches[0].replace('$', '').replace(',', '')
                    return float(amount_str)
                except:
                    continue
        
        return None
    
    def classify_item_type(self, text: str) -> str:
        """Classify agenda item type"""
        text_lower = text.lower()
        
        if 'consent' in text_lower:
            return 'consent'
        elif 'public hearing' in text_lower:
            return 'public_hearing'
        elif 'ordinance' in text_lower:
            return 'ordinance'
        elif 'resolution' in text_lower:
            return 'resolution'
        elif 'contract' in text_lower:
            return 'contract'
        elif 'budget' in text_lower:
            return 'budget'
        else:
            return 'regular'
    
    def extract_keywords(self, text: str) -> List[str]:
        """Extract keywords from text"""
        keywords = []
        
        # Define keyword categories
        keyword_categories = {
            'budget': ['budget', 'funding', 'appropriation', 'financial', 'cost', 'revenue'],
            'infrastructure': ['infrastructure', 'construction', 'repair', 'maintenance', 'facility'],
            'zoning': ['zoning', 'development', 'land use', 'permit', 'variance'],
            'public_safety': ['police', 'fire', 'emergency', 'safety', 'security'],
            'transportation': ['transportation', 'traffic', 'street', 'road', 'transit'],
            'parks': ['park', 'recreation', 'facility', 'sports', 'playground'],
            'housing': ['housing', 'residential', 'affordable', 'development'],
            'environment': ['environment', 'sustainability', 'green', 'pollution'],
            'economic': ['economic', 'development', 'business', 'commerce', 'jobs'],
            'governance': ['ordinance', 'policy', 'regulation', 'compliance'],
        }
        
        text_lower = text.lower()
        
        for category, terms in keyword_categories.items():
            if any(term in text_lower for term in terms):
                keywords.append(category)
        
        return list(set(keywords))  # Remove duplicates
    
    def parse_file(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """Parse a single agenda file"""
        try:
            logger.info(f"Parsing file: {file_path.name}")
            
            text = file_path.read_text(encoding='utf-8', errors='ignore')
            
            # Extract information
            date = self.extract_date(text)
            meeting_type = self.extract_meeting_type(text)
            attendees = self.extract_attendees(text)
            agenda_items = self.extract_agenda_items_improved(text)
            
            # Extract overall keywords
            overall_keywords = self.extract_keywords(text)
            
            # Calculate total financial impact
            total_financial = sum(
                item['financial_impact'] for item in agenda_items 
                if item['financial_impact'] is not None
            )
            
            meeting_data = {
                "source_file": str(file_path.name),
                "date": date,
                "meeting_type": meeting_type,
                "attendees": attendees,
                "agenda_items": agenda_items,
                "full_text": text,
                "keywords": overall_keywords,
                "financial_total": total_financial if total_financial > 0 else None,
                "item_count": len(agenda_items),
                "parsed_at": datetime.now().isoformat()
            }
            
            return meeting_data
            
        except Exception as e:
            logger.error(f"Error parsing {file_path.name}: {e}")
            return None
    
    def convert_all_files(self):
        """Convert all text files to JSON"""
        logger.info(f"Starting conversion of files in {self.input_dir}")
        
        # Find all text files
        text_files = list(self.input_dir.glob("*.txt"))
        logger.info(f"Found {len(text_files)} text files")
        
        # Process each file
        for file_path in text_files:
            meeting_data = self.parse_file(file_path)
            if meeting_data:
                self.meetings.append(meeting_data)
        
        # Create final JSON structure
        output_data = {
            "metadata": {
                "total_meetings": len(self.meetings),
                "conversion_date": datetime.now().isoformat(),
                "source_directory": str(self.input_dir)
            },
            "meetings": self.meetings
        }
        
        # Save to JSON file
        with open(self.output_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Conversion complete! Saved {len(self.meetings)} meetings to {self.output_file}")
        
        # Print summary
        self.print_summary()
    
    def print_summary(self):
        """Print conversion summary"""
        print("\n" + "="*50)
        print("CONVERSION SUMMARY")
        print("="*50)
        print(f"Total meetings processed: {len(self.meetings)}")
        
        # Meeting types
        meeting_types = {}
        dates = []
        total_items = 0
        total_financial = 0
        
        for meeting in self.meetings:
            # Count meeting types
            meeting_type = meeting['meeting_type']
            meeting_types[meeting_type] = meeting_types.get(meeting_type, 0) + 1
            
            # Collect dates
            if meeting['date']:
                dates.append(meeting['date'])
            
            # Count items
            total_items += meeting['item_count']
            
            # Sum financial
            if meeting['financial_total']:
                total_financial += meeting['financial_total']
        
        print(f"Total agenda items: {total_items}")
        print(f"Total financial impact: ${total_financial:,.2f}")
        
        print(f"\nMeeting types:")
        for meeting_type, count in meeting_types.items():
            print(f"  - {meeting_type}: {count}")
        
        if dates:
            print(f"\nDate range: {min(dates)} to {max(dates)}")
        
        print(f"\nJSON file saved: {self.output_file}")
        print("="*50)


def main():
    """Main conversion function"""
    parser = AgendaParser()
    parser.convert_all_files()
    
    print("\n🎉 Conversion complete!")
    print("📄 Your meetings are now in structured JSON format")
    print("🔍 You can now easily search by date, attendees, keywords, and more!")


if __name__ == "__main__":
    main()
