from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.vectorstores import Chroma
from langchain.chains import RetrievalQA
from settings import settings

def get_answer(query: str) -> str:
    # Load vector DB
    vectordb = Chroma(
        persist_directory=settings.VECTOR_DB_DIR,
        embedding_function=OpenAIEmbeddings(model=settings.EMBEDDING_MODEL)
    )
    retriever = vectordb.as_retriever()

    # Set up LLM
    llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0)

    # Set up RetrievalQA chain
    qa = RetrievalQA.from_chain_type(
        llm=llm,
        chain_type="stuff",
        retriever=retriever,
        return_source_documents=True
    )

    result = qa(query)
    return result["result"]

if __name__ == "__main__":
    print("🤖 Chatbot ready! Type your question (or 'exit' to quit):")
    while True:
        query = input("You: ")
        if query.lower() in ["exit", "quit"]:
            break
        answer = get_answer(query)
        print("Bot:", answer)