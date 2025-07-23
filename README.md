# Dallas City Agenda Processing Pipeline 🏛️

An AI-powered system for processing, analyzing, and querying Dallas city government meeting agendas. This pipeline transforms raw agenda text files into a searchable knowledge base using LLM summaries, structured data extraction, vector embeddings, and an interactive chatbot.

## 🌟 Features

- **LLM Summaries**: Generate concise summaries of meeting agendas using OpenAI GPT
- **Structured Data Extraction**: Extract dates, attendees, agenda items, and keywords into JSON format
- **Vector Embeddings**: Create searchable embeddings using OpenAI's embedding models
- **Interactive Chatbot**: Natural language interface to query agenda information
- **Scalable Processing**: Batch processing with progress tracking and error handling

## 📁 Project Structure

```
SURF2025/
├── Agendas_COR/              # Source agenda text files
├── processed_data/           # Generated summaries and JSON data
│   ├── summaries/           # LLM-generated summaries
│   └── json_data/           # Structured data extractions
├── vector_db/               # ChromaDB vector database
├── config.py                # Configuration settings
├── utils.py                 # Utility functions
├── summary_generator.py     # Step 1: Generate summaries
├── json_extractor.py        # Step 2: Extract structured data
├── embedding_generator.py   # Step 3: Create vector embeddings
├── chatbot.py              # Step 4: Interactive chatbot interface
├── main.py                 # Pipeline orchestrator
└── requirements.txt        # Python dependencies
```

## 🚀 Quick Start

### 1. Setup Environment

```bash
# Clone and navigate to the project
cd SURF2025

# Install dependencies
pip install -r requirements.txt

# Set up your OpenAI API key in .env file
echo "OPENAI_API_KEY=your_api_key_here" > .env
```

### 2. Run the Pipeline

```bash
# Check current status
python main.py --status

# Run the complete pipeline
python main.py --step full

# Or run individual steps
python main.py --step summaries    # Generate summaries
python main.py --step json         # Extract structured data  
python main.py --step embeddings   # Create vector embeddings
```

### 3. Use the Chatbot

```bash
# Start the interactive chatbot
streamlit run chatbot.py
```

Then open your browser to `http://localhost:8501` and start asking questions!

## 💬 Example Queries

- "What meetings were held in March 2025?"
- "Tell me about TIF district funding decisions"
- "What transportation projects were discussed?"
- "Show me meetings about budget approvals"
- "What are the recent landmark commission activities?"

## 🔧 Configuration

Key settings in `config.py`:

- **OPENAI_MODEL**: GPT model for processing (default: "gpt-4o-mini")
- **EMBEDDING_MODEL**: Embedding model (default: "text-embedding-3-small")
- **BATCH_SIZE**: Number of files to process at once
- **MAX_TOKENS**: Maximum tokens for API calls

## 📊 Pipeline Details

### Step 1: Summary Generation
- Processes raw agenda text files from `Agendas_COR/`
- Uses OpenAI GPT to generate 150-300 word summaries
- Saves summaries as JSON files with metadata

### Step 2: JSON Extraction  
- Extracts structured data: dates, attendees, agenda items, keywords
- Uses LLM prompting for accurate data extraction
- Includes financial items and meeting metadata

### Step 3: Embedding Generation
- Creates vector embeddings for summaries and structured data
- Uses ChromaDB for persistent vector storage
- Enables semantic search capabilities

### Step 4: Interactive Chatbot
- Streamlit-based web interface
- Combines vector search with LLM generation
- Provides source citations and similarity scores

## 🛠️ Development

### Testing with Limited Data
```bash
# Process only first 5 files for testing
python main.py --step full --limit 5
```

### Checking Logs
Logs are written to `pipeline.log` and displayed in the console.

### Extending the System
- Add new data extractors in `json_extractor.py`
- Modify summary prompts in `summary_generator.py`
- Customize chatbot responses in `chatbot.py`

## 📈 Performance

- **Processing Speed**: ~30 seconds per agenda file
- **Cost**: ~$0.01-0.05 per agenda file (OpenAI API)
- **Storage**: ~1MB per 100 processed agendas
- **Search Speed**: Sub-second semantic search

## 🔍 Troubleshooting

### Common Issues

1. **"Vector database not found"**
   ```bash
   python main.py --step embeddings
   ```

2. **"OpenAI API key not found"**
   - Check your `.env` file
   - Ensure the key starts with `sk-`

3. **"No agenda files found"**
   - Verify files are in `Agendas_COR/` directory
   - Check file naming pattern: `Agenda_*.txt`

## 📄 License

This project is part of the SURF 2025 research program.