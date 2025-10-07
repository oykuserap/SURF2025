"""
Embedding Generator for summaries and JSON data.
Creates vector embeddings for both summaries and structured data using OpenAI embeddings.
"""
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from openai import OpenAI
import chromadb
import uuid

from config import OPENAI_API_KEY, EMBEDDING_MODEL, OUTPUT_DIR, VECTOR_DB_DIR, BOND_DIR
from utils import setup_logging, load_json

logger = setup_logging()

class EmbeddingGenerator:
    """Generate embeddings for summaries and JSON data using OpenAI and ChromaDB."""
    
    def __init__(self):
        self.client = OpenAI(api_key=OPENAI_API_KEY)
        self.chroma_client = chromadb.PersistentClient(path=str(VECTOR_DB_DIR))
        
        # Create collections
        self.summaries_collection = self.chroma_client.get_or_create_collection(
            name="agenda_summaries",
            metadata={"description": "Embeddings of agenda summaries"}
        )
        
        self.json_collection = self.chroma_client.get_or_create_collection(
            name="agenda_structured_data",
            metadata={"description": "Embeddings of structured agenda data"}
        )
        
        # Bond documents collection
        self.bond_collection = self.chroma_client.get_or_create_collection(
            name="bond_documents",
            metadata={"description": "Embeddings of bond-related documents"}
        )
        
    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for text using OpenAI."""
        try:
            response = self.client.embeddings.create(
                model=EMBEDDING_MODEL,
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            return []

    def prepare_summary_text(self, summary_data: Dict[str, Any]) -> str:
        """Prepare summary text for embedding."""
        summary = summary_data.get("summary", "")
        agenda_number = summary_data.get("agenda_number", "")
        source_file = summary_data.get("source_file", "")
        
        # Combine metadata with summary for better context
        text = f"Agenda {agenda_number} ({source_file}): {summary}"
        return text

    def prepare_json_text(self, json_data: Dict[str, Any]) -> str:
        """Prepare structured JSON data for embedding."""
        extracted = json_data.get("extracted_data", {})
        
        # Extract key information for embedding
        meeting_info = extracted.get("meeting_info", {})
        agenda_items = extracted.get("agenda_items", [])
        keywords = extracted.get("keywords", [])
        financial_items = extracted.get("financial_items", [])
        
        # Create comprehensive text representation
        text_parts = []
        
        # Meeting information
        if meeting_info:
            date = meeting_info.get("date", "")
            meeting_type = meeting_info.get("type", "")
            organization = meeting_info.get("organization", "")
            text_parts.append(f"Meeting: {meeting_type} of {organization} on {date}")
        
        # Agenda items
        if agenda_items:
            items_text = "Agenda items: " + "; ".join([
                f"{item.get('item_number', '')}: {item.get('title', '')}"
                for item in agenda_items[:5]  # Limit to first 5 items
            ])
            text_parts.append(items_text)
        
        # Keywords
        if keywords:
            text_parts.append(f"Keywords: {', '.join(keywords)}")
        
        # Financial items
        if financial_items:
            financial_text = "Financial items: " + "; ".join([
                f"{item.get('description', '')} ({item.get('amount', '')})"
                for item in financial_items
            ])
            text_parts.append(financial_text)
        
        return " | ".join(text_parts)

    def process_summary_file(self, summary_file: Path) -> bool:
        """Process a single summary file and create embeddings."""
        try:
            print(f"📄 Processing summary: {summary_file.name}...")
            logger.info(f"Processing summary file: {summary_file.name}")
            
            # Load summary data
            summary_data = load_json(summary_file)
            
            if "error" in summary_data:
                print(f"   ⚠️  Skipping {summary_file.name} - contains error")
                logger.warning(f"Skipping file with error: {summary_file.name}")
                return False
            
            # Prepare text for embedding
            text = self.prepare_summary_text(summary_data)
            print(f"   📝 Summary text prepared ({len(text)} chars)")
            
            # Generate embedding
            print(f"   🔄 Generating embedding...")
            embedding = self.generate_embedding(text)
            
            if not embedding:
                print(f"   ❌ Failed to generate embedding for {summary_file.name}")
                logger.error(f"Failed to generate embedding for {summary_file.name}")
                return False
            
            print(f"   ✅ Embedding generated ({len(embedding)} dimensions)")
            
            # Create document ID
            doc_id = f"summary_{summary_data.get('agenda_number', uuid.uuid4())}"
            
            # Add to ChromaDB with safe metadata (no None values)
            metadata = {
                "agenda_number": str(summary_data.get("agenda_number", "unknown")),
                "source_file": str(summary_data.get("source_file", "unknown")),
                "type": "summary",
                "summary_length": int(summary_data.get("summary_length", 0))
            }
            
            self.summaries_collection.add(
                documents=[text],
                embeddings=[embedding],
                metadatas=[metadata],
                ids=[doc_id]
            )
            
            print(f"   💾 Saved to vector database")
            logger.info(f"Summary embedding created for {summary_file.name}")
            return True
            
        except Exception as e:
            print(f"   ❌ Error processing {summary_file.name}: {str(e)}")
            logger.error(f"Error processing summary file {summary_file.name}: {e}")
            return False

    def process_json_file(self, json_file: Path) -> bool:
        """Process a single JSON data file and create embeddings."""
        try:
            print(f"📊 Processing JSON data: {json_file.name}...")
            logger.info(f"Processing JSON file: {json_file.name}")
            
            # Load JSON data
            json_data = load_json(json_file)
            
            if "error" in json_data:
                print(f"   ⚠️  Skipping {json_file.name} - contains error")
                logger.warning(f"Skipping file with error: {json_file.name}")
                return False
            
            # Prepare text for embedding
            text = self.prepare_json_text(json_data)
            
            if not text.strip():
                print(f"   ⚠️  Skipping {json_file.name} - empty text")
                logger.warning(f"Empty text for {json_file.name}")
                return False
            
            print(f"   📝 JSON text prepared ({len(text)} chars)")
            
            # Generate embedding
            print(f"   🔄 Generating embedding...")
            embedding = self.generate_embedding(text)
            
            if not embedding:
                print(f"   ❌ Failed to generate embedding for {json_file.name}")
                logger.error(f"Failed to generate embedding for {json_file.name}")
                return False
            
            print(f"   ✅ Embedding generated ({len(embedding)} dimensions)")
            
            # Create document ID
            doc_id = f"json_{json_data.get('agenda_number', uuid.uuid4())}"
            
            # Extract metadata
            extracted = json_data.get("extracted_data", {})
            meeting_info = extracted.get("meeting_info", {})
            
            # Add to ChromaDB with safe metadata (no None values)
            metadata = {
                "agenda_number": str(json_data.get("agenda_number", "unknown")),
                "source_file": str(json_data.get("source_file", "unknown")),
                "type": "structured_data",
                "meeting_date": str(meeting_info.get("date", "unknown")),
                "meeting_type": str(meeting_info.get("type", "unknown")),
                "organization": str(meeting_info.get("organization", "unknown")),
                "num_agenda_items": int(len(extracted.get("agenda_items", []))),
                "num_keywords": int(len(extracted.get("keywords", [])))
            }
            
            self.json_collection.add(
                documents=[text],
                embeddings=[embedding],
                metadatas=[metadata],
                ids=[doc_id]
            )
            
            print(f"   💾 Saved to vector database")
            logger.info(f"JSON embedding created for {json_file.name}")
            return True
            
        except Exception as e:
            print(f"   ❌ Error processing {json_file.name}: {str(e)}")
            logger.error(f"Error processing JSON file {json_file.name}: {e}")
            return False

    def process_all_summaries(self) -> Dict[str, int]:
        """Process all summary files and create embeddings in batches."""
        summaries_dir = OUTPUT_DIR / "summaries"
        all_summary_files = list(summaries_dir.glob("summary_*.json"))
        
        # Filter out already processed files
        summary_files = self.filter_unprocessed_files(all_summary_files, "summaries")
        
        print(f"\n🔍 Found {len(all_summary_files)} total summary files")
        print(f"📋 {len(all_summary_files) - len(summary_files)} already processed")
        print(f"🆕 {len(summary_files)} new files to process")
        
        if len(summary_files) == 0:
            print("✅ All summary files already processed!")
            return {"successful": 0, "failed": 0}
        
        logger.info(f"Processing {len(summary_files)} summary files")
        
        successful = 0
        failed = 0
        batch_size = 10
        
        # Process in batches of 10
        for i in range(0, len(summary_files), batch_size):
            batch = summary_files[i:i+batch_size]
            batch_num = (i // batch_size) + 1
            total_batches = (len(summary_files) + batch_size - 1) // batch_size
            
            print(f"\n📦 Processing batch {batch_num}/{total_batches} ({len(batch)} files)")
            print("=" * 60)
            
            batch_successful = 0
            batch_failed = 0
            
            for summary_file in batch:
                if self.process_summary_file(summary_file):
                    successful += 1
                    batch_successful += 1
                else:
                    failed += 1
                    batch_failed += 1
                print()  # Empty line for readability
            
            print(f"📦 Batch {batch_num} complete: ✅ {batch_successful} successful, ❌ {batch_failed} failed")
            print(f"📊 Overall progress: {successful + failed}/{len(summary_files)} files processed")
            
            # Force save progress
            try:
                self.summaries_collection.persist()
                print(f"💾 Progress saved to disk")
            except:
                pass  # ChromaDB might not have persist method in all versions
        
        print(f"\n🎉 Summary processing complete!")
        print(f"   ✅ Total successful: {successful}")
        print(f"   ❌ Total failed: {failed}")
        
        return {"successful": successful, "failed": failed}

    def process_all_json_data(self) -> Dict[str, int]:
        """Process all JSON data files and create embeddings in batches."""
        json_dir = OUTPUT_DIR / "json_data"
        all_json_files = list(json_dir.glob("data_*.json"))
        
        # Filter out already processed files
        json_files = self.filter_unprocessed_files(all_json_files, "json_data")
        
        print(f"\n🔍 Found {len(all_json_files)} total JSON data files")
        print(f"📋 {len(all_json_files) - len(json_files)} already processed")
        print(f"🆕 {len(json_files)} new files to process")
        
        if len(json_files) == 0:
            print("✅ All JSON data files already processed!")
            return {"successful": 0, "failed": 0}
        
        logger.info(f"Processing {len(json_files)} JSON data files")
        
        successful = 0
        failed = 0
        batch_size = 10
        
        # Process in batches of 10
        for i in range(0, len(json_files), batch_size):
            batch = json_files[i:i+batch_size]
            batch_num = (i // batch_size) + 1
            total_batches = (len(json_files) + batch_size - 1) // batch_size
            
            print(f"\n📦 Processing batch {batch_num}/{total_batches} ({len(batch)} files)")
            print("=" * 60)
            
            batch_successful = 0
            batch_failed = 0
            
            for json_file in batch:
                if self.process_json_file(json_file):
                    successful += 1
                    batch_successful += 1
                else:
                    failed += 1
                    batch_failed += 1
                print()  # Empty line for readability
            
            print(f"📦 Batch {batch_num} complete: ✅ {batch_successful} successful, ❌ {batch_failed} failed")
            print(f"📊 Overall progress: {successful + failed}/{len(json_files)} files processed")
            
            # Force save progress
            try:
                self.json_collection.persist()
                print(f"💾 Progress saved to disk")
            except:
                pass  # ChromaDB might not have persist method in all versions
        
        print(f"\n🎉 JSON processing complete!")
        print(f"   ✅ Total successful: {successful}")
        print(f"   ❌ Total failed: {failed}")
        
        return {"successful": successful, "failed": failed}

    def get_collection_stats(self) -> Dict[str, Any]:
        """Get statistics about the vector collections."""
        return {
            "summaries_collection": {
                "count": self.summaries_collection.count(),
                "name": self.summaries_collection.name
            },
            "json_collection": {
                "count": self.json_collection.count(),
                "name": self.json_collection.name
            },
            "bond_collection": {
                "count": self.bond_collection.count(),
                "name": self.bond_collection.name
            }
        }

    def get_processed_files(self) -> Dict[str, List[str]]:
        """Get lists of already processed files to avoid reprocessing."""
        processed_summaries: List[str] = []
        processed_json: List[str] = []
        processed_bonds: List[str] = []

        try:
            # Get processed summaries
            summary_results = self.summaries_collection.get()
            for metadata in summary_results['metadatas']:
                if metadata and 'source_file' in metadata:
                    processed_summaries.append(metadata['source_file'])
        except Exception:
            pass

        try:
            # Get processed JSON data
            json_results = self.json_collection.get()
            for metadata in json_results['metadatas']:
                if metadata and 'source_file' in metadata:
                    processed_json.append(metadata['source_file'])
        except Exception:
            pass

        try:
            # Get processed bond documents
            bond_results = self.bond_collection.get()
            for metadata in bond_results['metadatas']:
                if metadata and 'source_file' in metadata:
                    processed_bonds.append(metadata['source_file'])
        except Exception:
            pass

        return {
            "summaries": processed_summaries,
            "json_data": processed_json,
            "bond_docs": processed_bonds
        }

    def filter_unprocessed_files(self, files: List[Path], file_type: str) -> List[Path]:
        """Filter out already processed files."""
        processed = self.get_processed_files()
        processed_names = processed.get(file_type, [])
        
        unprocessed = []
        for file_path in files:
            # Extract the source file name based on file type
            if file_type == "summaries":
                # summary_10.json -> Agenda_10.txt
                agenda_num = file_path.stem.replace("summary_", "")
                source_name = f"Agenda_{agenda_num}.txt"
            else:  # json_data
                # data_10.json -> Agenda_10.txt
                agenda_num = file_path.stem.replace("data_", "")
                source_name = f"Agenda_{agenda_num}.txt"
            
            if source_name not in processed_names:
                unprocessed.append(file_path)
        
        return unprocessed

    # -------------------------------
    # Bond documents processing
    # -------------------------------
    def prepare_bond_text(self, file_path: Path) -> str:
        try:
            return file_path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            return ""

    def process_bond_file(self, file_path: Path) -> bool:
        try:
            print(f"📄 Processing bond doc: {file_path.name}...")
            text = self.prepare_bond_text(file_path)
            if not text.strip():
                print("   ⚠️ Empty file or unreadable")
                return False
            # Trim very long docs to a sane size for embeddings (e.g., first 6000 chars)
            snippet = text[:6000]
            embedding = self.generate_embedding(snippet)
            if not embedding:
                print("   ❌ Failed to generate embedding")
                return False
            metadata = {
                "source_file": file_path.name,
                "type": "bond_document",
            }
            doc_id = f"bond_{file_path.name}"
            self.bond_collection.add(
                documents=[snippet],
                embeddings=[embedding],
                metadatas=[metadata],
                ids=[doc_id]
            )
            print("   💾 Saved to vector database")
            return True
        except Exception as e:
            print(f"   ❌ Error processing {file_path.name}: {e}")
            return False

    def process_bond_documents(self) -> Dict[str, int]:
        bond_dir = BOND_DIR
        bond_files = sorted(list(bond_dir.glob("*.txt"))) if bond_dir.exists() else []
        if not bond_files:
            print("No bond documents found.")
            return {"successful": 0, "failed": 0}
        # Filter out already processed
        processed = set(self.get_processed_files().get("bond_docs", []))
        to_process = [p for p in bond_files if p.name not in processed]
        print(f"🔎 Found {len(bond_files)} bond files | {len(bond_files)-len(to_process)} already processed | {len(to_process)} new")
        successful = 0
        failed = 0
        for f in to_process:
            if self.process_bond_file(f):
                successful += 1
            else:
                failed += 1
        print(f"🎉 Bond docs processed: ✅ {successful} | ❌ {failed}")
        try:
            self.bond_collection.persist()
        except Exception:
            pass
        return {"successful": successful, "failed": failed}

def main():
    """Main function to run embedding generation."""
    generator = EmbeddingGenerator()
    
    print("Generating embeddings for summaries and structured data...")
    
    # Process summaries
    print("\n1. Processing summaries...")
    summary_results = generator.process_all_summaries()
    print(f"   ✅ Successful: {summary_results['successful']}")
    print(f"   ❌ Failed: {summary_results['failed']}")
    
    # Process JSON data
    print("\n2. Processing structured data...")
    json_results = generator.process_all_json_data()
    print(f"   ✅ Successful: {json_results['successful']}")
    print(f"   ❌ Failed: {json_results['failed']}")
    
    # Show collection stats
    print("\n3. Processing bond documents...")
    bond_results = generator.process_bond_documents()
    print(f"   ✅ Successful: {bond_results['successful']}")
    print(f"   ❌ Failed: {bond_results['failed']}")

    print("\n4. Vector Database Statistics:")
    stats = generator.get_collection_stats()
    print(f"   📄 Summaries: {stats['summaries_collection']['count']} documents")
    print(f"   📊 Structured Data: {stats['json_collection']['count']} documents")
    print(f"   🏛️ Bond Docs: {stats['bond_collection']['count']} documents")
    
    print(f"\nEmbedding generation complete!")
    print(f"Vector database stored in: {VECTOR_DB_DIR}")

if __name__ == "__main__":
    main()
