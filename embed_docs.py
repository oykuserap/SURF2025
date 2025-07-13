import os
# Disable ChromaDB telemetry to avoid error messages - must be set before importing chroma
os.environ["CHROMA_TELEMETRY_ENABLED"] = "false"
os.environ["ANONYMIZED_TELEMETRY"] = "false"

from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
from langchain.schema import Document
from pathlib import Path
from settings import settings

CHUNKS_PATH = Path("./chunks")


def load_chunks():
    """Load chunks from saved files, extracting content and metadata."""
    docs = []
    for f in CHUNKS_PATH.glob("*.txt"):
        try:
            text = f.read_text(encoding="utf-8")
            lines = text.split('\n')
            
            # Extract metadata from header lines
            metadata = {"source": str(f)}
            content_start = 0
            
            for i, line in enumerate(lines):
                if line.startswith("# Source:"):
                    metadata["original_source"] = line.replace("# Source:", "").strip()
                elif line.startswith("# Chunk") and "of" in line:
                    # Parse "# Chunk 0 of 3"
                    parts = line.split()
                    if len(parts) >= 4:
                        metadata["chunk_index"] = int(parts[2])
                        metadata["total_chunks"] = int(parts[4])
                elif line.startswith("# Size:"):
                    metadata["chunk_size"] = int(line.replace("# Size:", "").replace("characters", "").strip())
                elif line.strip() == "" and i > 0:
                    # Empty line after metadata headers
                    content_start = i + 1
                    break
            
            # Extract the actual content (skip metadata headers)
            content = '\n'.join(lines[content_start:]).strip()
            
            if content:  # Only add non-empty chunks
                docs.append(Document(page_content=content, metadata=metadata))
                print(f"Loaded chunk from {f.name}: {len(content)} characters")
        except Exception as e:
            print(f"Error loading chunk {f.name}: {e}")
    
    return docs


def embed():
    """Load chunks and create embeddings in vector database."""
    print("Loading chunks...")
    docs = load_chunks()
    
    if not docs:
        print("❌ No chunks found! Run process_docs.py first.")
        return
    
    print(f"Embedding {len(docs)} chunks...")
    
    # Calculate some statistics
    total_chars = sum(len(doc.page_content) for doc in docs)
    avg_chunk_size = total_chars / len(docs) if docs else 0
    
    print(f"- Total characters to embed: {total_chars:,}")
    print(f"- Average chunk size: {avg_chunk_size:.0f} characters")
    
    try:
        embedder = OpenAIEmbeddings(model=settings.EMBEDDING_MODEL)
        vector_db = Chroma.from_documents(
            docs, 
            embedding=embedder, 
            persist_directory=settings.VECTOR_DB_DIR
        )
        print("✅ Embedding complete → stored in vector DB")
        print(f"📊 Vector DB location: {settings.VECTOR_DB_DIR}")
        
        # Test the vector database
        print("\n🔍 Testing vector database...")
        test_results = vector_db.similarity_search("agenda", k=2)
        print(f"Test search returned {len(test_results)} results")
        
    except Exception as e:
        print(f"❌ Error during embedding: {e}")
        raise


if __name__ == "__main__":
    embed()