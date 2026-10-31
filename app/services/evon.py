"""Evon reasoning client for Gnani AI."""

import time
from typing import Optional, Dict, Any, List
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.core.config import get_settings
from app.core.exceptions import EvonError
from app.models.schemas import EvonReasoningRequest, EvonReasoningResponse
from app.models.enums import Language, Intent, Sentiment, ResolutionAction, BotMode


class EvonClient:
    """Client for Gnani AI Evon Reasoning API."""
    
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        self.settings = get_settings()
        self.api_key = api_key or self.settings.gnani_api_key
        self.base_url = (base_url or self.settings.gnani_base_url).rstrip("/")
        self.model = self.settings.evon_model
        self.temperature = self.settings.evon_temperature
        self.max_tokens = self.settings.evon_max_tokens
        
        if not self.api_key:
            raise EvonError("API key not configured")
        
        self._client: Optional[httpx.AsyncClient] = None
        self._system_prompt: Optional[str] = None
    
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
                timeout=httpx.Timeout(120.0, connect=10.0),
            )
        return self._client
    
    async def close(self):
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
    
    def _load_system_prompt(self) -> str:
        """Load system prompt from file or use default."""
        if self._system_prompt is not None:
            return self._system_prompt
        
        try:
            with open(self.settings.evon_system_prompt_path, "r") as f:
                self._system_prompt = f.read().strip()
        except FileNotFoundError:
            self._system_prompt = self._default_system_prompt()
        
        return self._system_prompt
    
    def _default_system_prompt(self) -> str:
        """Default system prompt for customer support reasoning."""
        return """You are an expert customer support AI for Indian enterprises. 
Analyze the customer's transcript and provide structured reasoning.

Your task:
1. Detect the INTENT from: refund_request, order_status, product_inquiry, technical_support, billing_issue, account_help, complaint, cancellation, feedback, general_query, unknown
2. Detect SENTIMENT from: very_positive, positive, neutral, negative, very_negative, frustrated, angry
3. Determine RESOLUTION ACTION from: approve_refund, deny_refund, escalate, provide_info, schedule_callback, transfer_agent, apply_discount, replace_product, no_action
4. Extract ENTITIES (order_ids, amounts, product_names, dates, etc.)
5. Generate a natural language RESPONSE in the SAME language/style as the customer (including code-mixed Hinglish, Tanglish, etc.)
6. Provide step-by-step REASONING

Output ONLY valid JSON with this exact structure:
{
  "intent": "refund_request",
  "sentiment": "frustrated",
  "confidence": 0.92,
  "resolution": "approve_refund",
  "response_text": "Maaf kijiye, aapka refund process kar diya gaya hai. 3-5 business days mein amount wapas aa jayega.",
  "extracted_entities": {"order_id": "12345", "amount": 2999},
  "reasoning_trace": "Customer mentions 'refund chahiye' and order number. Sentiment is frustrated due to 'bahut problem ho rahi hai'. Policy allows refund for defective items within 30 days."
}"""
    
    @retry(
        wait=wait_exponential(multiplier=1, min=2, max=20),
        stop=stop_after_attempt(3),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError)),
    )
    async def reason(
        self,
        transcript: str,
        language: Language,
        context: Optional[Dict[str, Any]] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        mode: BotMode = BotMode.SUPPORT,
    ) -> EvonReasoningResponse:
        """
        Perform reasoning on transcript using Evon.
        
        Args:
            transcript: Transcribed text from Prisma
            language: Language of the transcript
            context: Additional context (customer info, order history, etc.)
            conversation_history: Previous conversation turns
            
        Returns:
            EvonReasoningResponse with intent, sentiment, resolution, and response
        """
        start_time = time.perf_counter()
        
        if mode == BotMode.TRANSLATE:
            # For translation, we use a specific prompt and the context/language as target
            target_lang = context.get("target_language", "en-IN") if context else "en-IN"
            system_prompt = f\"\"\"You are a professional real-time translator. 
Translate the provided text into {target_lang} while preserving the exact tone, emotion, and cultural nuances.
Output ONLY valid JSON with this exact structure:
{{
  \"intent\": \"general_query\",
  \"sentiment\": \"neutral\",
  \"confidence\": 0.99,
  \"resolution\": \"provide_info\",
  \"response_text\": \"TRANSLATED_TEXT_HERE\",
  \"extracted_entities\": {{}},
  \"reasoning_trace\": \"Translated from source to {target_lang}.\"
}}\"\"\"
        else:
            if mode == BotMode.TRANSLATE:
            # For translation, we use a specific prompt and the context/language as target
            target_lang = context.get(\"target_language\", \"en-IN\") if context else \"en-IN\"
            system_prompt = f\"\"\"You are a professional real-time translator. 
Translate the provided text into {target_lang} while preserving the exact tone, emotion, and cultural nuances.
Output ONLY valid JSON with this exact structure:
{{
  \"intent\": \"general_query\",
  \"sentiment\": \"neutral\",
  \"confidence\": 0.99,
  \"resolution\": \"provide_info\",
  \"response_text\": \"TRANSLATED_TEXT_HERE\",
  \"extracted_entities\": {{}},
  \"reasoning_trace\": \"Translated from source to {target_lang}.\"
}}\"\"\"
        else:
            system_prompt = self._load_system_prompt()
        
        # Build user prompt
        user_prompt = f"Language: {language.value}\nTranscript: {transcript}\n"
        
        if context:
            user_prompt += f"Context: {context}\n"
        
        if conversation_history:
            user_prompt += f"History: {conversation_history}\n"
        
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "response_format": {"type": "json_object"},
        }
        
        try:
            response = await self.client.post("/evon/chat/completions", json=payload)
            response.raise_for_status()
            data = response.json()
            
            processing_time = int((time.perf_counter() - start_time) * 1000)
            
            # Parse the JSON response from Evon
            content = data["choices"][0]["message"]["content"]
            import json
            result = json.loads(content)
            
            return EvonReasoningResponse(
                intent=Intent(result.get("intent", "unknown")),
                sentiment=Sentiment(result.get("sentiment", "neutral")),
                confidence=result.get("confidence", 0.0),
                resolution=ResolutionAction(result.get("resolution", "no_action")),
                response_text=result.get("response_text", ""),
                extracted_entities=result.get("extracted_entities", {}),
                reasoning_trace=result.get("reasoning_trace"),
                processing_time_ms=processing_time,
            )
            
        except httpx.HTTPStatusError as e:
            raise EvonError(
                f"Reasoning failed: {e.response.text}",
                status_code=e.response.status_code,
                response_data=e.response.json() if e.response.content else None,
            )
        except Exception as e:
            raise EvonError(f"Reasoning error: {str(e)}")
    
    async def health_check(self) -> bool:
        """Check if Evon service is available."""
        try:
            response = await self.client.get("/evon/health", timeout=5.0)
            return response.status_code == 200
        except Exception:
            return False