"""Integration tests for the full support bot pipeline."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.pipelines.support_bot import SupportBotPipeline
from app.models.schemas import SupportBotRequest, SupportBotResponse
from app.models.enums import Language, Intent, Sentiment, ResolutionAction

_VALID_AUDIO_BASE64 = "dGVzdCBhdWRpbw=="


class TestSupportBotPipeline:
    """Test the full support bot pipeline."""
    
    @pytest.fixture
    def pipeline(self):
        with patch.dict("os.environ", {"GNANI_API_KEY": "test_key"}):
            with patch("app.services.prisma.PrismaClient.__init__", return_value=None):
                with patch("app.services.evon.EvonClient.__init__", return_value=None):
                    with patch("app.services.timbre.TimbreClient.__init__", return_value=None):
                        pipeline = SupportBotPipeline()
                        pipeline.prisma = AsyncMock()
                        pipeline.evon = AsyncMock()
                        pipeline.timbre = AsyncMock()
                        return pipeline
    
    async def test_process_full_pipeline(self, pipeline):
        """Test full pipeline processing."""
        # Mock Prisma response
        from app.models.schemas import PrismaTranscriptionResponse
        prisma_response = PrismaTranscriptionResponse(
            text="Mujhe refund chahiye order 1234 ke liye",
            language=Language.HINGLISH,
            confidence=0.94,
            duration_seconds=3.0,
            processing_time_ms=500,
        )
        pipeline.prisma.transcribe.return_value = prisma_response
        
        # Mock Evon response
        from app.models.schemas import EvonReasoningResponse
        evon_response = EvonReasoningResponse(
            intent=Intent.REFUND_REQUEST,
            sentiment=Sentiment.FRUSTRATED,
            confidence=0.92,
            resolution=ResolutionAction.APPROVE_REFUND,
            response_text="Maaf kijiye, aapka refund process kar diya gaya hai.",
            extracted_entities={"order_id": "1234"},
            reasoning_trace="Customer wants refund for order 1234",
            processing_time_ms=800,
        )
        pipeline.evon.reason.return_value = evon_response
        
        # Mock Timbre response
        from app.models.schemas import TimbreSynthesisResponse
        timbre_response = TimbreSynthesisResponse(
            audio_base64="dGVzdCBhdWRpbw==",
            format="wav",
            sample_rate=22050,
            duration_seconds=2.0,
            processing_time_ms=600,
        )
        pipeline.timbre.synthesize.return_value = timbre_response
        
        # Process
        request = SupportBotRequest(
            audio_base64=_VALID_AUDIO_BASE64,
            audio_format="wav",
            language=Language.AUTO,
        )
        
        response = await pipeline.process(request)
        
        # Assertions
        assert isinstance(response, SupportBotResponse)
        assert response.transcript == "Mujhe refund chahiye order 1234 ke liye"
        assert response.detected_language == Language.HINGLISH
        assert response.intent == Intent.REFUND_REQUEST
        assert response.sentiment == Sentiment.FRUSTRATED
        assert response.resolution == ResolutionAction.APPROVE_REFUND
        assert response.response_text == "Maaf kijiye, aapka refund process kar diya gaya hai."
        assert response.response_audio_base64 == "dGVzdCBhdWRpbw=="
        assert response.total_latency_ms > 0
        assert "prisma_ms" in response.latency_breakdown
        assert "evon_ms" in response.latency_breakdown
        assert "timbre_ms" in response.latency_breakdown
    
    async def test_session_continuity(self, pipeline):
        """Test that session history is maintained."""
        # First request
        from app.models.schemas import PrismaTranscriptionResponse
        prisma_response = PrismaTranscriptionResponse(
            text="Hello",
            language=Language.ENGLISH_INDIA,
            confidence=0.9,
            duration_seconds=1.0,
            processing_time_ms=100,
        )
        pipeline.prisma.transcribe.return_value = prisma_response
        
        from app.models.schemas import EvonReasoningResponse
        evon_response = EvonReasoningResponse(
            intent=Intent.GENERAL_QUERY,
            sentiment=Sentiment.NEUTRAL,
            confidence=0.9,
            resolution=ResolutionAction.PROVIDE_INFO,
            response_text="Hello! How can I help?",
            extracted_entities={},
            reasoning_trace="Greeting",
            processing_time_ms=200,
        )
        pipeline.evon.reason.return_value = evon_response
        
        from app.models.schemas import TimbreSynthesisResponse
        timbre_response = TimbreSynthesisResponse(
            audio_base64="dGVzdA==",
            format="wav",
            sample_rate=22050,
            duration_seconds=1.0,
            processing_time_ms=150,
        )
        pipeline.timbre.synthesize.return_value = timbre_response
        
        session_id = "test-session-123"
        
        # First call
        request1 = SupportBotRequest(
            audio_base64=_VALID_AUDIO_BASE64,
            language=Language.ENGLISH_INDIA,
            session_id=session_id,
        )
        await pipeline.process(request1)
        
        # Second call - should have history
        request2 = SupportBotRequest(
            audio_base64=_VALID_AUDIO_BASE64,
            language=Language.ENGLISH_INDIA,
            session_id=session_id,
        )
        await pipeline.process(request2)
        
        # Verify Evon was called with history on second call
        calls = pipeline.evon.reason.call_args_list
        assert len(calls) == 2
        # Second call should have conversation_history
        assert calls[1].kwargs.get("conversation_history") is not None
