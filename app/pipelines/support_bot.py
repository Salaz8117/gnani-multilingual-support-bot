"""Main support bot pipeline orchestrating Prisma, Evon, and Timbre."""

import time
import uuid
from typing import Optional, Dict, Any
import structlog

from app.core.config import get_settings
from app.core.exceptions import PipelineError, ConfigurationError
from app.services.prisma import PrismaClient
from app.services.evon import EvonClient
from app.services.timbre import TimbreClient
from app.models.schemas import SupportBotRequest, SupportBotResponse
from app.models.enums import Language
from app.utils.audio import decode_audio_base64, encode_audio_base64

logger = structlog.get_logger()


class SupportBotPipeline:
    """Orchestrates the full support bot pipeline: STT -> Reasoning -> TTS."""
    
    def __init__(
        self,
        prisma_client: Optional[PrismaClient] = None,
        evon_client: Optional[EvonClient] = None,
        timbre_client: Optional[TimbreClient] = None,
    ):
        self.settings = get_settings()
        
        # Initialize clients
        self.prisma = prisma_client or PrismaClient()
        self.evon = evon_client or EvonClient()
        self.timbre = timbre_client or TimbreClient()
        
        # Session storage (in-memory for demo; use Redis in production)
        self._sessions: Dict[str, Dict[str, Any]] = {}
    
    async def process(self, request: SupportBotRequest) -> SupportBotResponse:
        """
        Process audio through the full pipeline.
        
        Args:
            request: SupportBotRequest with audio and metadata
            
        Returns:
            SupportBotResponse with transcript, reasoning, and audio response
        """
        session_id = request.session_id or str(uuid.uuid4())[:8]
        start_total = time.perf_counter()
        latency = {}
        
        logger.info("pipeline_start", session_id=session_id, language=request.language.value)
        
        try:
            # Stage 1: Speech-to-Text (Prisma)
            logger.debug("stage_prisma_start", session_id=session_id)
            start = time.perf_counter()
            
            prisma_response = await self.prisma.transcribe(
                audio_base64=request.audio_base64,
                language=request.language,
                enable_diarization=self.settings.prisma_enable_diarization,
                noise_reduction=self.settings.prisma_noise_reduction,
            )
            
            latency["prisma_ms"] = int((time.perf_counter() - start) * 1000)
            logger.info("prisma_done", session_id=session_id, text=prisma_response.text[:50], latency_ms=latency["prisma_ms"])
            
            # Stage 2: Reasoning (Evon)
            logger.debug("stage_evon_start", session_id=session_id)
            start = time.perf_counter()
            
            # Get conversation history for this session
            history = self._sessions.get(session_id, {}).get("history", [])
            
            evon_response = await self.evon.reason(
                transcript=prisma_response.text,
                language=prisma_response.language,
                context=request.context,
                conversation_history=history,
            )
            
            latency["evon_ms"] = int((time.perf_counter() - start) * 1000)
            logger.info("evon_done", session_id=session_id, intent=evon_response.intent.value, sentiment=evon_response.sentiment.value, latency_ms=latency["evon_ms"])
            
            # Stage 3: Text-to-Speech (Timbre)
            logger.debug("stage_timbre_start", session_id=session_id)
            start = time.perf_counter()
            
            timbre_response = await self.timbre.synthesize(
                text=evon_response.response_text,
                language=prisma_response.language,
                voice=self.settings.timbre_default_voice,
                sample_rate=self.settings.timbre_sample_rate,
            )
            
            latency["timbre_ms"] = int((time.perf_counter() - start) * 1000)
            logger.info("timbre_done", session_id=session_id, duration=timbre_response.duration_seconds, latency_ms=latency["timbre_ms"])
            
            # Update session history
            self._update_session(session_id, prisma_response.text, evon_response.response_text)
            
            total_latency = int((time.perf_counter() - start_total) * 1000)
            latency["total_ms"] = total_latency
            
            logger.info("pipeline_complete", session_id=session_id, total_latency_ms=total_latency)
            
            return SupportBotResponse(
                session_id=session_id,
                transcript=prisma_response.text,
                detected_language=prisma_response.language,
                intent=evon_response.intent,
                sentiment=evon_response.sentiment,
                resolution=evon_response.resolution,
                response_text=evon_response.response_text,
                response_audio_base64=timbre_response.audio_base64,
                latency_breakdown=latency,
                total_latency_ms=total_latency,
            )
            
        except Exception as e:
            logger.error("pipeline_failed", session_id=session_id, error=str(e))
            raise PipelineError(f"Pipeline failed: {str(e)}", stage="unknown", original_error=e)
    
    def _update_session(self, session_id: str, user_text: str, bot_text: str):
        """Update conversation history for session."""
        if session_id not in self._sessions:
            self._sessions[session_id] = {"history": [], "created": time.time()}
        
        self._sessions[session_id]["history"].extend([
            {"role": "user", "content": user_text},
            {"role": "assistant", "content": bot_text},
        ])
        
        # Keep only last 10 turns
        if len(self._sessions[session_id]["history"]) > 20:
            self._sessions[session_id]["history"] = self._sessions[session_id]["history"][-20:]
    
    async def process_file(
        self,
        file_path: str,
        language: Language = Language.AUTO,
        session_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> SupportBotResponse:
        """Process audio from a file path."""
        import base64
        
        with open(file_path, "rb") as f:
            audio_base64 = base64.b64encode(f.read()).decode("utf-8")
        
        request = SupportBotRequest(
            audio_base64=audio_base64,
            audio_format="wav",
            language=language,
            session_id=session_id,
            context=context,
        )
        
        return await self.process(request)
    
    async def health_check(self) -> Dict[str, bool]:
        """Check health of all services."""
        return {
            "prisma": await self.prisma.health_check(),
            "evon": await self.evon.health_check(),
            "timbre": await self.timbre.health_check(),
        }
    
    async def close(self):
        """Close all client connections."""
        await self.prisma.close()
        await self.evon.close()
        await self.timbre.close()


# Convenience function for quick processing
async def process_audio(
    audio_base64: str,
    language: Language = Language.AUTO,
    session_id: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None,
) -> SupportBotResponse:
    """Quick audio processing without managing pipeline instance."""
    pipeline = SupportBotPipeline()
    try:
        request = SupportBotRequest(
            audio_base64=audio_base64,
            audio_format="wav",
            language=language,
            session_id=session_id,
            context=context,
        )
        return await pipeline.process(request)
    finally:
        await pipeline.close()