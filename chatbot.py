"""
Interactive Chatbot for querying agenda data.
Provides natural language interface to search and query meeting agenda information.
"""
import streamlit as st
from typing import List, Dict, Any, Optional
from openai import OpenAI
import chromadb
from pathlib import Path
import json
import time
from datetime import datetime
import re
import csv
import os

from config import OPENAI_API_KEY, OPENAI_MODEL, EMBEDDING_MODEL, VECTOR_DB_DIR, OUTPUT_DIR
from utils import setup_logging

logger = setup_logging()

class AgendaChatbot:
    """Chatbot for querying agenda information using vector search and LLM."""
    
    def __init__(self):
        self.client = OpenAI(api_key=OPENAI_API_KEY)
        self.chroma_client = chromadb.PersistentClient(path=str(VECTOR_DB_DIR))

        # Load collections
        try:
            self.summaries_collection = self.chroma_client.get_collection("agenda_summaries")
            self.json_collection = self.chroma_client.get_collection("agenda_structured_data")
        except Exception as e:
            logger.error(f"Error loading collections: {e}")
            self.summaries_collection = None
            self.json_collection = None

    def generate_query_embedding(self, query: str) -> List[float]:
        """Generate embedding for user query."""
        try:
            response = self.client.embeddings.create(
                model=EMBEDDING_MODEL,
                input=query
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Error generating query embedding: {e}")
            return []

    def search_summaries(self, query: str, n_results: int = 5) -> List[Dict[str, Any]]:
        """Search agenda summaries using vector similarity."""
        if not self.summaries_collection:
            return []
        
        try:
            query_embedding = self.generate_query_embedding(query)
            if not query_embedding:
                return []
            
            results = self.summaries_collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                include=["documents", "metadatas", "distances"]
            )
            
            return [
                {
                    "document": doc,
                    "metadata": meta,
                    "distance": dist
                }
                for doc, meta, dist in zip(
                    results["documents"][0],
                    results["metadatas"][0],
                    results["distances"][0]
                )
            ]
        except Exception as e:
            logger.error(f"Error searching summaries: {e}")
            return []

    def search_structured_data(self, query: str, n_results: int = 5) -> List[Dict[str, Any]]:
        """Search structured agenda data using vector similarity."""
        if not self.json_collection:
            return []
        
        try:
            query_embedding = self.generate_query_embedding(query)
            if not query_embedding:
                return []
            
            results = self.json_collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                include=["documents", "metadatas", "distances"]
            )
            
            return [
                {
                    "document": doc,
                    "metadata": meta,
                    "distance": dist
                }
                for doc, meta, dist in zip(
                    results["documents"][0],
                    results["metadatas"][0],
                    results["distances"][0]
                )
            ]
        except Exception as e:
            logger.error(f"Error searching structured data: {e}")
            return []

    def _parse_meeting_type_from_query(self, query: str) -> Optional[str]:
        """Heuristic: extract '<Something> Committee' before the word 'meeting' if present."""
        import re
        m = re.search(r"([A-Za-z&\-\s]+Committee)", query, re.IGNORECASE)
        if m:
            return m.group(1).strip()
        # Also try specific known keyword
        if "transportation" in query.lower():
            return "Transportation"
        return None

    def get_detailed_agenda_data(self, agenda_number: int) -> Optional[Dict[str, Any]]:
        """Get detailed structured data for a specific agenda."""
        try:
            json_file = OUTPUT_DIR / "json_data" / f"data_{agenda_number}.json"
            if json_file.exists():
                with open(json_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Error loading detailed data for agenda {agenda_number}: {e}")
        
        return None

    def create_context_from_results(self, summary_results: List[Dict], json_results: List[Dict]) -> str:
        """Create context string from search results."""
        context_parts = []
        
        # Add summary results
        if summary_results:
            context_parts.append("RELEVANT AGENDA SUMMARIES:")
            for i, result in enumerate(summary_results[:3], 1):
                metadata = result["metadata"]
                document = result["document"]
                context_parts.append(f"\n{i}. Agenda {metadata.get('agenda_number', 'Unknown')} ({metadata.get('source_file', 'Unknown')}):")
                context_parts.append(f"   {document}")
        
        # Add structured data results
        if json_results:
            context_parts.append("\n\nRELEVANT STRUCTURED DATA:")
            for i, result in enumerate(json_results[:3], 1):
                metadata = result["metadata"]
                document = result["document"]
                context_parts.append(f"\n{i}. Agenda {metadata.get('agenda_number', 'Unknown')}:")
                context_parts.append(f"   Meeting: {metadata.get('meeting_type', 'Unknown')} on {metadata.get('meeting_date', 'Unknown')}")
                context_parts.append(f"   Organization: {metadata.get('organization', 'Unknown')}")
                context_parts.append(f"   Data: {document}")
        
        return "\n".join(context_parts)

    def generate_response(self, query: str, context: str) -> str:
        """Generate response using OpenAI with context."""
        try:
            system_prompt = """You are an AI assistant specializing in Dallas city government meeting agendas. 
            You help users find and understand information from city council meetings, committee meetings, and board meetings.
            
            Based on the provided context from agenda summaries and structured data, provide accurate and helpful responses.
            If the information isn't available in the context, say so clearly.
            
            RESPONSE STYLE GUIDELINES:
            - For simple, direct questions (like dates, names, basic facts): Provide concise, focused answers
            - For complex analysis or multiple topics: Provide detailed explanations
            - Always be clear and direct - avoid unnecessary elaboration for straightforward queries
            
            IMPORTANT: When referencing information, always mention the specific agenda number and source file name 
            (e.g., "According to Agenda 10 (Agenda_10.txt)..." or "As shown in Agenda 150 (Agenda_150.txt)...").
            This helps users trace back to the original documents.
            
            Focus on being helpful, accurate, and appropriately concise while citing specific agenda numbers and file names when referencing information."""
            
            user_prompt = f"""
User Question: {query}

Context from Agenda Database:
{context}

Please provide an appropriate response based on the available information. 
- If this is a simple, factual question, be concise and direct
- If this requires analysis or covers multiple topics, provide more detail
- Always mention specific agenda numbers when referencing information
"""
            
            response = self.client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=1000,
                temperature=0.3
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return f"I'm sorry, I encountered an error while processing your question: {str(e)}"

    def process_query(self, query: str) -> Dict[str, Any]:
        """Process a user query and return response with sources and timing."""
        start_time = time.time()

        # Search both collections
        search_start = time.time()
        summary_results = self.search_summaries(query, n_results=5)
        json_results = self.search_structured_data(query, n_results=5)
        search_time = time.time() - search_start

        # Create context
        context_start = time.time()
        context = self.create_context_from_results(summary_results, json_results)
        context_time = time.time() - context_start

        # Generate response
        response_start = time.time()
        response = self.generate_response(query, context)
        response_time = time.time() - response_start

        total_time = time.time() - start_time

        # Extract source files from results
        source_files = self.extract_source_files(summary_results, json_results)

        return {
            "response": response,
            "summary_results": summary_results,
            "json_results": json_results,
            "context": context,
            "source_files": source_files,
            "timing": {
                "total_time": round(total_time, 2),
                "search_time": round(search_time, 2),
                "context_time": round(context_time, 2),
                "response_time": round(response_time, 2)
            },
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

    def extract_source_files(self, summary_results: List[Dict], json_results: List[Dict]) -> List[Dict[str, Any]]:
        """Extract and deduplicate source file information from search results."""
        sources = {}
        
        # Process summary results
        for result in summary_results:
            metadata = result["metadata"]
            agenda_num = metadata.get('agenda_number')
            source_file = metadata.get('source_file', 'Unknown')
            
            if agenda_num not in sources:
                sources[agenda_num] = {
                    "agenda_number": agenda_num,
                    "source_file": source_file,
                    "similarity_summary": round(1 - result["distance"], 3) if result["distance"] is not None else 0.0,
                    "similarity_structured": 0.0,
                    "found_in": ["summary"]
                }
            else:
                sources[agenda_num]["similarity_summary"] = round(1 - result["distance"], 3) if result["distance"] is not None else 0.0
                if "summary" not in sources[agenda_num]["found_in"]:
                    sources[agenda_num]["found_in"].append("summary")
        
        # Process JSON results
        for result in json_results:
            metadata = result["metadata"]
            agenda_num = metadata.get('agenda_number')
            source_file = metadata.get('source_file', 'Unknown')
            
            if agenda_num not in sources:
                sources[agenda_num] = {
                    "agenda_number": agenda_num,
                    "source_file": source_file,
                    "similarity_summary": 0.0,
                    "similarity_structured": round(1 - result["distance"], 3) if result["distance"] is not None else 0.0,
                    "found_in": ["structured_data"],
                    "meeting_date": metadata.get('meeting_date'),
                    "meeting_type": metadata.get('meeting_type'),
                    "organization": metadata.get('organization')
                }
            else:
                sources[agenda_num]["similarity_structured"] = round(1 - result["distance"], 3) if result["distance"] is not None else 0.0
                if "structured_data" not in sources[agenda_num]["found_in"]:
                    sources[agenda_num]["found_in"].append("structured_data")
                # Add meeting info if not already present
                if "meeting_date" not in sources[agenda_num]:
                    sources[agenda_num]["meeting_date"] = metadata.get('meeting_date')
                    sources[agenda_num]["meeting_type"] = metadata.get('meeting_type')
                    sources[agenda_num]["organization"] = metadata.get('organization')
        
        # Sort by highest similarity score
        source_list = list(sources.values())
        source_list.sort(key=lambda x: max(
            x.get('similarity_summary') or 0, 
            x.get('similarity_structured') or 0
        ), reverse=True)
        
        return source_list

def _sanitize_markdown_response(text: str) -> str:
    """Fix common Markdown issues in LLM output:
    - Convert snake_case word groups used as sentence text into spaced words
    - Preserve filenames like Agenda_448.txt (escape underscores instead)
    - Escape remaining underscores so Markdown doesn't treat them as italics

    Heuristics:
    - If a token has underscores and no dot and no digits, replace '_' with space
    - Otherwise, escape underscores so they render literally
    """
    if not text:
        return text

    def fix_token(token: str) -> str:
        if "_" not in token:
            return token
        # Preserve filenames or tokens with digits/periods by escaping underscores
        if any(ch.isdigit() for ch in token) or "." in token:
            return token.replace("_", r"\_")
        # Otherwise convert underscores to spaces
        return token.replace("_", " ")

    # Process token-by-token to avoid breaking Markdown lists/links
    parts = re.split(r"(\s+)", text)
    parts = [fix_token(p) if not p.isspace() else p for p in parts]
    fixed = "".join(parts)
    # As a final safeguard, escape any remaining underscores
    fixed = fixed.replace("_", r"\_")
    return fixed

# -------------------------------
# Persistent logging utilities
# -------------------------------
LOGS_DIR = OUTPUT_DIR / "chat_logs"
RECENT_QUERIES_FILE = LOGS_DIR / "recent_queries.json"
CHAT_LOG_JSONL = LOGS_DIR / "chat_history.jsonl"
CHAT_LOG_CSV = LOGS_DIR / "chat_history.csv"

def _ensure_logs_dir() -> None:
    try:
        LOGS_DIR.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        logger.error(f"Unable to create logs directory: {e}")

def load_recent_queries_from_disk(limit: int = 10) -> list:
    _ensure_logs_dir()
    if RECENT_QUERIES_FILE.exists():
        try:
            with open(RECENT_QUERIES_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return data[:limit]
        except Exception as e:
            logger.warning(f"Failed to read recent queries: {e}")
    return []

def save_recent_queries_to_disk(queries: list) -> None:
    _ensure_logs_dir()
    try:
        with open(RECENT_QUERIES_FILE, "w", encoding="utf-8") as f:
            json.dump(queries, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.warning(f"Failed to write recent queries: {e}")

def append_chat_log(record: dict) -> None:
    """Append a chat record to JSONL and CSV.
    Expected record keys: timestamp, query, response (plus optional timings/sources)
    """
    _ensure_logs_dir()
    # JSONL
    try:
        with open(CHAT_LOG_JSONL, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception as e:
        logger.warning(f"Failed to append to JSONL log: {e}")
    # CSV
    try:
        file_exists = os.path.exists(CHAT_LOG_CSV)
        with open(CHAT_LOG_CSV, "a", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=["timestamp", "query", "response"],
                extrasaction="ignore",
            )
            if not file_exists:
                writer.writeheader()
            writer.writerow({
                "timestamp": record.get("timestamp", ""),
                "query": record.get("query", ""),
                "response": record.get("response", ""),
            })
    except Exception as e:
        logger.warning(f"Failed to append to CSV log: {e}")

def main():
    """Main Streamlit app for the chatbot."""
    st.set_page_config(
        page_title="Dallas City Agenda Chatbot",
        page_icon="🏛️",
        layout="wide"
    )
    
    st.title("🏛️ Dallas City Agenda Chatbot")
    st.markdown("Ask questions about Dallas city government meeting agendas and get informed answers!")
    
    # Initialize chatbot
    if 'chatbot' not in st.session_state:
        with st.spinner("Initializing chatbot..."):
            st.session_state.chatbot = AgendaChatbot()
    
    chatbot = st.session_state.chatbot
    
    # Check if collections are available
    if not chatbot.summaries_collection or not chatbot.json_collection:
        st.error("⚠️ Vector database not found. Please run the embedding generation first.")
        st.info("Run: `python embedding_generator.py` to create the vector database.")
        return
    
    # Display collection stats
    try:
        stats = {
            "summaries": chatbot.summaries_collection.count(),
            "structured_data": chatbot.json_collection.count()
        }
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Summary Documents", stats["summaries"])
        with col2:
            st.metric("Structured Data", stats["structured_data"])
    except:
        pass
    
    # Chat interface
    st.markdown("---")
    
    # Chat history in main area
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []

    # Display chat history using chat-style bubbles
    for chat in st.session_state.chat_history:
        # User bubble
        with st.chat_message("user", avatar="👤"):
            st.markdown(chat['query'])
        # Assistant bubble
        with st.chat_message("assistant", avatar="🏛️"):
            st.markdown(_sanitize_markdown_response(chat['result']['response']))
        timing = chat['result']['timing']
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("⏱️ Total Time", f"{timing['total_time']}s")
        with col2:
            st.metric("🔍 Search", f"{timing['search_time']}s")
        with col3:
            st.metric("📝 Context", f"{timing['context_time']}s")
        with col4:
            st.metric("Response", f"{timing['response_time']}s")
        st.caption(f"Query processed at {chat['result']['timestamp']}")

        # Display detailed source information
        if chat['result']["source_files"]:
            st.markdown("### 📚 Sources & Original Files")
            for i, source in enumerate(chat['result']["source_files"][:5], 1):
                with st.expander(f"📄 **{source['source_file']}** (Agenda {source['agenda_number']})"):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown("**File Information:**")
                        st.write(f"• **Original File:** `{source['source_file']}`")
                        st.write(f"• **Agenda Number:** {source['agenda_number']}")
                        if source.get('meeting_date'):
                            st.write(f"• **Meeting Date:** {source['meeting_date']}")
                        if source.get('meeting_type'):
                            st.write(f"• **Meeting Type:** {source['meeting_type']}")
                        if source.get('organization'):
                            st.write(f"• **Organization:** {source['organization']}")
                    with col2:
                        st.markdown("**Relevance Scores:**")
                        if source['similarity_summary'] is not None:
                            st.write(f"• **Summary Match:** {source['similarity_summary']:.3f}")
                        if source['similarity_structured'] is not None:
                            st.write(f"• **Data Match:** {source['similarity_structured']:.3f}")
                        st.write(f"• **Found In:** {', '.join(source['found_in'])}")
                        agenda_path = Path("Agendas_COR") / source["source_file"]
                        if agenda_path.exists():
                            # Show a short preview and allow download of the original file
                            try:
                                preview_text = agenda_path.read_text(encoding="utf-8", errors="replace")
                            except Exception:
                                preview_text = ""
                            if preview_text:
                                st.markdown("**Preview (first 1,500 chars):**")
                                st.text(preview_text[:1500] + ("..." if len(preview_text) > 1500 else ""))

                            # Download button for the original file
                            try:
                                file_bytes = agenda_path.read_bytes()
                                st.download_button(
                                    label="📥 Download Original",
                                    data=file_bytes,
                                    file_name=source["source_file"],
                                    mime="text/plain"
                                )
                            except Exception:
                                st.caption("Unable to load file for download.")
                        else:
                            st.caption("Original file not found on disk.")

        # Expandable detailed search results
        with st.expander("🔍 Detailed Search Results"):
            if chat['result']["summary_results"]:
                st.markdown("**Summary Search Results:**")
                for i, res in enumerate(chat['result']["summary_results"], 1):
                    meta = res["metadata"]
                    similarity = round(1 - res['distance'], 3) if res['distance'] is not None else 0.0
                    st.markdown(f"{i}. **{meta.get('source_file')}** (Agenda {meta.get('agenda_number')}) - Similarity: {similarity}")
                    with st.expander(f"Preview of {meta.get('source_file')}"):
                        st.text(res["document"][:500] + "..." if len(res["document"]) > 500 else res["document"])
            if chat['result']["json_results"]:
                st.markdown("**Structured Data Results:**")
                for i, res in enumerate(chat['result']["json_results"], 1):
                    meta = res["metadata"]
                    similarity = round(1 - res['distance'], 3) if res['distance'] is not None else 0.0
                    st.markdown(f"{i}. **{meta.get('source_file')}** - {meta.get('meeting_type')} on {meta.get('meeting_date')} - Similarity: {similarity}")
                    with st.expander(f"Structured data from {meta.get('source_file')}"):
                        st.text(res["document"])

    # Bottom input area: stays at the bottom like a chat app
    bottom_col1, bottom_col2 = st.columns([1, 5])
    with bottom_col1:
        if st.button("🗑️ Clear Chat History"):
            st.session_state.chat_history = []
            st.rerun()
    with bottom_col2:
        user_query = st.chat_input(
            "Ask a question about Dallas city agendas:",
            key="user_input"
        )
        if user_query:
            with st.spinner("🔍 Searching agenda database..."):
                result = chatbot.process_query(user_query)
            # Save in-memory history
            st.session_state.chat_history.append({'query': user_query, 'result': result})
            # Persist chat log (JSONL & CSV)
            append_chat_log({
                'timestamp': result.get('timestamp', ''),
                'query': user_query,
                'response': result.get('response', ''),
                'timing': result.get('timing', {}),
                'sources': result.get('source_files', []),
            })
            # Update query history when a new query is submitted
            if user_query not in [q['query'] for q in st.session_state.query_history]:
                st.session_state.query_history.insert(0, {
                    'query': user_query,
                    'timestamp': result.get('timestamp', ''),
                    'total_time': result.get('timing', {}).get('total_time', 0)
                })
                st.session_state.query_history = st.session_state.query_history[:10]
                # Persist recent queries list
                save_recent_queries_to_disk(st.session_state.query_history)
            st.rerun()
    
    # Sidebar with additional info
    with st.sidebar:
        st.markdown("### About")
        st.markdown("""
        This chatbot helps you explore Dallas city government meeting agendas using AI-powered search.
        
        **Features:**
        - Semantic search across agendas
        - Structured data extraction
        - AI-powered responses
        - Source citations with original files
        - Response timing metrics
        """)

        st.markdown("### Example Questions")
        with st.expander("Example Questions"):
            with st.expander("By meeting/date"):
                st.markdown("""
                - What were the main topics in the Transportation & Infrastructure Committee on March 25, 2025?
                - Summarize key decisions from City Council on 2025-04-10.
                - Which committees met in March 2025 and what did they cover?
                """)

            with st.expander("Budget and finance"):
                st.markdown("""
                - What budget items were approved in the last two council meetings?
                - Which TIF projects were discussed recently and what funding amounts were proposed?
                - Were any contracts over $500,000 approved this month?
                """)

            with st.expander("Transportation and infrastructure"):
                st.markdown("""
                - What transportation projects downtown were discussed in the last 60 days?
                - Any updates on bike lanes, sidewalks, or Vision Zero initiatives this quarter?
                - What was decided about road resurfacing or traffic signal upgrades?
                """)

            with st.expander("Development and zoning"):
                st.markdown("""
                - Which zoning cases were heard last week and what were the outcomes?
                - What major developments were proposed for Deep Ellum or Oak Cliff recently?
                - Any PUD or SUP applications discussed this month?
                """)

            with st.expander("Neighborhood and location"):
                st.markdown("""
                - Which neighborhoods were mentioned in recent planning meetings and why?
                - What city-owned properties in District 2 were on recent agendas?
                """)

            with st.expander("Policy and outcomes"):
                st.markdown("""
                - What votes were taken on short-term rental regulation in the last 90 days?
                - Were there any changes to procurement or ethics policies?
                """)

            with st.expander("Grants and funding"):
                st.markdown("""
                - What grants were applied for or awarded in the last two months?
                - Any federal/state funding tied to transportation or housing in recent meetings?
                """)

            with st.expander("Public input and stakeholders"):
                st.markdown("""
                - What public comments or stakeholder concerns were recorded for Agenda 13?
                - Which organizations presented or were cited in recent committee meetings?
                """)

            with st.expander("Follow-ups and actions"):
                st.markdown("""
                - What items were deferred, and when are they scheduled next?
                - What action items were assigned, and to which departments?
                """)

            with st.expander("Cross-meeting trends"):
                st.markdown("""
                - What recurring themes appeared across agendas in June–August 2025?
                - How have downtown development topics changed over the last quarter?
                """)

            with st.expander("Quick facts"):
                st.markdown("""
                - When and where was the last Landmark Commission meeting held?
                - Which committee has met most frequently this quarter?
                """)

            st.caption("If you know details, include them in the question for higher precision: Meeting type, exact date or month/year, neighborhood or district, keywords (TIF, zoning, RFP, grant, contract amount).")

        st.markdown("### System Status")
        if chatbot.summaries_collection and chatbot.json_collection:
            st.success("✅ Vector database loaded")
            try:
                stats = {
                    "summaries": chatbot.summaries_collection.count(),
                    "structured_data": chatbot.json_collection.count()
                }
                st.write(f"{stats['summaries']} summary documents")
                st.write(f"{stats['structured_data']} structured documents")
            except:
                pass
        else:
            st.error("❌ Vector database not available")

        # Query History (display-only; initialize from disk)
        if 'query_history' not in st.session_state:
            st.session_state.query_history = load_recent_queries_from_disk(limit=10)

        if st.session_state.query_history:
            st.markdown("### Recent Queries")
            with st.expander("Recent Queries"):
                for i, query_info in enumerate(st.session_state.query_history[:5]):
                    with st.expander(f"Query {i+1}"):
                        st.write(f"**Q:** {query_info['query']}")
                        st.caption(f"Asked at {query_info.get('timestamp', 'Unknown')}")

        # Performance Tips
        st.markdown("### Performance Tips")
        st.markdown("""
        - **Specific queries** get better results
        - **Date ranges** help narrow search
        - **Organization names** improve accuracy
        - **Keywords** like 'budget', 'TIF', 'transportation' work well
        """)

        # Clear history button
        if st.button("Clear Query History"):
            st.session_state.query_history = []
            save_recent_queries_to_disk([])
            st.rerun()

if __name__ == "__main__":
    main()
