"""
Configuration settings for the agenda processing pipeline.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# API Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Paths
BASE_DIR = Path(__file__).parent
AGENDAS_DIR = BASE_DIR / "Agendas_COR"
OUTPUT_DIR = BASE_DIR / "processed_data"
VECTOR_DB_DIR = BASE_DIR / "vector_db"
BOND_DIR = BASE_DIR / "bond_data"

# Processing Configuration
BATCH_SIZE = 5  # Number of files to process at once
MAX_TOKENS = 4000  # Maximum tokens for OpenAI API calls

# Model Configuration
OPENAI_MODEL = "gpt-4o-mini"  # Cost-effective model for processing
EMBEDDING_MODEL = "text-embedding-3-small"  # Embedding model

# Create output directories if they don't exist
OUTPUT_DIR.mkdir(exist_ok=True)
VECTOR_DB_DIR.mkdir(exist_ok=True)
(OUTPUT_DIR / "summaries").mkdir(exist_ok=True)
(OUTPUT_DIR / "json_data").mkdir(exist_ok=True)
