"""Pydantic models for API requests and responses."""

import base64
import binascii
from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field, ConfigDict, field_validator
from datetime import datetime, timezone

from app.models.enums import Language, Intent, Sentiment, ResolutionAction, VoiceType, AudioFormat, BotMode

# Decoded-audio ceiling, kept in sync with Settings.max_audio_size_mb default (25 MB).
MAX_AUDIO_BYTES = 25 * 1024 * 1024


def _utcnow() -> datetime:
    """Timezone-aware UTC now (datetime.utcnow is deprecated)."""
    return datetime.now(timezone.utc)


class PrismaTranscriptionRequest(BaseModel):
    """Request for Prisma STT transcription."""
    
    model_config = ConfigDict(populate_by_name=True)
    
    language: Language = Field(default=Language.AUTO, description="Language code or 'auto'")
    enable_diarization: bool = Field(default=False, description="Enable speaker diarization")
    noise_reduction: bool = Field(default=True, description="Enable noise reduction")
    timestamp: bool = Field(default=True, description="Include word-level timestamps")


class PrismaTranscriptionResponse(BaseModel):
    """Response from Prisma STT transcription."""
    
    model_config = ConfigDict(populate_by_name=True)
    
    text: str = Field(..., description="Transcribed text")
    language: Language = Field(..., description="Detected language")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Overall confidence score")
    duration_seconds: float = Field(..., description="Audio duration in seconds")
    processing_time_ms: int = Field(..., description="Processing time in milliseconds")
    words: Optional[List[Dict[str, Any]]] = Field(default=None, description="Word-level timestamps")
    segments: Optional[List[Dict[str, Any]]] = Field(default=None, description="Speaker segments if diarization enabled")


class EvonReasoningRequest(BaseModel):
    """Request for Evon reasoning."""
    
    model_config = ConfigDict(populate_by_name=True)
    
    transcript: str = Field(..., description="Transcribed text from Prisma")
    language: Language = Field(..., description="Language of the transcript")
    context: Optional[Dict[str, Any]] = Field(default=None, description="Additional context (customer info, order history, etc.)")
    conversation_history: Optional[List[Dict[str, str]]] = Field(default=None, description="Previous conversation turns")


class EvonReasoningResponse(BaseModel):
    """Response from Evon reasoning."""
    
    model_config = ConfigDict(populate_by_name=True)
    
    intent: Intent = Field(..., description="Detected intent")
    sentiment: Sentiment = Field(..., description="Customer sentiment")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Reasoning confidence")
    resolution: ResolutionAction = Field(..., description="Recommended resolution action")
    response_text: str = Field(..., description="Natural language response for the customer")
    extracted_entities: Dict[str, Any] = Field(default_factory=dict, description="Extracted entities (order IDs, amounts, etc.)")
    reasoning_trace: Optional[str] = Field(default=None, description="Step-by-step reasoning")
    processing_time_ms: int = Field(..., description="Processing time in milliseconds")


class TimbreSynthesisRequest(BaseModel):
    """Request for Timbre TTS synthesis."""
    
    model_config = ConfigDict(populate_by_name=True)
    
    text: str = Field(..., description="Text to synthesize")
    language: Language = Field(..., description="Language for synthesis")
    voice: VoiceType = Field(default=VoiceType.FEMALE_WARM, description="Voice type")
    sample_rate: int = Field(default=22050, description="Output sample rate")
    speed: float = Field(default=1.0, ge=0.5, le=2.0, description="Speech speed")
    pitch: float = Field(default=1.0, ge=0.5, le=2.0, description="Speech pitch")


class TimbreSynthesisResponse(BaseModel):
    """Response from Timbre TTS synthesis."""
    
    model_config = ConfigDict(populate_by_name=True)
    
    audio_base64: str = Field(..., description="Base64 encoded audio data")
    format: str = Field(default="wav", description="Audio format")
    sample_rate: int = Field(..., description="Sample rate")
    duration_seconds: float = Field(..., description="Audio duration")
    processing_time_ms: int = Field(..., description="Processing time in milliseconds")


class SupportBotRequest(BaseModel):
    """Unified request for the support bot pipeline."""

    model_config = ConfigDict(populate_by_name=True)

    audio_base64: str = Field(..., min_length=1, description="Base64 encoded audio input")
    audio_format: Literal["wav", "mp3", "flac", "ogg", "m4a", "aac", "opus"] = Field(
        default="wav", description="Audio container format"
    )
    language: Language = Field(default=Language.AUTO, description="Expected language or 'auto'")
    mode: BotMode = Field(default=BotMode.SUPPORT, description="Bot operating mode (support or translate)")
    session_id: Optional[str] = Field(default=None, max_length=64, description="Session ID for conversation continuity")
    context: Optional[Dict[str, Any]] = Field(default=None, description="Additional context")

    @field_validator("audio_base64")
    @classmethod
    def validate_audio_base64(cls, value: str) -> str:
        """Reject payloads that are not valid base64 or exceed the decoded-size ceiling."""
        try:
            decoded = base64.b64decode(value, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise ValueError("audio_base64 is not valid base64 data") from exc
        if len(decoded) > MAX_AUDIO_BYTES:
            raise ValueError(f"decoded audio exceeds {MAX_AUDIO_BYTES // (1024 * 1024)} MB limit")
        return value


class SupportBotResponse(BaseModel):
    """Unified response from the support bot pipeline."""
    
    model_config = ConfigDict(populate_by_name=True)
    
    session_id: str = Field(..., description="Session ID")
    transcript: str = Field(..., description="Transcribed text")
    detected_language: Language = Field(..., description="Detected language")
    intent: Intent = Field(..., description="Detected intent")
    sentiment: Sentiment = Field(..., description="Customer sentiment")
    resolution: ResolutionAction = Field(..., description="Resolution action")
    response_text: str = Field(..., description="Bot response text")
    response_audio_base64: str = Field(..., description="Base64 encoded response audio")
    latency_breakdown: Dict[str, int] = Field(..., description="Latency per stage in ms")
    total_latency_ms: int = Field(..., description="Total pipeline latency")
    timestamp: datetime = Field(default_factory=_utcnow, description="Response timestamp")


class HealthCheckResponse(BaseModel):
    """Health check response."""
    
    model_config = ConfigDict(populate_by_name=True)
    
    status: Literal["healthy", "degraded", "unhealthy"]
    version: str = "0.1.0"
    services: Dict[str, Literal["up", "down", "unknown"]]
    timestamp: datetime = Field(default_factory=_utcnow)


class ErrorResponse(BaseModel):
    """Standard error response."""
    
    model_config = ConfigDict(populate_by_name=True)
    
    error: str
    detail: str
    service: Optional[str] = None
    timestamp: datetime = Field(default_factory=_utcnow)