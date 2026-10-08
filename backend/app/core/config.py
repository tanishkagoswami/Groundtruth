from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # API Keys
    GROQ_API_KEY: str
    GITHUB_TOKEN: str
    SEMANTIC_SCHOLAR_API_KEY: str = "" # Optional, but higher rate limits if you have one
    
    # Database Config
    MONGODB_URI: str = "mongodb://localhost:27017"
    MONGO_DB_NAME: str = "relevance_engine"

    class Config:
        env_file = ".env"

# Instantiate once to be used across the app
settings = Settings()