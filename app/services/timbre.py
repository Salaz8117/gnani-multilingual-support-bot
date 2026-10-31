"""Timbre TTS client for Gnani AI."""

import base64
import time
from typing import Optional
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.core.config import get_settings
from app.core.exceptions import TimbreError
from app.models.schemas import TimbreSynthesisRequest, TimbreSynthesisResponse
from app.models.enums import Language, VoiceType


class TimbreClient:
    """Client for Gnani AI Timbre Text-to-Speech API."""
    
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        self.settings = get_settings()
        self.api_key = api_key or self.settings.gnani_api_key
        self.base_url = (base_url or self.settings.gnani_base_url).rstrip("/")
        
        if not self.api_key:
            raise TimbreError("API key not configured")
        
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
    async def synthesize(
        self,
        text: str,
        language: Language,
        voice: VoiceType = VoiceType.FEMALE_WARM,
        sample_rate: int = 22050,
        speed: float = 1.0,
        pitch: float = 1.0,
    ) -> TimbreSynthesisResponse:
        """
        Synthesize speech using Timbre TTS.
        
        Args:
            text: Text to synthesize
            language: Language for synthesis
            voice: Voice type
            sample_rate: Output sample rate
            speed: Speech speed (0.5-2.0)
            pitch: Speech pitch (0.5-2.0)
            
        Returns:
            TimbreSynthesisResponse with base64 encoded audio
        """
        start_time = time.perf_counter()
        
        payload = {
            "text": text,
            "language": language.value,
            "voice": voice.value,
            "sample_rate": sample_rate,
            "speed": speed,
            "pitch": pitch,
        }
        
        try:
            response = await self.client.post("/timbre/synthesize", json=payload)
            response.raise_for_status()
            data = response.json()
            
            processing_time = int((time.perf_counter() - start_time) * 1000)
            
            # Handle both base64 and direct audio URL responses
            audio_base64 = data.get("audio_base64") or data.get("audio", "")
            
            return TimbreSynthesisResponse(
                audio_base64=audio_base64,
                format=data.get("format", "wav"),
                sample_rate=data.get("sample_rate", sample_rate),
                duration_seconds=data.get("duration_seconds", 0.0),
                processing_time_ms=processing_time,
            )
            
        except httpx.HTTPStatusError as e:
            raise TimbreError(
                f"Synthesis failed: {e.response.text}",
                status_code=e.response.status_code,
                response_data=e.response.json() if e.response.content else None,
            )
        except Exception as e:
            raise TimbreError(f"Synthesis error: {str(e)}")
    
    async def synthesize_to_file(
        self,
        text: str,
        output_path: str,
        language: Language,
        voice: VoiceType = VoiceType.FEMALE_WARM,
        sample_rate: int = 22050,
        speed: float = 1.0,
        pitch: float = 1.0,
    ) -> TimbreSynthesisResponse:
        """Synthesize speech and save to file."""
        response = await self.synthesize(
            text=text,
            language=language,
            voice=voice,
            sample_rate=sample_rate,
            speed=speed,
            pitch=pitch,
        )
        
        import base64
        audio_bytes = base64.b64decode(response.audio_base64)
        
        with open(output_path, "wb") as f:
            f.write(audio_bytes)
        
        return response
    
    async def health_check(self) -> bool:
        """Check if Timbre service is available."""
        try:
            response = await self.client.get("/timbre/health", timeout=5.0)
            return response.status_code == 200
        except Exception:
            return False