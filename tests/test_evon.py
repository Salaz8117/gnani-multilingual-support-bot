"""Tests for Evon reasoning client."""

import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.evon import EvonClient
from app.models.enums import Language, Intent, Sentiment, ResolutionAction
from app.models.schemas import EvonReasoningResponse


class TestEvonClient:
    """Test Evon reasoning client."""
    
    @pytest.fixture
    def client(self):
        with patch.dict("os.environ", {"GNANI_API_KEY": "test_key"}):
            with patch("app.services.evon.EvonClient._load_system_prompt", return_value="test prompt"):
                return EvonClient(api_key="test_key", base_url="http://test.api")
    
    @pytest.mark.asyncio
    async def test_reason_success(self, client):
        """Test successful reasoning."""
        evon_response = {
            "intent": "refund_request",
            "sentiment": "frustrated",
            "confidence": 0.92,
            "resolution": "approve_refund",
            "response_text": "Maaf kijiye, refund process kar diya.",
            "extracted_entities": {"order_id": "12345"},
            "reasoning_trace": "Customer wants refund for order 12345",
        }
        
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": json.dumps(evon_response)}}]
        }
        mock_response.raise_for_status = MagicMock()
        
        client._client = AsyncMock()
        client._client.post.return_value = mock_response
        
        result = await client.reason(
            transcript="I want refund for order 12345",
            language=Language.HINGLISH,
        )
        
        assert isinstance(result, EvonReasoningResponse)
        assert result.intent == Intent.REFUND_REQUEST
        assert result.sentiment == Sentiment.FRUSTRATED
        assert result.confidence == 0.92
        assert result.resolution == ResolutionAction.APPROVE_REFUND
    
    @pytest.mark.asyncio
    async def test_reason_http_error(self, client):
        """Test reasoning with HTTP error."""
        import httpx
        
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        
        client._client = AsyncMock()
        client._client.post.side_effect = httpx.HTTPStatusError(
            "Server Error", request=MagicMock(), response=mock_response
        )
        
        with pytest.raises(Exception):  # EvonError
            await client.reason("test", Language.ENGLISH_INDIA)