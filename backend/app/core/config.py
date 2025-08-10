"""
Application configuration settings.
"""

import os
from typing import List, Optional

from pydantic import validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""

    # Application
    DEBUG: bool = False
    ENVIRONMENT: str = "development"
    SECRET_KEY: str
    ALLOWED_HOSTS: List[str] = ["localhost", "127.0.0.1"]
    CORS_ORIGINS: List[str] = ["http://localhost:3000"]

    # Database
    DATABASE_URL: str
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20
    DATABASE_POOL_TIMEOUT: int = 30
    DATABASE_POOL_RECYCLE: int = 3600
    DATABASE_QUERY_TIMEOUT: int = 60
    DATABASE_SLOW_QUERY_THRESHOLD: float = 0.1  # 100ms

    # Redis
    REDIS_URL: str = "redis://localhost:6379"

    # JWT
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # External APIs
    ALPHA_VANTAGE_API_KEY: Optional[str] = None
    GOOGLE_GEMINI_API_KEY: Optional[str] = None
    NEWS_API_KEY: Optional[str] = None

    # OAuth
    GOOGLE_CLIENT_ID: Optional[str] = None
    GOOGLE_CLIENT_SECRET: Optional[str] = None
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/api/v1/oauth/callback/google"
    LINE_CLIENT_ID: Optional[str] = None
    LINE_CLIENT_SECRET: Optional[str] = None
    LINE_REDIRECT_URI: str = "http://localhost:8000/api/v1/oauth/callback/line"

    # Frontend URL for redirects
    FRONTEND_URL: str = "http://localhost:3000"

    # Email
    SENDGRID_API_KEY: Optional[str] = None
    FROM_EMAIL: str = "noreply@kessan.com"
    FROM_NAME: str = "Project Kessan"
    SUPPORT_EMAIL: str = "support@kessan.com"

    # SMTP settings (alternative to SendGrid)
    SMTP_SERVER: str = "localhost"
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""

    # Cost Control
    DAILY_AI_BUDGET_USD: float = 100.0
    MONTHLY_AI_BUDGET_USD: float = 2500.0

    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 60
    RATE_LIMIT_PER_HOUR: int = 1000

    # Alerting
    SLACK_WEBHOOK_URL: Optional[str] = None
    PAGERDUTY_INTEGRATION_KEY: Optional[str] = None
    ENABLE_ERROR_ALERTING: bool = True
    ENABLE_GRACEFUL_DEGRADATION: bool = True

    # Datadog APM
    DD_SERVICE: str = "kessan-backend"
    DD_ENV: Optional[str] = None
    DD_VERSION: str = "1.0.0"
    DD_TRACE_ENABLED: bool = False
    DD_AGENT_HOST: Optional[str] = None
    DD_TRACE_AGENT_PORT: int = 8126
    DD_LOGS_INJECTION: bool = True
    DD_PROFILING_ENABLED: bool = False

    @validator("CORS_ORIGINS", pre=True)
    def assemble_cors_origins(cls, v):
        if isinstance(v, str):
            return [i.strip() for i in v.split(",")]
        return v

    @validator("ALLOWED_HOSTS", pre=True)
    def assemble_allowed_hosts(cls, v):
        if isinstance(v, str):
            return [i.strip() for i in v.split(",")]
        return v

    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings()
