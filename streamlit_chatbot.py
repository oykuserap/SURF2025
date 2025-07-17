"""
Streamlit UI for the Enhanced City of Richardson Council Meeting Chatbot
"""
import streamlit as st
import os
import sys
import time
from pathlib import Path

# Add the current directory to the Python path
sys.path.append(str(Path(__file__).parent))

# Disable ChromaDB telemetry
os.environ["CHROMA_TELEMETRY_ENABLED"] = "false"
os.environ["ANONYMIZED_TELEMETRY"] = "false"

from enhanced_chatbot import EnhancedDocumentChatbot

# Set page config
st.set_page_config(
    page_title="City of Richardson Council Meeting Chatbot",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #1e3c72 0%, #2a5298 100%);
        padding: 1rem;
        border-radius: 10px;
        margin-bottom: 2rem;
    }
    .main-header h1 {
        color: white;
        margin-bottom: 0;
        text-align: center;
    }
    .stats-container {
        background: #f8f9fa;
        padding: 1rem;
        border-radius: 8px;
        margin-bottom: 1rem;
    }
    .source-item {
        background: #e9ecef;
        padding: 0.5rem;
        border-radius: 5px;
        margin-bottom: 0.5rem;
        border-left: 4px solid #007bff;
    }
    .response-time {
        color: #28a745;
        font-weight: bold;
    }
    .stTextInput > div > div > input {
        background-color: #ffffff;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'chatbot' not in st.session_state:
    with st.spinner("🔄 Loading enhanced chatbot..."):
        st.session_state.chatbot = EnhancedDocumentChatbot()

if 'messages' not in st.session_state:
    st.session_state.messages = []

# Main header
st.markdown("""
<div class="main-header">
    <h1>🏛️ City of Richardson Council Meeting Chatbot</h1>
    <p style="color: #e9ecef; text-align: center; margin-bottom: 0;">
        Powered by structured meeting data with enhanced search capabilities
    </p>
</div>
""", unsafe_allow_html=True)

# Sidebar with stats and capabilities
with st.sidebar:
    st.header("📊 Database Stats")
    
    if st.session_state.chatbot.json_data:
        stats = st.session_state.chatbot.get_meeting_stats()
        
        # Parse the stats string to extract values
        stats_lines = stats.split('\n')
        for line in stats_lines:
            if 'Total meetings:' in line:
                total_meetings = line.split(':')[1].strip()
                st.metric("Total Meetings", total_meetings)
            elif 'Date range:' in line:
                date_range = line.split(':', 1)[1].strip()
                st.metric("Date Range", date_range)
            elif 'Total financial impact:' in line:
                financial_impact = line.split(':', 1)[1].strip()
                st.metric("Total Financial Impact", financial_impact)
    
    st.header("💡 Enhanced Capabilities")
    st.write("""
    - **Search by date**: "What happened in April 2025?"
    - **Find by attendee**: "Which meetings did John Smith attend?"
    - **Financial analysis**: "What are the largest budget items?"
    - **Topic tracking**: "Show me all infrastructure projects"
    - **Trend analysis**: "What are the recurring themes?"
    """)
    
    st.header("📝 Example Questions")
    example_questions = [
        "What specific zoning changes were discussed in March 2025, and what was their financial impact?",
        "Provide a comprehensive summary of all housing-related initiatives from the past year",
        "What are the major infrastructure projects planned, including budgets and timelines?",
        "How has the city's approach to public safety evolved based on recent council discussions?",
        "What are the largest budget allocations across all departments, and how do they compare to previous years?",
        "Summarize all environmental and sustainability initiatives discussed in council meetings"
    ]
    
    for question in example_questions:
        if st.button(f"💬 {question}", key=f"example_{hash(question)}", use_container_width=True):
            st.session_state.current_question = question

# Main chat interface
st.header("💬 Chat Interface")

# Display chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        
        # Display sources if available
        if message["role"] == "assistant" and "sources" in message:
            st.markdown("---")
            st.markdown(f"**📚 Sources** (Response time: {message['response_time']:.2f} seconds)")
            
            for i, source_info in enumerate(message["sources"], 1):
                st.markdown(f"""
                <div class="source-item">
                    <strong>{i}.</strong> {source_info}
                </div>
                """, unsafe_allow_html=True)

# Chat input
if prompt := st.chat_input("Ask me about City of Richardson council meetings..."):
    st.session_state.current_question = prompt

# Handle example button clicks
if hasattr(st.session_state, 'current_question'):
    prompt = st.session_state.current_question
    delattr(st.session_state, 'current_question')
    
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # Display user message
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Get bot response
    with st.chat_message("assistant"):
        with st.spinner("🤔 Analyzing structured data..."):
            result = st.session_state.chatbot.get_answer(prompt)
        
        # Display the answer with enhanced formatting
        st.markdown(result["answer"])
        
        # Add analysis summary if sources are available
        if result["sources"]:
            st.markdown("---")
            
            # Response time and source count
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"**⏱️ Response Time:** {result['response_time']:.2f} seconds")
            with col2:
                st.markdown(f"**📄 Sources Found:** {len(result['sources'])} documents")
            
            # Source breakdown
            st.markdown("**📚 Source Details:**")
            
            source_summaries = st.session_state.chatbot.create_source_summary(result["sources"][:8])
            
            for i, summary in enumerate(source_summaries, 1):
                # Clean up the summary format for display
                clean_summary = summary.strip().replace(f"   {i}. ", "")
                st.markdown(f"""
                <div class="source-item">
                    <strong>{i}.</strong> {clean_summary}
                </div>
                """, unsafe_allow_html=True)
            
            if len(result["sources"]) > 8:
                st.markdown(f"*... and {len(result['sources']) - 8} more sources*")
            
            # Add expandable section for additional context
            with st.expander("🔍 Additional Context"):
                # Show meeting types and dates from sources
                meeting_types = set()
                dates = set()
                for source in result["sources"]:
                    metadata = source.metadata
                    if metadata.get('meeting_type'):
                        meeting_types.add(metadata['meeting_type'])
                    if metadata.get('date'):
                        dates.add(metadata['date'])
                
                if meeting_types:
                    st.markdown(f"**Meeting Types:** {', '.join(sorted(meeting_types))}")
                if dates:
                    sorted_dates = sorted([d for d in dates if d])
                    if sorted_dates:
                        st.markdown(f"**Date Range:** {sorted_dates[0]} to {sorted_dates[-1]}")
                
                # Show financial impact summary if relevant
                total_financial = 0
                financial_items = 0
                for source in result["sources"]:
                    metadata = source.metadata
                    if metadata.get('financial_impact'):
                        try:
                            total_financial += float(metadata['financial_impact'])
                            financial_items += 1
                        except:
                            pass
                
                if financial_items > 0:
                    st.markdown(f"**Financial Impact:** ${total_financial:,.2f} across {financial_items} items")
    
    # Add assistant response to chat history
    source_summaries = st.session_state.chatbot.create_source_summary(result["sources"][:8])
    st.session_state.messages.append({
        "role": "assistant", 
        "content": result["answer"],
        "sources": source_summaries,
        "response_time": result["response_time"]
    })

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #6c757d; margin-top: 2rem;">
    <p>🤖 Enhanced RAG Chatbot for City of Richardson Council Meetings</p>
    <p>Powered by OpenAI, LangChain, and ChromaDB</p>
</div>
""", unsafe_allow_html=True)
