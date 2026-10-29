"""Configuration settings for RepoGuard AI."""

import os
from pathlib import Path
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Load .env if present
load_dotenv()

class Settings(BaseModel):
    """RepoGuard runtime configuration."""
    
    # Nebius AI Studio settings
    nebius_api_key: str = Field(
        default_factory=lambda: os.getenv("NEBIUS_API_KEY", "")
    )
    nebius_base_url: str = Field(
        default_factory=lambda: os.getenv("NEBIUS_BASE_URL", "https://api.studio.nebius.ai/v1")
    )
    nebius_model: str = Field(
        default_factory=lambda: os.getenv("NEBIUS_MODEL", "nvidia/Llama-3.1-Nemotron-70B-Instruct-HF")
    )
    
    # GitHub Integration
    github_token: str = Field(
        default_factory=lambda: os.getenv("GITHUB_TOKEN", "")
    )
    github_webhook_secret: str = Field(
        default_factory=lambda: os.getenv("GITHUB_WEBHOOK_SECRET", "")
    )
    
    # Agent & Reflection Loop settings
    max_reflection_attempts: int = Field(
        default_factory=lambda: int(os.getenv("MAX_REFLECTION_ATTEMPTS", "3"))
    )
    sandbox_timeout_seconds: int = Field(
        default_factory=lambda: int(os.getenv("SANDBOX_TIMEOUT_SECONDS", "60"))
    )
    sandbox_mode: str = Field(
        default_factory=lambda: os.getenv("SANDBOX_MODE", "subprocess")
    )
    
    # Storage and paths
    base_dir: Path = Field(
        default_factory=lambda: Path(__file__).resolve().parent.parent
    )
    
    @property
    def is_nebius_configured(self) -> bool:
        """Check if a valid Nebius API key is provided."""
        return bool(self.nebius_api_key and not self.nebius_api_key.startswith("your-"))


# Global settings singleton
settings = Settings()
