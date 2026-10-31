"""Prisma STT client for Gnani AI."""

import base64
import time
from typing import Optional
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.core.config import get_settings
from app.core.exceptions import PrismaError
from app.models.schemas import PrismaTranscriptionRequest, PrismaTranscriptionResponse
from app.models.enums import Language


class PrismaClient:
    """Client for Gnani AI Prisma Speech-to-Text API."""
    
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        self.settings = get_settings()
        self.api_key = api_key or self.settings.gnani_api_key
        self.base_url = (base_url or self.settings.gnani_base_url).rstrip("/")
        
        if not self.api_key:
            raise PrismaError("API key not configured")
        
        self._client: Optional[httpx.AsyncClient] = None
    
    @property
    def client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                timeout=httpx.Timeout(60.0, connect=10.0),
            )
        return self._client
    
    async def close(self):
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
    
    @retry(
        wait=wait_exponential(multiplier=1, min=1, max=10),
        stop=stop_after_attempt(3),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError)),
    )
    async def transcribe(
        self,
        audio_base64: str,
        language: Language = Language.AUTO,
        enable_diarization: bool = False,
        noise_reduction: bool = True,
    ) -> PrismaTranscriptionResponse:
        """
        Transcribe audio using Prisma STT.
        
        Args:
            audio_base64: Base64 encoded audio data
            language: Language code or 'auto' for detection
            enable_diarization: Enable speaker diarization
            noise_reduction: Enable noise reduction
            
        Returns:
            PrismaTranscriptionResponse with transcript and metadata
        """
        start_time = time.perf_counter()
        
        payload = {
            "audio": audio_base64,
            "language": language.value,
            "enable_diarization": enable_diarization,
            "noise_reduction": noise_reduction,
            "timestamp": True,
        }
        
        try:
            response = await self.client.post("/prisma/transcribe", json=payload)
            response.raise_for_status()
            data = response.json()
            
            processing_time = int((time.perf_counter() - start_time) * 1000)
            
            return PrismaTranscriptionResponse(
                text=data.get("text", ""),
                language=Language(data.get("language", "auto")),
                confidence=data.get("confidence", 0.0),
                duration_seconds=data.get("duration_seconds", 0.0),
                processing_time_ms=processing_time,
                words=data.get("words"),
                segments=data.get("segments"),
            )
            
        except httpx.HTTPStatusError as e:
            raise PrismaError(
                f"Transcription failed: {e.response.text}",
                status_code=e.response.status_code,
                response_data=e.response.json() if e.response.content else None,
            )
        except Exception as e:
            raise PrismaError(f"Transcription error: {str(e)}")
    
    async def transcribe_file(
        self,
        file_path: str,
        language: Language = Language.AUTO,
        enable_diarization: bool = False,
        noise_reduction: bool = True,
    ) -> PrismaTranscriptionResponse:
        """Transcribe audio from a file path."""
        import base64
        
        with open(file_path, "rb") as f:
            audio_base64 = base64.b64encode(f.read()).decode("utf-8")
        
        return await self.transcribe(
            audio_base64=audio_base64,
            language=language,
            enable_diarization=enable_diarization,
            noise_reduction=noise_reduction,
        )
    
    async def health_check(self) -> bool:
        """Check if Prisma service is available."""
        try:
            response = await self.client.get("/prisma/health", timeout=5.0)
            return response.status_code == 200
        except Exception:
            return False