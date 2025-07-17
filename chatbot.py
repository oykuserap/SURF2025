import os
# Disable ChromaDB telemetry
os.environ["CHROMA_TELEMETRY_ENABLED"] = "false"
os.environ["ANONYMIZED_TELEMETRY"] = "false"

from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_chroma import Chroma
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate
from settings import settings
import sys

class DocumentChatbot:
    def __init__(self):
        self.vectordb = None
        self.qa_chain = None
        self.setup_retrieval_system()
    
    def setup_retrieval_system(self):
        """Initialize the vector database and QA chain."""
        try:
            print("🔄 Loading vector database...")
            
            # Load vector DB
            self.vectordb = Chroma(
                persist_directory=settings.VECTOR_DB_DIR,
                embedding_function=OpenAIEmbeddings(model=settings.EMBEDDING_MODEL)
            )
            
            # Test if the database has documents
            test_results = self.vectordb.similarity_search("test", k=1)
            if not test_results:
                print("❌ No documents found in vector database!")
                print("💡 Run process_docs.py and then embed_docs.py first")
                sys.exit(1)
            
            print(f"✅ Vector database loaded with documents")
            
            # Set up retriever with better parameters
            retriever = self.vectordb.as_retriever(
                search_type="similarity",
                search_kwargs={"k": 5}  # Retrieve top 5 most relevant chunks
            )
            
            # Set up LLM
            llm = ChatOpenAI(
                model="gpt-3.5-turbo",
                temperature=0.1,  # Slightly more creative but still focused
                max_tokens=500
            )
            
            # Custom prompt template for better responses
            prompt_template = """You are a helpful assistant that answers questions based on City of Dallas council agenda documents. 
            
            IMPORTANT: You only have access to HISTORICAL agenda documents from previous meetings. You do NOT have:
            - Today's current agenda
            - Live meeting information
            - Real-time updates
            - Future meeting plans
            
            When asked about "today" or "current" meetings, clarify that you only know about past agendas.
            
            Use the following pieces of context to answer the question at the end. There is the dates provided in the Agendas so make sure to give answers including the dates as well.
            If you don't know the answer based on the context, just say that you don't know - don't make up an answer.
            Also, make sure to include the source documents in your answer. Specifically, include the original source file name.

            Context:
            {context}
            
            Question: {question}
            
            Answer: """
            
            PROMPT = PromptTemplate(
                template=prompt_template,
                input_variables=["context", "question"]
            )
            
            # Set up RetrievalQA chain with custom prompt
            self.qa_chain = RetrievalQA.from_chain_type(
                llm=llm,
                chain_type="stuff",
                retriever=retriever,
                return_source_documents=True,
                chain_type_kwargs={"prompt": PROMPT}
            )
            
            print("✅ Chatbot ready!")
            
        except Exception as e:
            print(f"❌ Error setting up chatbot: {e}")
            print("💡 Make sure you have:")
            print("   1. Run process_docs.py to create chunks")
            print("   2. Run embed_docs.py to create embeddings")
            print("   3. Set your OpenAI API key in .env file")
            sys.exit(1)
    
    def get_answer(self, query: str) -> dict:
        """Get answer for a query with source information."""
        try:
            result = self.qa_chain({"query": query})
            return {
                "answer": result["result"],
                "sources": result["source_documents"]
            }
        except Exception as e:
            return {
                "answer": f"Sorry, I encountered an error: {str(e)}",
                "sources": []
            }
    
    def print_sources(self, sources):
        """Print source information in a readable format."""
        if not sources:
            return
        
        print("\n📚 Sources:")
        for i, source in enumerate(sources[:3], 1):  # Show top 3 sources
            source_file = source.metadata.get("original_source", "Unknown")
            chunk_info = f"Chunk {source.metadata.get('chunk_index', '?')}"
            print(f"   {i}. {source_file} ({chunk_info})")
    
    def run_interactive(self):
        """Run the interactive chatbot."""
        print("\n" + "="*60)
        print("🤖 Document Chatbot - Ask questions about your files!")
        print("="*60)
        print("� Available Data: Historical City of Dallas Council Agendas")
        print("⚠️  Note: I only know about PAST agendas, not current/live meetings")
        print("="*60)
        print("💡 Try asking:")
        print("   - What topics were discussed in previous meetings?")
        print("   - What ordinances were considered in past agendas?")
        print("   - What patterns do you see across multiple agendas?")
        print("   - What public hearings were scheduled?")
        print("   - What contracts were approved in past meetings?")
        print("\n📝 Type 'exit' or 'quit' to stop")
        print("-"*60)
        
        while True:
            try:
                query = input("\n🗣️  You: ").strip()
                
                if query.lower() in ["exit", "quit", "q"]:
                    print("👋 Goodbye!")
                    break
                
                if not query:
                    continue
                
                print("🤔 Thinking...")
                result = self.get_answer(query)
                
                print(f"\n🤖 Bot: {result['answer']}")
                self.print_sources(result['sources'])
                
            except KeyboardInterrupt:
                print("\n\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"\n❌ Error: {e}")

def get_answer(query: str) -> str:
    """Simple function for backwards compatibility."""
    chatbot = DocumentChatbot()
    result = chatbot.get_answer(query)
    return result["answer"]

if __name__ == "__main__":
    print("🤖 Chatbot ready! Type your question (or 'exit' to quit):")
    while True:
        query = input("You: ")
        if query.lower() in ["exit", "quit"]:
            break
        answer = get_answer(query)
        print("Bot:", answer)