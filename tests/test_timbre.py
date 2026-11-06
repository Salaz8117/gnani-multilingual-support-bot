"""Tests for Timbre TTS client."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.timbre import TimbreClient
from app.models.enums import Language, VoiceType
from app.models.schemas import TimbreSynthesisResponse


class TestTimbreClient:
    """Test Timbre TTS client."""
    
    @pytest.fixture
    def client(self):
        with patch.dict("os.environ", {"GNANI_API_KEY": "test_key"}):
            return TimbreClient(api_key="test_key", base_url="http://test.api")
    
    async def test_synthesize_success(self, client):
        """Test successful synthesis."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "audio_base64": "dGVzdCBhdWRpbw==",
            "format": "wav",
            "sample_rate": 22050,
            "duration_seconds": 1.5,
        }
        mock_response.raise_for_status = MagicMock()
        
        client._client = AsyncMock()
        client._client.is_closed = False
        client._client.post.return_value = mock_response
        
        result = await client.synthesize(
            text="Hello world",
            language=Language.ENGLISH_INDIA,
            voice=VoiceType.FEMALE_WARM,
        )
        
        assert isinstance(result, TimbreSynthesisResponse)
        assert result.audio_base64 == "dGVzdCBhdWRpbw=="
        assert result.format == "wav"
        assert result.sample_rate == 22050
    
    async def test_synthesize_http_error(self, client):
        """Test synthesis with HTTP error."""
        import httpx
        
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "Bad Request"
        
        client._client = AsyncMock()
        client._client.is_closed = False
        client._client.post.side_effect = httpx.HTTPStatusError(
            "Bad Request", request=MagicMock(), response=mock_response
        )
        
        with pytest.raises(Exception):  # TimbreError
            await client.synthesize("test", Language.ENGLISH_INDIA)
