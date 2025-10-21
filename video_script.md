# Dallas City Agenda Chatbot - Video Demonstration Script
## Total Duration: 5-6 minutes

---

## **INTRO SECTION (0:00 - 0:45)**

### Screen: Desktop/Browser Tab
**Narration:**
"Hi everyone! Today I'm excited to show you an AI-powered chatbot I built that makes Dallas city government meeting data accessible to everyone. This system processes hundreds of city council, committee, and commission meeting agendas, making it easy to find information about city decisions, budget items, development projects, and more."

### Action: Open browser and navigate to Streamlit app
**Narration continues:**
"Let me show you how it works. I've built this using Streamlit, OpenAI's API for natural language processing, and ChromaDB for vector search across over 1,400 documents."

---

## **OVERVIEW & STATISTICS (0:45 - 1:30)**

### Screen: Chatbot main interface
**Narration:**
"Here's the main interface. As you can see, we have 974 summary documents and 973 structured data documents - that's nearly 2,000 pieces of searchable content from Dallas city meetings. The system includes two main tabs: Dallas City Agendas and Bond Documents."

### Point to metrics display
**Narration:**
"The system covers meetings through March 2025, including city council sessions, committee meetings, budget hearings, planning commission meetings, and more. What makes this special is that it doesn't just do keyword search - it uses AI to understand the meaning behind your questions."

---

## **FEATURE 1: CLARIFYING QUESTIONS (1:30 - 2:30)**

### Screen: Type a broad question
**Type:** "What were recent transportation decisions?"

### Screen: Show clarifying questions appearing
**Narration:**
"One unique feature is the clarifying questions system. When I ask a broad question like 'What were recent transportation decisions?', the AI automatically generates up to 3 clarifying questions to help provide more accurate results."

### Screen: Show the clarifying questions
**Narration:**
"Look - it's asking about time period, specific types of decisions, and geographic focus. This helps narrow down the search from hundreds of meetings to exactly what I'm looking for. I can answer these questions or skip them if my original query was specific enough."

### Action: Fill in clarifications or skip
**Example clarifications:** 
- "Last 3 months"
- "Infrastructure projects and funding"
- "Downtown and Oak Cliff areas"

---

## **FEATURE 2: INTELLIGENT SEARCH & RESPONSES (2:30 - 3:45)**

### Screen: Submit the query and show processing
**Narration:**
"Now watch what happens. The system is doing several things simultaneously: generating embeddings for my query, searching through both summary and structured data, ranking results by relevance and recency, and then using GPT to synthesize a comprehensive answer."

### Screen: Show the response with timing metrics
**Narration:**
"Here's the response! Notice the timing metrics - it searched through nearly 2,000 documents in under 2 seconds. The AI provides specific agenda numbers, meeting dates, and cites its sources. This isn't just generic information - these are actual decisions made by Dallas city government."

### Point to sources section
**Narration:**
"Down here, you can see exactly which agenda files the information came from, with similarity scores showing how relevant each source is to your question."

---

## **FEATURE 3: SPECIFIC AGENDA LOOKUP (3:45 - 4:15)**

### Screen: Type a specific agenda query
**Type:** "What was discussed in Agenda 150?"

**Narration:**
"The system is also smart about specific requests. If I ask about a particular agenda number, it automatically retrieves that exact document even if it wasn't in the top similarity results. This ensures you never miss specific information you're looking for."

### Screen: Show the specific agenda response
**Narration:**
"Perfect! It found the exact agenda I requested and provided detailed information about what was discussed in that specific meeting."

---

## **FEATURE 4: BOND DOCUMENTS TAB (4:15 - 4:45)**

### Screen: Switch to Bond Documents tab
**Narration:**
"The system also includes a separate tab for bond documents. This handles a different type of city financial data with its own specialized search."

### Screen: Type a bond-related query
**Type:** "Infrastructure bond funding for transportation projects"

**Narration:**
"Bond documents require different handling since they contain financial and legal information. The system processes these separately and can provide detailed analysis of funding mechanisms, project allocations, and budget implications."

---

## **FEATURE 5: TECHNICAL ARCHITECTURE (4:45 - 5:30)**

### Screen: Show system status in sidebar
**Narration:**
"Let me show you what's happening under the hood. The system uses several advanced technologies working together:"

### Point to different elements
**Narration:**
"First, OpenAI's text-embedding-ada-002 model creates vector representations of all documents. ChromaDB provides fast vector similarity search. GPT-4 generates natural language responses. And the whole thing is built with Python, using Streamlit for the interface."

### Screen: Show example questions in sidebar
**Narration:**
"The sidebar shows example questions across different categories - budget and finance, transportation, development, policy changes. The system handles everything from simple factual questions to complex analytical queries spanning multiple meetings."

---

## **CONCLUSION & IMPACT (5:30 - 6:00)**

### Screen: Navigate back to main interface
**Narration:**
"This system democratizes access to city government information. Instead of manually reading through hundreds of PDF files to understand what the city is doing, residents, journalists, researchers, and city staff can ask natural language questions and get immediate, accurate answers with full source citations."

### Screen: Show the clean interface one more time
**Narration:**
"The entire codebase is clean, modular, and scalable. It could easily be adapted for other cities or government entities. The combination of AI-powered search, intelligent clarification, and comprehensive source citation makes complex government data accessible to everyone."

**Final shot: Fade out on main interface**
**Narration:**
"Thanks for watching! This represents the future of government transparency - making public information truly public and accessible."

---

## **SCREEN RECORDING CHECKLIST**

### Before Recording:
- [ ] Clear browser history/bookmarks for clean appearance
- [ ] Close unnecessary applications
- [ ] Set browser zoom to 100% or 110% for readability
- [ ] Prepare test queries in advance
- [ ] Ensure Streamlit app is running smoothly
- [ ] Test internet connection for API calls

### Recording Settings:
- [ ] 1080p or higher resolution
- [ ] Include cursor in recording
- [ ] Record system audio if needed
- [ ] Use clean desktop background

### Demonstration Queries to Prepare:
1. "What were recent transportation decisions?" (for clarifying questions)
2. "What was discussed in Agenda 150?" (for specific lookup)
3. "Budget items approved in the last council meeting" (for recency)
4. "Infrastructure bond funding for transportation projects" (for bond tab)
5. "Development projects in Deep Ellum" (for location-specific search)

### Key Points to Emphasize:
- ✅ 1,400+ documents processed
- ✅ AI-powered clarifying questions (max 3)
- ✅ Sub-2-second search times
- ✅ Specific agenda number retrieval
- ✅ Source citations with similarity scores
- ✅ Two-tab interface (Agendas + Bonds)
- ✅ Natural language processing
- ✅ Government transparency and accessibility

---

## **POST-PRODUCTION NOTES**

### Editing Tips:
- Add zoom-ins on important UI elements
- Highlight search timing metrics
- Add text overlays for key statistics
- Include smooth transitions between sections
- Consider adding background music (low volume)

### Possible Additions:
- Screen recordings of actual government websites for comparison
- Brief code snippets showing the technology stack
- User testimonials or use cases
- Performance metrics visualization

### Export Settings:
- MP4 format for wide compatibility
- Include captions/subtitles for accessibility
- Optimize for YouTube/LinkedIn sharing