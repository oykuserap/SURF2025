"""
Enhanced JSON-based RAG System
Processes structured meeting data for better retrieval and analysis
"""
import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
from langchain.schema import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter

class JSONMeetingProcessor:
    def __init__(self, json_file: str = "./meetings.json"):
        self.json_file = Path(json_file)
        self.meetings_data = None
        self.load_meetings()
    
    def load_meetings(self):
        """Load meetings from JSON file"""
        if self.json_file.exists():
            with open(self.json_file, 'r', encoding='utf-8') as f:
                self.meetings_data = json.load(f)
        else:
            print(f"❌ JSON file not found: {self.json_file}")
            print("💡 Run convert_to_json.py first to create the JSON file")
    
    def create_documents_from_json(self) -> List[Document]:
        """Create LangChain documents from structured JSON data"""
        if not self.meetings_data:
            return []
        
        documents = []
        
        for meeting in self.meetings_data['meetings']:
            # Create a comprehensive document for each meeting
            doc_content = self.create_meeting_summary(meeting)
            
            # Enhanced metadata
            metadata = {
                'source': meeting['source_file'],
                'date': meeting['date'],
                'meeting_type': meeting['meeting_type'],
                'attendees_count': len(meeting['attendees']['present']),
                'item_count': meeting['item_count'],
                'financial_total': meeting['financial_total'],
                'keywords': meeting['keywords'],
                'has_financial_impact': meeting['financial_total'] is not None and meeting['financial_total'] > 0
            }
            
            documents.append(Document(
                page_content=doc_content,
                metadata=metadata
            ))
            
            # Also create separate documents for individual agenda items
            for item in meeting['agenda_items']:
                if item['title'] and len(item['title']) > 20:  # Only meaningful items
                    item_content = self.create_item_summary(item, meeting)
                    
                    item_metadata = {
                        'source': meeting['source_file'],
                        'date': meeting['date'],
                        'meeting_type': meeting['meeting_type'],
                        'item_number': item['item_number'],
                        'item_type': item['type'],
                        'financial_impact': item['financial_impact'],
                        'keywords': item['keywords'],
                        'is_agenda_item': True
                    }
                    
                    documents.append(Document(
                        page_content=item_content,
                        metadata=item_metadata
                    ))
        
        return documents
    
    def create_meeting_summary(self, meeting: Dict) -> str:
        """Create a comprehensive summary of a meeting"""
        summary = f"""
MEETING SUMMARY
Date: {meeting['date']}
Type: {meeting['meeting_type']}
Total Agenda Items: {meeting['item_count']}
"""
        
        if meeting['financial_total']:
            summary += f"Total Financial Impact: ${meeting['financial_total']:,.2f}\n"
        
        if meeting['attendees']['present']:
            summary += f"Attendees: {', '.join(meeting['attendees']['present'])}\n"
        
        if meeting['keywords']:
            summary += f"Key Topics: {', '.join(meeting['keywords'])}\n"
        
        summary += "\nAGENDA ITEMS:\n"
        for item in meeting['agenda_items']:
            summary += f"- {item['item_number']}: {item['title']}\n"
            if item['financial_impact'] is not None and item['financial_impact'] != 0:
                summary += f"  Financial Impact: ${item['financial_impact']:,.2f}\n"
            if item['keywords']:
                summary += f"  Keywords: {', '.join(item['keywords'])}\n"
        
        return summary
    
    def create_item_summary(self, item: Dict, meeting: Dict) -> str:
        """Create a focused summary for an agenda item"""
        summary = f"""
AGENDA ITEM {item['item_number']}
Meeting Date: {meeting['date']}
Meeting Type: {meeting['meeting_type']}
Item Type: {item['type']}
Title: {item['title']}
"""
        
        if item['financial_impact'] is not None and item['financial_impact'] != 0:
            summary += f"Financial Impact: ${item['financial_impact']:,.2f}\n"
        
        if item['keywords']:
            summary += f"Keywords: {', '.join(item['keywords'])}\n"
        
        return summary
    
    def search_by_criteria(self, 
                          date_range: Optional[tuple] = None,
                          meeting_type: Optional[str] = None,
                          keywords: Optional[List[str]] = None,
                          financial_threshold: Optional[float] = None,
                          attendee: Optional[str] = None) -> List[Dict]:
        """Search meetings by specific criteria"""
        if not self.meetings_data:
            return []
        
        results = []
        
        for meeting in self.meetings_data['meetings']:
            # Check date range
            if date_range and meeting['date']:
                if not (date_range[0] <= meeting['date'] <= date_range[1]):
                    continue
            
            # Check meeting type
            if meeting_type and meeting_type.lower() not in meeting['meeting_type'].lower():
                continue
            
            # Check keywords
            if keywords:
                meeting_keywords = meeting['keywords'] + [
                    kw for item in meeting['agenda_items'] 
                    for kw in item['keywords']
                ]
                if not any(kw.lower() in [mk.lower() for mk in meeting_keywords] for kw in keywords):
                    continue
            
            # Check financial threshold
            if financial_threshold and meeting['financial_total']:
                if meeting['financial_total'] < financial_threshold:
                    continue
            
            # Check attendee
            if attendee:
                attendees = meeting['attendees']['present']
                if not any(attendee.lower() in att.lower() for att in attendees):
                    continue
            
            results.append(meeting)
        
        return results
    
    def get_financial_summary(self) -> Dict:
        """Get financial summary across all meetings"""
        if not self.meetings_data:
            return {}
        
        total_financial = 0
        meeting_financials = []
        item_financials = []
        
        for meeting in self.meetings_data['meetings']:
            if meeting['financial_total']:
                total_financial += meeting['financial_total']
                meeting_financials.append({
                    'date': meeting['date'],
                    'type': meeting['meeting_type'],
                    'total': meeting['financial_total']
                })
            
            for item in meeting['agenda_items']:
                if item['financial_impact'] is not None and item['financial_impact'] != 0:
                    item_financials.append({
                        'date': meeting['date'],
                        'item': item['title'][:100],
                        'amount': item['financial_impact'],
                        'type': item['type']
                    })
        
        return {
            'total_financial_impact': total_financial,
            'meetings_with_financial_impact': len(meeting_financials),
            'items_with_financial_impact': len(item_financials),
            'largest_meeting_impact': max(meeting_financials, key=lambda x: x['total']) if meeting_financials else None,
            'largest_item_impact': max(item_financials, key=lambda x: x['amount']) if item_financials else None
        }
    
    def get_keyword_analysis(self) -> Dict:
        """Analyze keywords across all meetings"""
        if not self.meetings_data:
            return {}
        
        keyword_counts = {}
        
        for meeting in self.meetings_data['meetings']:
            # Count meeting-level keywords
            for keyword in meeting['keywords']:
                keyword_counts[keyword] = keyword_counts.get(keyword, 0) + 1
            
            # Count item-level keywords
            for item in meeting['agenda_items']:
                for keyword in item['keywords']:
                    keyword_counts[keyword] = keyword_counts.get(keyword, 0) + 1
        
        # Sort by frequency
        sorted_keywords = sorted(keyword_counts.items(), key=lambda x: x[1], reverse=True)
        
        return {
            'total_unique_keywords': len(keyword_counts),
            'most_common_keywords': sorted_keywords[:10],
            'keyword_distribution': dict(sorted_keywords)
        }


def update_process_docs():
    """Update the existing process_docs.py to use JSON data"""
    json_processor = JSONMeetingProcessor()
    
    if not json_processor.meetings_data:
        print("❌ No JSON data found. Run convert_to_json.py first.")
        return
    
    # Create documents from JSON
    documents = json_processor.create_documents_from_json()
    
    print(f"✅ Created {len(documents)} documents from JSON data")
    
    # Use existing chunking logic
    from langchain.text_splitter import RecursiveCharacterTextSplitter
    
    CHUNK_SIZE = 1000
    CHUNK_OVERLAP = 200
    
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        length_function=len,
        separators=["\n\n", "\n", ". ", " ", ""]
    )
    
    all_chunks = []
    for doc in documents:
        chunks = text_splitter.split_documents([doc])
        all_chunks.extend(chunks)
    
    print(f"✅ Created {len(all_chunks)} chunks from {len(documents)} documents")
    
    # Save chunks (same as existing process)
    chunks_path = Path("./chunks")
    chunks_path.mkdir(exist_ok=True)
    
    # Clear existing chunks
    for existing_chunk in chunks_path.glob("chunk_*.txt"):
        existing_chunk.unlink()
    
    for i, chunk in enumerate(all_chunks):
        chunk_content = f"# Chunk {i}\n"
        chunk_content += f"# Source: {chunk.metadata.get('source', 'unknown')}\n"
        chunk_content += f"# Date: {chunk.metadata.get('date', 'unknown')}\n"
        chunk_content += f"# Meeting Type: {chunk.metadata.get('meeting_type', 'unknown')}\n"
        chunk_content += f"# Keywords: {', '.join(chunk.metadata.get('keywords', []))}\n"
        
        # Handle financial impact with proper null checking
        financial_impact = chunk.metadata.get('financial_impact')
        if financial_impact is not None and financial_impact != 0:
            chunk_content += f"# Financial Impact: ${financial_impact:,.2f}\n"
        else:
            chunk_content += f"# Financial Impact: Not specified\n"
        
        chunk_content += f"# Size: {len(chunk.page_content)} characters\n\n"
        chunk_content += chunk.page_content
        
        (chunks_path / f"chunk_{i}.txt").write_text(chunk_content, encoding="utf-8")
    
    print(f"✅ Saved {len(all_chunks)} enhanced chunks to {chunks_path}")
    
    return all_chunks


if __name__ == "__main__":
    # Demonstrate the enhanced functionality
    processor = JSONMeetingProcessor()
    
    if processor.meetings_data:
        print("📊 Financial Summary:")
        financial_summary = processor.get_financial_summary()
        print(json.dumps(financial_summary, indent=2))
        
        print("\n📈 Keyword Analysis:")
        keyword_analysis = processor.get_keyword_analysis()
        print(f"Top 5 Keywords: {keyword_analysis['most_common_keywords'][:5]}")
        
        print("\n🔄 Updating document processing...")
        update_process_docs()
    else:
        print("❌ No JSON data found. Run convert_to_json.py first.")
