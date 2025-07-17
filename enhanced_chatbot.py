"""
Enhanced chatbot with JSON-based structured data support
"""
import os
# Disable ChromaDB telemetry
os.environ["CHROMA_TELEMETRY_ENABLED"] = "false"
os.environ["ANONYMIZED_TELEMETRY"] = "false"

import json
import time
from pathlib import Path
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_chroma import Chroma
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate
from settings import settings
import sys

class EnhancedDocumentChatbot:
    def __init__(self):
        self.vectordb = None
        self.qa_chain = None
        self.json_data = None
        self.load_json_data()
        self.setup_retrieval_system()
    
    def load_json_data(self):
        """Load the JSON data for enhanced querying."""
        json_path = Path("./meetings.json")
        if json_path.exists():
            with open(json_path, 'r', encoding='utf-8') as f:
                self.json_data = json.load(f)
            print(f"📊 Loaded {len(self.json_data['meetings'])} meetings from JSON")
        else:
            print("⚠️  No JSON data found. Some advanced features may be limited.")
    
    def setup_retrieval_system(self):
        """Initialize the vector database and QA chain."""
        try:
            print("🔄 Loading enhanced vector database...")
            
            # Load vector DB
            self.vectordb = Chroma(
                persist_directory=settings.VECTOR_DB_DIR,
                embedding_function=OpenAIEmbeddings(model=settings.EMBEDDING_MODEL)
            )
            
            # Test if the database has documents
            test_results = self.vectordb.similarity_search("test", k=1)
            if not test_results:
                print("❌ No documents found in vector database!")
                print("💡 Run embed_json.py first to create enhanced embeddings")
                sys.exit(1)
            
            print(f"✅ Vector database loaded with documents")
            
            # Set up retriever with enhanced parameters for detailed responses
            retriever = self.vectordb.as_retriever(
                search_type="similarity",
                search_kwargs={"k": 12}  # Retrieve more chunks for comprehensive context
            )
            
            # Set up LLM with higher token limit for detailed responses
            llm = ChatOpenAI(
                model="gpt-3.5-turbo",
                temperature=0.1,
                max_tokens=1500  # Increased for more detailed responses
            )
            
            # Enhanced prompt template for detailed responses
            prompt_template = """You are an expert assistant for City of Richardson council meeting information with deep knowledge of municipal governance.
            
            You have access to comprehensive structured meeting data including:
            - Meeting dates, types, and attendees
            - Individual agenda items with financial impacts
            - Keywords and categories
            - Full meeting transcripts
            - Historical context and trends
            
            RESPONSE REQUIREMENTS:
            1. PROVIDE COMPREHENSIVE SUMMARIES: Give detailed explanations, not just brief answers
            2. INCLUDE CONTEXT: Explain the background and significance of decisions
            3. ANALYZE PATTERNS: When relevant, identify trends across multiple meetings
            4. QUANTIFY IMPACT: Always mention financial amounts, vote counts, and timelines
            5. CITE SOURCES: Reference specific agenda items, meeting dates, and participants
            6. EXPLAIN PROCESS: Describe the administrative or legal process when relevant
            
            RESPONSE FORMAT:
            - Start with a clear summary of the main findings
            - Provide detailed explanations organized by topic or chronology
            - Include specific data points (amounts, dates, participants)
            - Explain the broader context or implications
            - Reference all relevant agenda items and meetings
            
            When answering:
            ✓ Be specific about dates, amounts, and attendees
            ✓ Distinguish between agenda item types (consent, regular, public hearing, ordinance)
            ✓ Explain the significance of financial impacts
            ✓ Provide vote outcomes when available
            ✓ Describe implementation timelines
            ✓ Connect related items across meetings
            ✓ Explain technical terms and procedures
            
            Context from meetings:
            {context}
            
            Question: {question}
            
            Detailed Answer:"""
            
            PROMPT = PromptTemplate(
                template=prompt_template,
                input_variables=["context", "question"]
            )
            
            # Set up RetrievalQA chain
            self.qa_chain = RetrievalQA.from_chain_type(
                llm=llm,
                chain_type="stuff",
                retriever=retriever,
                return_source_documents=True,
                chain_type_kwargs={"prompt": PROMPT}
            )
            
            print("✅ Enhanced chatbot ready!")
            
        except Exception as e:
            print(f"❌ Error setting up chatbot: {e}")
            print("💡 Make sure you have:")
            print("   1. Run convert_to_json.py to create structured data")
            print("   2. Run embed_json.py to create enhanced embeddings")
            print("   3. Set your OpenAI API key in .env file")
            sys.exit(1)
    
    def get_meeting_stats(self):
        """Get quick stats about the meetings."""
        if not self.json_data:
            return "No JSON data available"
        
        meetings = self.json_data['meetings']
        total_meetings = len(meetings)
        total_financial = sum(meeting.get('financial_total', 0) or 0 for meeting in meetings)
        
        # Get date range
        dates = [meeting['date'] for meeting in meetings if meeting.get('date')]
        if dates:
            date_range = f"{min(dates)} to {max(dates)}"
        else:
            date_range = "No dates available"
        
        # Get most common keywords
        all_keywords = []
        for meeting in meetings:
            all_keywords.extend(meeting.get('keywords', []))
        
        keyword_counts = {}
        for keyword in all_keywords:
            keyword_counts[keyword] = keyword_counts.get(keyword, 0) + 1
        
        top_keywords = sorted(keyword_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        
        return f"""
📊 Meeting Database Stats:
- Total meetings: {total_meetings}
- Date range: {date_range}
- Total financial impact: ${total_financial:,}
- Top keywords: {', '.join([f"{k}({v})" for k, v in top_keywords])}
"""
    
    def get_answer(self, query: str) -> dict:
        """Get answer for a query with enhanced source information and timing."""
        try:
            start_time = time.time()
            result = self.qa_chain({"query": query})
            end_time = time.time()
            
            response_time = end_time - start_time
            
            return {
                "answer": result["result"],
                "sources": result["source_documents"],
                "response_time": response_time
            }
        except Exception as e:
            return {
                "answer": f"Sorry, I encountered an error: {str(e)}",
                "sources": [],
                "response_time": 0
            }
    
    def print_enhanced_sources(self, sources, response_time=0):
        """Print enhanced source information with structured metadata and original file mapping."""
        if not sources:
            return
        
        print(f"\n📚 Sources (Response time: {response_time:.2f} seconds):")
        
        source_summaries = self.create_source_summary(sources[:5])  # Show top 5 sources
        for summary in source_summaries:
            print(summary)
        
        if len(sources) > 5:
            print(f"   ... and {len(sources) - 5} more sources")
    
    def get_original_source_file(self, source_metadata):
        """Map source metadata to original agenda file."""
        source = source_metadata.get('source', '')
        date = source_metadata.get('date', '')
        
        # Try to find the original file from the JSON data
        if self.json_data and 'meetings' in self.json_data:
            for meeting in self.json_data['meetings']:
                # Try to match by date if available
                if date and meeting.get('date') == date:
                    source_file = meeting.get('source_file', 'Unknown file')
                    meeting_type = meeting.get('meeting_type', 'Unknown type')
                    return f"{source_file} ({meeting_type})"
                
                # Try to match by source pattern
                if source and 'Meeting_' in source:
                    # Extract potential date from Meeting_2025-04-09 format
                    if date in source:
                        source_file = meeting.get('source_file', 'Unknown file')
                        meeting_type = meeting.get('meeting_type', 'Unknown type')
                        return f"{source_file} ({meeting_type})"
        
        # Try to extract from source string patterns  
        if 'Agenda_' in source:
            return source
        elif 'Meeting_' in source and date:
            return f"Meeting on {date}"
        elif 'chunk_' in source:
            return f"Document chunk ({date})" if date else "Document chunk"
        
        return "Unknown file"

    def create_source_summary(self, docs):
        """Create a summary of sources with original file mapping."""
        sources = []
        for i, doc in enumerate(docs):
            metadata = doc.metadata
            original_file = self.get_original_source_file(metadata)
            chunk_type = metadata.get('chunk_type', 'unknown')
            date = metadata.get('date', 'unknown')
            
            if chunk_type == 'overview':
                sources.append(f"   {i+1}. {original_file} - Meeting Overview")
            elif chunk_type == 'agenda_item':
                item_num = metadata.get('item_number', '?')
                item_title = metadata.get('item_title', 'Unknown item')
                sources.append(f"   {i+1}. {original_file} - Agenda Item #{item_num}: {item_title}")
            elif chunk_type == 'full_meeting':
                sources.append(f"   {i+1}. {original_file} - Full Meeting Content")
            else:
                sources.append(f"   {i+1}. {original_file} - {chunk_type}")
        
        return sources

    def run_interactive(self):
        """Run the enhanced interactive chatbot."""
        print("\n" + "="*70)
        print("🤖 Enhanced City of Richardson Council Meeting Chatbot")
        print("="*70)
        print("📊 Powered by structured meeting data with enhanced search capabilities")
        print("="*70)
        
        # Show stats
        print(self.get_meeting_stats())
        
        print("\n💡 Enhanced capabilities:")
        print("   - Search by date: 'What happened in April 2025?'")
        print("   - Find by attendee: 'Which meetings did John Smith attend?'")
        print("   - Financial analysis: 'What are the largest budget items?'")
        print("   - Topic tracking: 'Show me all infrastructure projects'")
        print("   - Trend analysis: 'What are the recurring themes?'")
        
        print("\n📝 Type 'exit' or 'quit' to stop")
        print("-"*70)
        
        while True:
            try:
                query = input("\n🗣️  You: ").strip()
                
                if query.lower() in ["exit", "quit", "q"]:
                    print("👋 Goodbye!")
                    break
                
                if query.lower() == "stats":
                    print(self.get_meeting_stats())
                    continue
                
                if not query:
                    continue
                
                print("🤔 Analyzing structured data...")
                result = self.get_answer(query)
                
                print(f"\n🤖 Bot: {result['answer']}")
                self.print_enhanced_sources(result['sources'], result['response_time'])
                
            except KeyboardInterrupt:
                print("\n\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"\n❌ Error: {e}")

def get_answer(query: str) -> str:
    """Simple function for backwards compatibility."""
    chatbot = EnhancedDocumentChatbot()
    result = chatbot.get_answer(query)
    return result["answer"]

if __name__ == "__main__":
    chatbot = EnhancedDocumentChatbot()
    chatbot.run_interactive()
