from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain.schema import Document
from pathlib import Path
from settings import settings

CHUNKS_PATH = Path("./chunks")


def load_chunks():
    docs = []
    for f in CHUNKS_PATH.glob("*.txt"):
        text = f.read_text(encoding="utf-8")
        docs.append(Document(page_content=text, metadata={"source": str(f)}))
    return docs


def embed():
    docs = load_chunks()
    print(f"Embedding {len(docs)} chunks …")
    embedder = OpenAIEmbeddings(model=settings.EMBEDDING_MODEL)
    Chroma.from_documents(docs, embedding=embedder, persist_directory=settings.VECTOR_DB_DIR)
    print("✅ Embedding complete → stored in vector DB")


if __name__ == "__main__":
    embed()