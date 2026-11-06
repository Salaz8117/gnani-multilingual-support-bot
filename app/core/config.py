"""Application configuration management."""

from functools import lru_cache
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )
    
    # Gnani AI API
    gnani_api_key: str = Field(default="", alias="GNANI_API_KEY")
    gnani_base_url: str = Field(default="https://api.gnani.ai/v1", alias="GNANI_BASE_URL")
    
    # Application
    app_env: str = Field(default="development", alias="APP_ENV")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    debug: bool = Field(default=True, alias="DEBUG")
    
    # Audio
    max_audio_size_mb: int = Field(default=25, alias="MAX_AUDIO_SIZE_MB")
    supported_audio_formats: str = Field(default="wav,mp3,m4a,ogg,flac", alias="SUPPORTED_AUDIO_FORMATS")
    sample_rate: int = Field(default=16000, alias="SAMPLE_RATE")
    
    # Prisma (STT)
    prisma_default_language: str = Field(default="auto", alias="PRISMA_DEFAULT_LANGUAGE")
    prisma_enable_diarization: bool = Field(default=False, alias="PRISMA_ENABLE_DIARIZATION")
    prisma_noise_reduction: bool = Field(default=True, alias="PRISMA_NOISE_REDUCTION")
    
    # Evon (Reasoning)
    evon_model: str = Field(default="evon-30b", alias="EVON_MODEL")
    evon_temperature: float = Field(default=0.3, alias="EVON_TEMPERATURE")
    evon_max_tokens: int = Field(default=1024, alias="EVON_MAX_TOKENS")
    evon_system_prompt_path: str = Field(default="assets/prompts/support_bot_system.txt", alias="EVON_SYSTEM_PROMPT_PATH")
    
    # Timbre (TTS)
    timbre_default_voice: str = Field(default="female_warm", alias="TIMBRE_DEFAULT_VOICE")
    timbre_default_language: str = Field(default="hi-IN", alias="TIMBRE_DEFAULT_LANGUAGE")
    timbre_sample_rate: int = Field(default=22050, alias="TIMBRE_SAMPLE_RATE")
    
    # Demo
    demo_port: int = Field(default=7860, alias="DEMO_PORT")
    api_port: int = Field(default=8000, alias="API_PORT")

    # Twilio (optional)
    twilio_account_sid: Optional[str] = Field(default=None, alias="TWILIO_ACCOUNT_SID")
    twilio_auth_token: Optional[str] = Field(default=None, alias="TWILIO_AUTH_TOKEN")
    twilio_phone_number: Optional[str] = Field(default=None, alias="TWILIO_PHONE_NUMBER")
    
    # Redis (optional)
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")
    session_ttl_seconds: int = Field(default=3600, alias="SESSION_TTL_SECONDS")
    
    # CORS — comma-separated explicit origins; never pair "*" with credentials
    cors_origins: str = Field(
        default="http://localhost:3000,http://localhost:7860",
        alias="CORS_ORIGINS",
    )
    
    @property
    def supported_formats_list(self) -> list[str]:
        return [fmt.strip() for fmt in self.supported_audio_formats.split(",")]
    
    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Get cached settings instance. Call reset_settings() in tests that patch env vars."""
    return Settings()


def reset_settings() -> None:
    """Clear the cached Settings so a fresh one is built from the current environment."""
    get_settings.cache_clear()
