from pathlib import Path
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document

RAW_DIR = Path("./Agendas_COR")
CHUNKS_PATH = Path("./chunks")
CHUNKS_PATH.mkdir(exist_ok=True)


def load_text_files():
    docs = []
    for file in RAW_DIR.glob("*.txt"):
        try:
            text = file.read_text(encoding="utf-8", errors="ignore")
            docs.append(Document(page_content=text, metadata={"source": str(file)}))
        except Exception as e:
            print(f"Skipping {file}: {e}")
    return docs

def save_docs(docs):
    for i, doc in enumerate(docs):
        (CHUNKS_PATH / f"doc_{i}.txt").write_text(doc.page_content, encoding="utf-8")


def save_chunks(chunks):
    for i, doc in enumerate(chunks):
        (CHUNKS_PATH / f"chunk_{i}.txt").write_text(doc.page_content, encoding="utf-8")


if __name__ == "__main__":
    chunks = load_text_files()
    save_chunks(chunks)
    print(f"Saved {len(chunks)} chunks to ./chunks")