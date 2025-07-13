from pydantic_settings import BaseSettings
from dotenv import load_dotenv
import os

load_dotenv()  # Loads variables from .env into environment

class Settings(BaseSettings):
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    VECTOR_DB_DIR: str = "./vector_db"
    OPENAI_API_KEY: str
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

# Validate that API key is provided
try:
    settings = Settings()
    if not settings.OPENAI_API_KEY or settings.OPENAI_API_KEY == "your_openai_api_key_here":
        raise ValueError("Please set your OpenAI API key in the .env file")
except Exception as e:
    print(f"❌ Configuration error: {e}")
    print("💡 Please:")
    print("   1. Get an API key from https://platform.openai.com/api-keys")
    print("   2. Add it to your .env file: OPENAI_API_KEY=your_actual_key_here")
    raise