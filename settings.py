from pydantic_settings import BaseSettings
from dotenv import load_dotenv
import os

load_dotenv()  # Loads variables from .env into environment

class Settings(BaseSettings):
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    VECTOR_DB_DIR: str = "./vector_db"
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY")  # Get from environment

settings = Settings()