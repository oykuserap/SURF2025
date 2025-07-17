"""
Enhanced JSON-based embedding system for better chatbot performance
"""
import os
# Disable ChromaDB telemetry
os.environ["CHROMA_TELEMETRY_ENABLED"] = "false"
os.environ["ANONYMIZED_TELEMETRY"] = "false"

import json
from pathlib import Path
from typing import List
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
from langchain.schema import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
import tiktoken
from settings import settings

JSON_PATH = Path("./meetings.json")
CHUNKS_PATH = Path("./chunks")


def load_json_chunks():
    """Load chunks from JSON structure with enhanced metadata."""
    if not JSON_PATH.exists():
        print(f"❌ JSON file not found at {JSON_PATH}")
        print("💡 Run convert_to_json.py first to create the JSON structure")
        return []
    
    docs = []
    
    with open(JSON_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print(f"📊 Found {len(data['meetings'])} meetings in JSON")
    
    for meeting in data['meetings']:
        # Create chunks for different parts of the meeting
        meeting_date = meeting['date'] or "Date not specified"
        meeting_type = meeting['meeting_type']
        
        # Handle attendees structure
        attendees_data = meeting.get('attendees', {})
        if isinstance(attendees_data, dict):
            all_attendees = []
            all_attendees.extend(attendees_data.get('present', []))
            all_attendees.extend(attendees_data.get('staff', []))
            attendees = all_attendees
        else:
            attendees = attendees_data or []
        
        # 1. Meeting Overview Chunk
        overview_content = f"""
Meeting Date: {meeting_date}
Meeting Type: {meeting_type}
Attendees: {', '.join(attendees)}
Total Agenda Items: {len(meeting['agenda_items'])}
Keywords: {', '.join(meeting.get('keywords', []))}
Financial Impact: ${meeting.get('financial_total', 0) or 0:,}
"""
        
        overview_metadata = {
            "source": f"Meeting_{meeting_date}",
            "chunk_type": "overview",
            "date": meeting_date,
            "meeting_type": meeting_type,
            "attendees": ", ".join(attendees),
            "keywords": ", ".join(meeting.get('keywords', [])),
            "financial_total": meeting.get('financial_total', 0) or 0
        }
        
        docs.append(Document(page_content=overview_content, metadata=overview_metadata))
        
        # 2. Individual Agenda Item Chunks
        for item in meeting['agenda_items']:
            item_content = f"""
Date: {meeting_date}
Agenda Item #{item['item_number']}: {item['title']}
Type: {item['type']}
Financial Impact: ${item.get('financial_impact', 0) or 0:,}
Keywords: {', '.join(item.get('keywords', []))}
"""
            
            item_metadata = {
                "source": f"Meeting_{meeting_date}_Item_{item['item_number']}",
                "chunk_type": "agenda_item",
                "date": meeting_date,
                "meeting_type": meeting_type,
                "item_number": item['item_number'],
                "item_title": item['title'],
                "item_type": item['type'],
                "financial_impact": item.get('financial_impact', 0) or 0,
                "keywords": ", ".join(item.get('keywords', [])),
                "attendees": ", ".join(attendees)
            }
            
            docs.append(Document(page_content=item_content, metadata=item_metadata))
        
        # 3. Full Meeting Content Chunk (for comprehensive searches)
        if meeting.get('full_text'):
            full_content = f"""
Complete Meeting Content - {meeting_date}
Meeting Type: {meeting_type}
Attendees: {', '.join(attendees)}

{meeting['full_text']}
"""
            
            full_metadata = {
                "source": f"Meeting_{meeting_date}_Full",
                "chunk_type": "full_meeting",
                "date": meeting_date,
                "meeting_type": meeting_type,
                "attendees": ", ".join(attendees),
                "keywords": ", ".join(meeting.get('keywords', [])),
                "financial_total": meeting.get('financial_total', 0) or 0
            }
            
            docs.append(Document(page_content=full_content, metadata=full_metadata))
    
    print(f"✅ Created {len(docs)} structured chunks from JSON")
    return docs


def count_tokens(text: str) -> int:
    """Count tokens in text using tiktoken"""
    encoding = tiktoken.encoding_for_model("text-embedding-3-small")
    return len(encoding.encode(text))


def chunk_large_documents(docs: List[Document], max_tokens: int = 6000) -> List[Document]:
    """Split large documents into smaller chunks to avoid token limits"""
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=4000,  # Characters, not tokens
        chunk_overlap=200,
        length_function=len,
        separators=["\n\n", "\n", ". ", " ", ""]
    )
    
    chunked_docs = []
    for doc in docs:
        token_count = count_tokens(doc.page_content)
        
        if token_count > max_tokens:
            print(f"⚠️  Large document detected: {token_count} tokens, splitting...")
            
            # Split the document
            split_docs = text_splitter.split_documents([doc])
            
            # Update metadata for each chunk
            for i, split_doc in enumerate(split_docs):
                split_doc.metadata.update(doc.metadata)
                split_doc.metadata["chunk_part"] = f"{i+1}_of_{len(split_docs)}"
                chunked_docs.append(split_doc)
        else:
            chunked_docs.append(doc)
    
    return chunked_docs


def embed_json():
    """Load JSON chunks and create embeddings in vector database."""
    print("🔄 Loading structured chunks from JSON...")
    docs = load_json_chunks()
    
    if not docs:
        print("❌ No chunks found! Run convert_to_json.py first.")
        return
    
    # Chunk large documents
    docs = chunk_large_documents(docs)
    
    print(f"📊 Embedding {len(docs)} structured chunks...")
    
    # Calculate statistics
    total_chars = sum(len(doc.page_content) for doc in docs)
    avg_chunk_size = total_chars / len(docs) if docs else 0
    
    # Count chunk types
    chunk_types = {}
    for doc in docs:
        chunk_type = doc.metadata.get('chunk_type', 'unknown')
        chunk_types[chunk_type] = chunk_types.get(chunk_type, 0) + 1
    
    print(f"- Total characters to embed: {total_chars:,}")
    print(f"- Average chunk size: {avg_chunk_size:.0f} characters")
    print(f"- Chunk types: {chunk_types}")
    
    # Split large documents to avoid token limits
    print("\n📦 Processing large documents...")
    chunked_docs = chunk_large_documents(docs)
    if len(chunked_docs) > len(docs):
        print(f"📦 Split {len(docs)} documents into {len(chunked_docs)} chunks")
    
    try:
        embedder = OpenAIEmbeddings(model=settings.EMBEDDING_MODEL)
        
        # Process in smaller batches to avoid hitting token limits
        batch_size = 50  # Process 50 documents at a time
        all_processed = []
        
        for i in range(0, len(chunked_docs), batch_size):
            batch = chunked_docs[i:i+batch_size]
            print(f"🔄 Processing batch {i//batch_size + 1}/{(len(chunked_docs)-1)//batch_size + 1} ({len(batch)} documents)")
            
            # Check total tokens in batch
            batch_tokens = sum(count_tokens(doc.page_content) for doc in batch)
            print(f"   Batch tokens: {batch_tokens:,}")
            
            if batch_tokens > 250000:  # Safety margin below 300k limit
                print("   ⚠️  Large batch detected, processing individually...")
                for j, doc in enumerate(batch):
                    single_batch = [doc]
                    if i == 0 and j == 0:
                        vector_db = Chroma.from_documents(
                            single_batch,
                            embedding=embedder,
                            persist_directory=settings.VECTOR_DB_DIR
                        )
                    else:
                        vector_db.add_documents(single_batch)
                    all_processed.extend(single_batch)
            else:
                if i == 0:
                    vector_db = Chroma.from_documents(
                        batch,
                        embedding=embedder,
                        persist_directory=settings.VECTOR_DB_DIR
                    )
                else:
                    vector_db.add_documents(batch)
                all_processed.extend(batch)
        
        print("✅ Embedding complete → stored in vector DB")
        print(f"📊 Vector DB location: {settings.VECTOR_DB_DIR}")
        print(f"📊 Total processed documents: {len(all_processed)}")
        
        # Test the vector database with different query types
        print("\n🔍 Testing vector database...")
        
        # Test 1: General search
        test_results = vector_db.similarity_search("budget", k=3)
        print(f"Budget search returned {len(test_results)} results")
        
        # Test 2: Date-specific search
        date_results = vector_db.similarity_search("April 2025", k=2)
        print(f"Date search returned {len(date_results)} results")
        
        # Test 3: Financial search
        financial_results = vector_db.similarity_search("contract approval", k=2)
        print(f"Financial search returned {len(financial_results)} results")
        
        return vector_db
        
    except Exception as e:
        print(f"❌ Error during embedding: {e}")
        raise


if __name__ == "__main__":
    embed_json()
