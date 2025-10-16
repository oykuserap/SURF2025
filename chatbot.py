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
            # Optional: bond collection
            try:
                self.bond_collection = self.chroma_client.get_collection("bond_documents")
            except Exception:
                self.bond_collection = None
        except Exception as e:
            logger.error(f"Error loading collections: {e}")
            self.summaries_collection = None
            self.json_collection = None
            self.bond_collection = None
        # Preload agenda date mapping for recency ranking
        self.agenda_date_map = {}
        if self.json_collection:
            try:
                all_meta = self.json_collection.get(include=["metadatas", "ids"])  # type: ignore
                for meta in all_meta.get("metadatas", []):
                    if not meta:
                        continue
                    agenda_num = meta.get("agenda_number")
                    meeting_date = meta.get("meeting_date")
                    parsed = self._parse_date(meeting_date)
                    if agenda_num and parsed:
                        # store as date object
                        self.agenda_date_map[str(agenda_num)] = parsed
            except Exception as e:
                logger.warning(f"Could not preload agenda dates: {e}")

    # -------------------------------
    # Date parsing & recency helpers
    # -------------------------------
    def _parse_date(self, date_str: Optional[str]):
        if not date_str or not isinstance(date_str, str):
            return None
        import datetime, re
        ds = date_str.strip()
        ds = re.sub(r"(\d+)(st|nd|rd|th)", r"\1", ds)  # remove ordinals
        fmts = ["%B %d, %Y", "%b %d, %Y", "%Y-%m-%d"]
        for f in fmts:
            try:
                return datetime.datetime.strptime(ds, f).date()
            except Exception:
                pass
        return None

    def _query_requests_recency(self, query: str) -> bool:
        q = query.lower()
        triggers = ["recent", "latest", "last", "past", "newest", "most recent"]
        return any(t in q for t in triggers)

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

    def search_bond_documents(self, query: str, n_results: int = 5) -> List[Dict[str, Any]]:
        """Search bond documents."""
        if not getattr(self, 'bond_collection', None):
            return []
        try:
            query_embedding = self.generate_query_embedding(query)
            if not query_embedding:
                return []
            results = self.bond_collection.query(
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
            logger.error(f"Error searching bond documents: {e}")
            return []

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

    def create_context_from_results(self, summary_results: List[Dict], json_results: List[Dict], recency_mode: bool = False) -> str:
        """Create context string from search results."""
        context_parts: List[str] = []

        # Always attempt to enrich and sort by date (most recent first) for better temporal awareness
        def date_key(res):
            meta = res.get("metadata", {})
            ag = meta.get("agenda_number")
            d = self.agenda_date_map.get(str(ag)) or self._parse_date(meta.get("meeting_date"))
            # Return ordinal (int) so all keys are comparable. Use -1 for missing dates.
            try:
                return d.toordinal() if d else -1
            except Exception:
                return -1

        # Enrich summary results with meeting_date if available from structured map
        for r in summary_results:
            meta = r.get("metadata", {})
            ag = meta.get("agenda_number")
            if ag and str(ag) in self.agenda_date_map and "meeting_date" not in meta:
                meta["meeting_date"] = self.agenda_date_map[str(ag)].isoformat()

        # Sort by date (newest first) if we have dates; otherwise original similarity order preserved
        try:
            json_results.sort(key=date_key, reverse=True)
            summary_results.sort(key=date_key, reverse=True)
        except Exception:
            pass

        # Add summary results section
        if summary_results:
            context_parts.append("RELEVANT AGENDA SUMMARIES:")
            for i, result in enumerate(summary_results[:3], 1):
                metadata = result.get("metadata", {})
                document = result.get("document", "")
                context_parts.append(f"\n{i}. Agenda {metadata.get('agenda_number', 'Unknown')} ({metadata.get('source_file', 'Unknown')}):")
                context_parts.append(f"   {document}")

        # Add structured data section
        if json_results:
            context_parts.append("\n\nRELEVANT STRUCTURED DATA:")
            for i, result in enumerate(json_results[:3], 1):
                metadata = result.get("metadata", {})
                document = result.get("document", "")
                context_parts.append(f"\n{i}. Agenda {metadata.get('agenda_number', 'Unknown')}: ")
                context_parts.append(f"   Meeting: {metadata.get('meeting_type', 'Unknown')} on {metadata.get('meeting_date', 'Unknown')}")
                context_parts.append(f"   Organization: {metadata.get('organization', 'Unknown')}")
                context_parts.append(f"   Data: {document}")

        return "\n".join(context_parts)

    def create_bond_context(self, bond_results: List[Dict]) -> str:
        parts: List[str] = []
        if not bond_results:
            return "No bond documents matched."
        parts.append("RELEVANT BOND DOCUMENTS:")
        for i, result in enumerate(bond_results[:5], 1):
            meta = result.get("metadata", {})
            doc = result.get("document", "")
            parts.append(f"\n{i}. {meta.get('source_file', 'Unknown')}")
            parts.append(doc[:800] + ("..." if len(doc) > 800 else ""))
        return "\n".join(parts)

    # -------------------------------
    # Explicit agenda/date helpers
    # -------------------------------
    def extract_agenda_numbers(self, query: str) -> List[int]:
        """Extract explicit agenda numbers mentioned in the user query.
        Matches patterns like 'Agenda 150' or 'agenda 12'. Returns unique ints.
        """
        nums = set()
        for m in re.finditer(r"agenda\s+(\d{1,4})", query, re.IGNORECASE):
            try:
                nums.add(int(m.group(1)))
            except ValueError:
                continue
        return sorted(nums)

    def load_agenda_artifacts(self, agenda_number: int) -> Dict[str, Any]:
        """Load summary / structured data / raw file for a given agenda number if present.
        Returns dict with keys: summary_text, structured_text, metadata.
        """
        summary_file = OUTPUT_DIR / "summaries" / f"summary_{agenda_number}.json"
        json_file = OUTPUT_DIR / "json_data" / f"data_{agenda_number}.json"
        raw_file = Path("Agendas_COR") / f"Agenda_{agenda_number}.txt"
        summary_text = None
        structured_text = None
        metadata: Dict[str, Any] = {"agenda_number": str(agenda_number), "source_file": f"Agenda_{agenda_number}.txt"}
        try:
            if summary_file.exists():
                with open(summary_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    summary_text = data.get("summary")
                    metadata["type"] = "summary"
        except Exception:
            pass
        try:
            if json_file.exists():
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    extracted = data.get("extracted_data", {})
                    meeting_info = extracted.get("meeting_info", {})
                    metadata.update({
                        "meeting_date": meeting_info.get("date"),
                        "meeting_type": meeting_info.get("type"),
                        "organization": meeting_info.get("organization"),
                        "type": "structured_data"
                    })
                    # Build concise structured text snippet similar to embedding text assembly
                    parts = []
                    if meeting_info:
                        parts.append(f"Meeting: {meeting_info.get('type')} on {meeting_info.get('date')} ({meeting_info.get('organization')})")
                    agenda_items = extracted.get("agenda_items", [])
                    if agenda_items:
                        parts.append("Items: " + "; ".join([f"{i.get('item_number')}: {i.get('title')}" for i in agenda_items[:5]]))
                    keywords = extracted.get("keywords", [])
                    if keywords:
                        parts.append("Keywords: " + ", ".join(keywords[:10]))
                    structured_text = " | ".join(parts)
        except Exception:
            pass
        # Fallback to raw text snippet if neither summary nor structured available
        if not summary_text and not structured_text and raw_file.exists():
            try:
                raw = raw_file.read_text(encoding='utf-8', errors='replace')
                summary_text = raw[:1200]
            except Exception:
                pass
        return {"summary_text": summary_text, "structured_text": structured_text, "metadata": metadata}

    def generate_response(self, query: str, context: str) -> str:
        """Generate response using OpenAI with context."""
        try:
            system_prompt = """You are an AI assistant specializing in Dallas city government meeting agendas.
            You help users find and understand information from city council meetings, commission meetings, and committee meetings.

            CORE RULES:
            1. If the user explicitly references an agenda number (e.g. 'Agenda 150', 'agenda 12') you MUST look for that exact agenda in the provided context. If it's not present in context but the filename pattern exists (Agenda_<number>.txt) you should state that it exists in the source corpus but was not included in retrieved context and avoid inventing details.
            2. If the user references a specific date (e.g. 'on March 25, 2025' or an ISO date '2025-03-25'), prioritize meetings on that date in your answer. If no meeting for that date appears in context, say that the date was not found in retrieved records.
            3. NEVER fabricate agenda content. If a requested agenda/date is missing from context, respond with a clear statement that it was not retrieved and suggest re-indexing or confirming embeddings.
            4. Always cite agenda number and file (e.g., "According to Agenda 150 (Agenda_150.txt)...").

            RESPONSE STYLE:
            - Simple factual question: brief, direct answer with citation.
            - Multi-part / analytical: structured bullets or short sections.
            - Always distinguish confirmed facts (from context) from missing data.

            If nothing in context answers the question: clearly say so and do NOT speculate."""
            
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

        # Extract explicit agendas before search
        explicit_agendas = self.extract_agenda_numbers(query)
        recency_mode = self._query_requests_recency(query)

    # Search both collections
        search_start = time.time()
        summary_results = self.search_summaries(query, n_results=5)
        json_results = self.search_structured_data(query, n_results=5)
        search_time = time.time() - search_start

        # Inject explicitly requested agendas if missing from retrieved results
        if explicit_agendas:
            present_agendas = {r['metadata'].get('agenda_number') for r in summary_results} | {r['metadata'].get('agenda_number') for r in json_results}
            for num in explicit_agendas:
                if str(num) not in present_agendas and num not in present_agendas:
                    artifacts = self.load_agenda_artifacts(num)
                    meta_base = artifacts['metadata']
                    # Add summary if available
                    if artifacts['summary_text']:
                        summary_results.append({
                            'document': artifacts['summary_text'],
                            'metadata': {**meta_base, 'injected': True, 'source': 'explicit_agenda'},
                            'distance': 0.4  # heuristic
                        })
                    # Add structured if available
                    if artifacts['structured_text']:
                        json_results.append({
                            'document': artifacts['structured_text'],
                            'metadata': {**meta_base, 'injected': True, 'source': 'explicit_agenda'},
                            'distance': 0.4
                        })

        # Create context
        context_start = time.time()
        context = self.create_context_from_results(summary_results, json_results, recency_mode=recency_mode)
        context_time = time.time() - context_start

        # Generate response
        response_start = time.time()
        response = self.generate_response(query, context)
        response_time = time.time() - response_start

        total_time = time.time() - start_time

        # Extract source files from results
        source_files = self.extract_source_files(summary_results, json_results)

        # If recency_mode, reorder source_files by meeting_date (desc) while preserving existing order fallback
        if recency_mode:
            def src_key(s):
                ag = s.get("agenda_number")
                d = self.agenda_date_map.get(str(ag)) or self._parse_date(s.get("meeting_date"))
                try:
                    return d.toordinal() if d else -1
                except Exception:
                    return -1
            source_files.sort(key=src_key, reverse=True)

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

    def process_bond_query(self, query: str) -> Dict[str, Any]:
        start = time.time()
        results = self.search_bond_documents(query, n_results=8)
        ctx = self.create_bond_context(results)
        # Use LLM for summarization if available, else return context
        if results:
            answer = self.generate_response(query, ctx)
        else:
            answer = "No matching bond documents found."
        return {
            "response": answer,
            "bond_results": results,
            "context": ctx,
            "timing": {"total_time": round(time.time() - start, 2)},
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

    def generate_clarifying_questions(self, query: str) -> List[str]:
        """Generate up to 3 clarifying questions to better understand user intent."""
        try:
            prompt = f"""
You are analyzing a user query about Dallas City agendas and bond documents. 
Generate 0-3 clarifying questions that would help provide a more accurate and useful response.

User Query: "{query}"

Consider these aspects:
- Time period (specific dates, years, recent vs historical)
- Document type (agendas vs bond documents vs both)
- Specific departments or topics
- Level of detail needed (summary vs detailed)
- Specific action items vs general information

Only ask questions if the query is genuinely ambiguous or would benefit from clarification.
If the query is already clear and specific, return an empty list.

Return ONLY a JSON array of question strings, maximum 3 questions.
Example: ["What time period are you interested in?", "Are you looking for approved or proposed items?"]

If no clarification needed, return: []
"""

            response = self.client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=200,
                temperature=0.3
            )
            
            content = response.choices[0].message.content.strip()
            
            # Parse JSON response
            import json
            try:
                questions = json.loads(content)
                if isinstance(questions, list) and len(questions) <= 3:
                    return [q for q in questions if isinstance(q, str) and q.strip()]
            except json.JSONDecodeError:
                pass
            
            return []
            
        except Exception as e:
            logger.error(f"Error generating clarifying questions: {e}")
            return []

    def process_query_with_clarification(self, query: str, clarifications: List[str] = None) -> Dict[str, Any]:
        """Process query with optional clarifications from user."""
        # Combine original query with clarifications
        enhanced_query = query
        if clarifications:
            clarification_text = " ".join([f"Additional context: {c}" for c in clarifications if c.strip()])
            enhanced_query = f"{query} {clarification_text}"
        
        # Use the enhanced query for search and response
        return self.process_query(enhanced_query)

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
    st.markdown("Ask questions about Dallas city government meeting agendas and get informed answers!"
    " But remember, I only have the meeting summaries and structured data available until the end of March 2025 :) ")
    
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
    
    # Chat interface with tabs
    st.markdown("---")
    tabs = st.tabs(["Dallas City Agendas", "Bond Documents"])

    # Dallas City Agendas tab
    with tabs[0]:
        st.markdown("### 🏛️ Search Dallas City Agendas")
        
        # Optional include bonds in general search
        include_bonds = st.checkbox("Include bond documents in search results", value=False)

        # Chat history in main area
        if 'chat_history' not in st.session_state:
            st.session_state.chat_history = []
            
        # Clarifying questions state
        if 'pending_query' not in st.session_state:
            st.session_state.pending_query = None
        if 'clarifying_questions' not in st.session_state:
            st.session_state.clarifying_questions = []
        if 'clarifications' not in st.session_state:
            st.session_state.clarifications = []

        # Display chat history
        for chat in st.session_state.chat_history:
            with st.chat_message("user", avatar="👤"):
                st.markdown(chat['query'])
            with st.chat_message("assistant", avatar="🏛️"):
                st.markdown(_sanitize_markdown_response(chat['result']['response']))
            timing = chat['result']['timing']
            col1, col2, col3, col4 = st.columns(4)
            with col1: st.metric("⏱️ Total Time", f"{timing['total_time']}s")
            with col2: st.metric("🔍 Search", f"{timing['search_time']}s")
            with col3: st.metric("📝 Context", f"{timing['context_time']}s")
            with col4: st.metric("Response", f"{timing['response_time']}s")
            st.caption(f"Query processed at {chat['result']['timestamp']}")

            # Sources
            if chat['result']["source_files"]:
                st.markdown("### 📚 Sources & Original Files")
                for i, source in enumerate(chat['result']["source_files"][:5], 1):
                    with st.expander(f"📄 **{source['source_file']}** (Agenda {source.get('agenda_number','-')})"):
                        st.write(f"• **Original File:** `{source['source_file']}`")

        # Show clarifying questions if any
        if st.session_state.clarifying_questions:
            st.markdown("### 🤔 I'd like to clarify a few things to give you a better answer:")
            
            clarifications = []
            for i, question in enumerate(st.session_state.clarifying_questions):
                st.markdown(f"**{i+1}. {question}**")
                
                # Create text input for each question
                answer = st.text_input(
                    f"Your answer:",
                    key=f"clarification_{i}",
                    placeholder="Type your answer or leave blank to skip..."
                )
                if answer.strip():
                    clarifications.append(answer.strip())
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🚀 Search with clarifications", type="primary"):
                    # Process with clarifications
                    with st.spinner("🔎 Searching with your clarifications..."):
                        result = chatbot.process_query_with_clarification(
                            st.session_state.pending_query, 
                            clarifications
                        )
                        # Optionally augment with bonds
                        if include_bonds:
                            bond_hits = chatbot.search_bond_documents(st.session_state.pending_query, n_results=3)
                            bond_ctx = chatbot.create_bond_context(bond_hits)
                            augmented = chatbot.generate_response(st.session_state.pending_query, result['context'] + "\n\n" + bond_ctx)
                            result['response'] = augmented
                    
                    # Add to chat history
                    display_query = st.session_state.pending_query
                    if clarifications:
                        display_query += f" (with clarifications: {'; '.join(clarifications)})"
                    
                    st.session_state.chat_history.append({'query': display_query, 'result': result})
                    
                    # Clear clarifying questions state
                    st.session_state.pending_query = None
                    st.session_state.clarifying_questions = []
                    st.session_state.clarifications = []
                    st.rerun()
                    
            with col2:
                if st.button("⏭️ Skip clarifications"):
                    # Process without clarifications
                    with st.spinner("🔎 Searching..."):
                        result = chatbot.process_query(st.session_state.pending_query)
                        if include_bonds:
                            bond_hits = chatbot.search_bond_documents(st.session_state.pending_query, n_results=3)
                            bond_ctx = chatbot.create_bond_context(bond_hits)
                            augmented = chatbot.generate_response(st.session_state.pending_query, result['context'] + "\n\n" + bond_ctx)
                            result['response'] = augmented
                    
                    st.session_state.chat_history.append({'query': st.session_state.pending_query, 'result': result})
                    
                    # Clear state
                    st.session_state.pending_query = None
                    st.session_state.clarifying_questions = []
                    st.session_state.clarifications = []
                    st.rerun()

        # Input (only show if no pending clarifications)
        if not st.session_state.clarifying_questions:
            user_query = st.chat_input("Ask a question about Dallas city agendas:", key="agenda_input")
            if user_query:
                # Generate clarifying questions first
                clarifying_questions = chatbot.generate_clarifying_questions(user_query)
                
                if clarifying_questions:
                    # Store the query and questions for clarification
                    st.session_state.pending_query = user_query
                    st.session_state.clarifying_questions = clarifying_questions
                    st.rerun()
                else:
                    # No clarification needed, process directly
                    with st.spinner("🔎 Searching..."):
                        result = chatbot.process_query(user_query)
                        # Optionally augment context with bonds
                        if include_bonds:
                            bond_hits = chatbot.search_bond_documents(user_query, n_results=3)
                            bond_ctx = chatbot.create_bond_context(bond_hits)
                            # Regenerate with bond context appended
                            augmented = chatbot.generate_response(user_query, result['context'] + "\n\n" + bond_ctx)
                            result['response'] = augmented
                    st.session_state.chat_history.append({'query': user_query, 'result': result})
                    st.rerun()

    # Bond Documents tab
    with tabs[1]:
        st.markdown("### 🏛️ Search Bond Documents")
        
        if 'bond_history' not in st.session_state:
            st.session_state.bond_history = []
            
        # Bond-specific clarifying questions state
        if 'bond_pending_query' not in st.session_state:
            st.session_state.bond_pending_query = None
        if 'bond_clarifying_questions' not in st.session_state:
            st.session_state.bond_clarifying_questions = []
            
        for chat in st.session_state.bond_history:
            with st.chat_message("user", avatar="👤"):
                st.markdown(chat['query'])
            with st.chat_message("assistant", avatar="🏛️"):
                st.markdown(_sanitize_markdown_response(chat['result']['response']))
                
        # Show bond clarifying questions if any
        if st.session_state.bond_clarifying_questions:
            st.markdown("### 🤔 I'd like to clarify a few things about your bond document search:")
            
            bond_clarifications = []
            for i, question in enumerate(st.session_state.bond_clarifying_questions):
                st.markdown(f"**{i+1}. {question}**")
                
                answer = st.text_input(
                    f"Your answer:",
                    key=f"bond_clarification_{i}",
                    placeholder="Type your answer or leave blank to skip..."
                )
                if answer.strip():
                    bond_clarifications.append(answer.strip())
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🚀 Search bonds with clarifications", type="primary"):
                    with st.spinner("🔎 Searching bond documents..."):
                        # Enhance query with clarifications
                        enhanced_query = st.session_state.bond_pending_query
                        if bond_clarifications:
                            clarification_text = " ".join([f"Additional context: {c}" for c in bond_clarifications if c.strip()])
                            enhanced_query = f"{st.session_state.bond_pending_query} {clarification_text}"
                        
                        result = chatbot.process_bond_query(enhanced_query)
                    
                    # Add to bond history
                    display_query = st.session_state.bond_pending_query
                    if bond_clarifications:
                        display_query += f" (with clarifications: {'; '.join(bond_clarifications)})"
                    
                    st.session_state.bond_history.append({'query': display_query, 'result': result})
                    
                    # Clear state
                    st.session_state.bond_pending_query = None
                    st.session_state.bond_clarifying_questions = []
                    st.rerun()
                    
            with col2:
                if st.button("⏭️ Skip clarifications", key="bond_skip"):
                    with st.spinner("🔎 Searching bond documents..."):
                        result = chatbot.process_bond_query(st.session_state.bond_pending_query)
                    
                    st.session_state.bond_history.append({'query': st.session_state.bond_pending_query, 'result': result})
                    
                    # Clear state
                    st.session_state.bond_pending_query = None
                    st.session_state.bond_clarifying_questions = []
                    st.rerun()
        
        # Bond input (only show if no pending clarifications)
        if not st.session_state.bond_clarifying_questions:
            bond_query = st.chat_input("Ask a question about bond documents:", key="bond_input")
            if bond_query:
                # Generate clarifying questions for bond search
                clarifying_questions = chatbot.generate_clarifying_questions(f"Bond documents: {bond_query}")
                
                if clarifying_questions:
                    st.session_state.bond_pending_query = bond_query
                    st.session_state.bond_clarifying_questions = clarifying_questions
                    st.rerun()
                else:
                    # No clarification needed, process directly
                    with st.spinner("🔎 Searching bond documents..."):
                        result = chatbot.process_bond_query(bond_query)
                    st.session_state.bond_history.append({'query': bond_query, 'result': result})
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
