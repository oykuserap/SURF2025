from pathlib import Path
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document

RAW_DIR = Path("./raw_docs")
CHUNKS_PATH = Path("./chunks")
CHUNKS_PATH.mkdir(exist_ok=True)


def load_text_files():
    all_chunks = []
    splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=100)
    for file in RAW_DIR.glob("*.txt"):
        try:
            text = file.read_text(encoding="utf-8", errors="ignore")
            chunks = splitter.create_documents([text], metadatas=[{"source": str(file)}])
            all_chunks.extend(chunks)
        except Exception as e:
            print(f"Skipping {file}: {e}")
    return all_chunks


def save_chunks(chunks):
    for i, doc in enumerate(chunks):
        (CHUNKS_PATH / f"chunk_{i}.txt").write_text(doc.page_content, encoding="utf-8")


if __name__ == "__main__":
    chunks = load_text_files()
    save_chunks(chunks)
    print(f"✅ Saved {len(chunks)} chunks to ./chunks")