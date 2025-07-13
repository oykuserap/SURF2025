from pathlib import Path
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document

RAW_DIR = Path("./Agendas_COR")
CHUNKS_PATH = Path("./chunks")
CHUNKS_PATH.mkdir(exist_ok=True)

# Configuration for text splitting
CHUNK_SIZE = 1000  # Maximum characters per chunk
CHUNK_OVERLAP = 200  # Overlap between chunks to maintain context


def load_text_files():
    """Load all text files from the raw directory."""
    docs = []
    for file in RAW_DIR.glob("*.txt"):
        try:
            text = file.read_text(encoding="utf-8", errors="ignore")
            docs.append(Document(page_content=text, metadata={"source": str(file)}))
            print(f"Loaded {file.name}: {len(text)} characters")
        except Exception as e:
            print(f"Skipping {file}: {e}")
    return docs


def split_documents(docs):
    """Split documents into smaller chunks for better retrieval."""
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        length_function=len,
        separators=["\n\n", "\n", ". ", " ", ""]  # Try these separators in order
    )
    
    all_chunks = []
    for doc in docs:
        chunks = text_splitter.split_documents([doc])
        # Add chunk index to metadata
        for i, chunk in enumerate(chunks):
            chunk.metadata.update({
                "chunk_index": i,
                "total_chunks": len(chunks),
                "chunk_size": len(chunk.page_content)
            })
        all_chunks.extend(chunks)
    
    return all_chunks


def save_chunks(chunks):
    """Save chunks to individual files with metadata."""
    # Clear existing chunks
    for existing_chunk in CHUNKS_PATH.glob("chunk_*.txt"):
        existing_chunk.unlink()
    
    for i, chunk in enumerate(chunks):
        chunk_content = f"# Chunk {i}\n"
        chunk_content += f"# Source: {chunk.metadata.get('source', 'unknown')}\n"
        chunk_content += f"# Chunk {chunk.metadata.get('chunk_index', 0)} of {chunk.metadata.get('total_chunks', 1)}\n"
        chunk_content += f"# Size: {chunk.metadata.get('chunk_size', len(chunk.page_content))} characters\n\n"
        chunk_content += chunk.page_content
        
        (CHUNKS_PATH / f"chunk_{i}.txt").write_text(chunk_content, encoding="utf-8")


def process_documents():
    """Complete document processing pipeline."""
    print("Loading documents...")
    docs = load_text_files()
    print(f"Loaded {len(docs)} documents")
    
    if not docs:
        print("No documents found!")
        return
    
    print("Splitting documents into chunks...")
    chunks = split_documents(docs)
    print(f"Created {len(chunks)} chunks")
    
    print("Saving chunks...")
    save_chunks(chunks)
    print(f"Saved {len(chunks)} chunks to {CHUNKS_PATH}")
    
    # Print statistics
    total_chars = sum(len(chunk.page_content) for chunk in chunks)
    avg_chunk_size = total_chars / len(chunks) if chunks else 0
    print(f"\nStatistics:")
    print(f"- Total chunks: {len(chunks)}")
    print(f"- Total characters: {total_chars:,}")
    print(f"- Average chunk size: {avg_chunk_size:.0f} characters")
    
    return chunks


if __name__ == "__main__":
    process_documents()