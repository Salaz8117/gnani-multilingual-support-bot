"""Tests for Prisma STT client."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.prisma import PrismaClient
from app.models.enums import Language
from app.models.schemas import PrismaTranscriptionResponse


class TestPrismaClient:
    """Test Prisma STT client."""
    
    @pytest.fixture
    def client(self):
        with patch.dict("os.environ", {"GNANI_API_KEY": "test_key"}):
            return PrismaClient(api_key="test_key", base_url="http://test.api")
    
    @pytest.mark.asyncio
    async def test_transcribe_success(self, client):
        """Test successful transcription."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "text": "Hello world",
            "language": "en-IN",
            "confidence": 0.95,
            "duration_seconds": 2.5,
            "words": [],
            "segments": None,
        }
        mock_response.raise_for_status = MagicMock()
        
        client._client = AsyncMock()
        client._client.post.return_value = mock_response
        
        result = await client.transcribe("base64_audio", language=Language.ENGLISH_INDIA)
        
        assert isinstance(result, PrismaTranscriptionResponse)
        assert result.text == "Hello world"
        assert result.language == Language.ENGLISH_INDIA
        assert result.confidence == 0.95
    
    @pytest.mark.asyncio
    async def test_transcribe_http_error(self, client):
        """Test transcription with HTTP error."""
        import httpx
        
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "Bad Request"
        mock_response.json.return_value = {"error": "Invalid audio"}
        
        client._client = AsyncMock()
        client._client.post.side_effect = httpx.HTTPStatusError(
            "Bad Request", request=MagicMock(), response=mock_response
        )
        
        with pytest.raises(Exception):  # PrismaError
            await client.transcribe("base64_audio")
    
    @pytest.mark.asyncio
    async def test_health_check(self, client):
        """Test health check."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        
        client._client = AsyncMock()
        client._client.get.return_value = mock_response
        
        result = await client.health_check()
        assert result is True