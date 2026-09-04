import os
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # App Settings
    PROJECT_NAME: str = "Heaven_Python API"
    VERSION: str = "1.0.0"
    API_PREFIX: str = "/api"
    PORT: int = 3009
    ENVIRONMENT: str = "development"
    
    # MongoDB Settings
    MONGODB_URI: str = "mongodb://localhost:27017/HavenTo"
    DATABASE_NAME: str = "HavenTo"
    
    # Security & JWT
    JWT_SECRET: str = "havento_jwt_secret_key"
    SESSION_SECRET: str = "havento_session_secret"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    
    # Frontend URLs & CORS
    FRONTEND_URL: str = "http://localhost:5173"
    CORS_ORIGINS: List[str] = [
        "http://localhost",
        "http://localhost:80",
        "http://127.0.0.1",
        "http://127.0.0.1:80",
        "http://localhost:5173",
        "http://localhost:3000",
        "http://localhost:3009",
        "https://havento.vercel.app",
        "https://heaven.vercel.app",
        "https://doubleslash.heaven2.vercel.app",
        "http://127.0.0.1:5173"
    ]
    
    # Email Settings (Gmail OAuth2 & SMTP)
    EMAIL_USER: Optional[str] = None
    EMAIL_PASS: Optional[str] = None
    GMAIL_CLIENT_ID: Optional[str] = None
    GMAIL_CLIENT_SECRET: Optional[str] = None
    GMAIL_REFRESH_TOKEN: Optional[str] = None
    
    # AI Keys (Groq & Gemini)
    GROQ_API_KEY: Optional[str] = None
    GEMINI_API_KEY: Optional[str] = None
    
    # Upload Directories
    UPLOAD_DIR: str = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static", "uploads")
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
