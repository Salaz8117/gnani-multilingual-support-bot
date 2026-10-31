"""Mock Gnani clients for demo without API keys."""

import asyncio
import base64
import json
import time
import random
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

from app.models.schemas import (
    PrismaTranscriptionResponse,
    EvonReasoningResponse,
    TimbreSynthesisResponse,
    SupportBotRequest,
    SupportBotResponse,
)
from app.models.enums import Language, Intent, Sentiment, ResolutionAction, VoiceType
from app.core.exceptions import PrismaError, EvonError, TimbreError


# Demo scenarios for realistic responses
DEMO_SCENARIOS = [
    {
        "keywords": ["refund", "money back", "return", "defective", "problem"],
        "transcript": "Hello, main order number 12345 ka refund chahiye. Bahut problem ho rahi hai, product defective hai.",
        "language": Language.HINGLISH,
        "intent": Intent.REFUND_REQUEST,
        "sentiment": Sentiment.FRUSTRATED,
        "resolution": ResolutionAction.APPROVE_REFUND,
        "response": "Maaf kijiye, aapka refund process kar diya gaya hai. Amount 3-5 business days mein wapas aa jayega. Kuch aur madad chahiye?",
        "entities": {"order_id": "12345", "product": "Wireless Headphones", "amount": 2999},
    },
    {
        "keywords": ["complaint", "defective", "broken", "quality", "issue"],
        "transcript": "நான் வாங்கிய தவிர் பொருட்கள் ப meu பிழை உள்ளது. இது நல்ல தேவையில் இருக்க வேண்டிய நேரத்தில் خرابی হয়েছে।",
        "language": Language.TAMIL,
        "intent": Intent.COMPLAINT,
        "sentiment": Sentiment.NEGATIVE,
        "resolution": ResolutionAction.REPLACE_PRODUCT,
        "response": "மன்னிக்கவும், உங்கள் தவறான தயாரிப்பு மாற்றும் பணி தொடங்கியுள்ளது. 2-3 நாட்களில் புதிய தயாரிப்பு கிடைக்கும்.",
        "entities": {"order_id": "TN-789", "product": "Smart Watch"},
    },
    {
        "keywords": ["order", "status", "tracking", "where", "delivery", "arrive"],
        "transcript": "Hi, I'd like to check the status of my order ORD-999. It was supposed to arrive yesterday.",
        "language": Language.ENGLISH_INDIA,
        "intent": Intent.ORDER_STATUS,
        "sentiment": Sentiment.NEUTRAL,
        "resolution": ResolutionAction.PROVIDE_INFO,
        "response": "Your order ORD-999 is out for delivery and will arrive today by 6 PM. You'll receive an SMS with tracking details.",
        "entities": {"order_id": "ORD-999"},
    },
    {
        "keywords": ["technical", "support", "router", "internet", "slow", "disconnect", "wifi"],
        "transcript": "আমার রাউটারের সাথে সমস্যা হচ্ছে। ইন্টারনেট খুব ধীরে চলে এবং ঘন ঘন ডিসকানেক্ট হয়।",
        "language": Language.BENGALI,
        "intent": Intent.TECHNICAL_SUPPORT,
        "sentiment": Sentiment.FRUSTRATED,
        "resolution": ResolutionAction.SCHEDULE_CALLBACK,
        "response": "দুঃখিত, আপনার রাউটার সমস্যার জন্য আমরা একটি টেকনিশিয়ান আপনাকে কল করবেন ২ ঘন্টার মধ্যে।",
        "entities": {"device": "WiFi Router Model X"},
    },
    {
        "keywords": ["bill", "billing", "charge", "amount", "payment", "invoice"],
        "transcript": "Mera bill galat aaya hai. Main ₹500 ka plan liya tha par ₹800 charge kiya gaya.",
        "language": Language.HINGLISH,
        "intent": Intent.BILLING_ISSUE,
        "sentiment": Sentiment.ANGRY,
        "resolution": ResolutionAction.APPLY_DISCOUNT,
        "response": "Maaf kijiye, billing error ke liye. ₹300 credit aapke account mein add kar diya gaya hai. Agla bill sahi aayega.",
        "entities": {"amount": 300, "plan": "₹500"},
    },
    {
        "keywords": ["cancel", "cancellation", "stop", "subscription", "membership"],
        "transcript": "I want to cancel my subscription. I'm not using the service anymore.",
        "language": Language.ENGLISH_INDIA,
        "intent": Intent.CANCELLATION,
        "sentiment": Sentiment.NEUTRAL,
        "resolution": ResolutionAction.PROVIDE_INFO,
        "response": "Your subscription has been cancelled. You'll continue to have access until the end of your billing cycle. No further charges.",
        "entities": {"subscription_id": "SUB-4567"},
    },
]


def generate_silence_wav(duration_seconds: float = 2.0, sample_rate: int = 22050) -> bytes:
    """Generate a WAV file with silence."""
    import io
    import numpy as np
    import soundfile as sf
    
    silence = np.zeros(int(duration_seconds * sample_rate), dtype=np.float32)
    buffer = io.BytesIO()
    sf.write(buffer, silence, sample_rate, format='WAV')
    return buffer.getvalue()


class MockPrismaClient:
    """Mock Prisma STT client for demo."""
    
    def __init__(self, *args, **kwargs):
        pass
    
    async def transcribe(
        self,
        audio_base64: str,
        language: Language = Language.AUTO,
        enable_diarization: bool = False,
        noise_reduction: bool = True,
    ) -> PrismaTranscriptionResponse:
        """Simulate transcription with realistic delay."""
        await asyncio.sleep(0.3 + random.uniform(0, 0.2))  # 300-500ms
        
        # Pick scenario based on audio "content" (hash for consistency)
        scenario_idx = hash(audio_base64[:100]) % len(DEMO_SCENARIOS)
        scenario = DEMO_SCENARIOS[scenario_idx]
        
        return PrismaTranscriptionResponse(
            text=scenario["transcript"],
            language=scenario["language"],
            confidence=0.92 + random.uniform(0, 0.05),
            duration_seconds=3.5 + random.uniform(0, 1.5),
            processing_time_ms=int(300 + random.uniform(0, 200)),
            words=None,
            segments=None,
        )
    
    async def transcribe_file(self, file_path: str, **kwargs) -> PrismaTranscriptionResponse:
        with open(file_path, "rb") as f:
            audio_base64 = base64.b64encode(f.read()).decode("utf-8")
        return await self.transcribe(audio_base64, **kwargs)
    
    async def health_check(self) -> bool:
        return True
    
    async def close(self):
        pass


class MockEvonClient:
    """Mock Evon reasoning client for demo."""
    
    def __init__(self, *args, **kwargs):
        pass
    
    async def reason(
        self,
        transcript: str,
        language: Language,
        context: Optional[Dict[str, Any]] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ) -> EvonReasoningResponse:
        """Simulate reasoning with realistic delay."""
        await asyncio.sleep(0.6 + random.uniform(0, 0.4))  # 600-1000ms
        
        # Match scenario based on transcript keywords
        transcript_lower = transcript.lower()
        matched_scenario = None
        
        for scenario in DEMO_SCENARIOS:
            if any(kw in transcript_lower for kw in scenario["keywords"]):
                matched_scenario = scenario
                break
        
        if not matched_scenario:
            matched_scenario = DEMO_SCENARIOS[0]  # Default
        
        # Merge context entities
        entities = matched_scenario["entities"].copy()
        if context:
            entities.update(context)
        
        return EvonReasoningResponse(
            intent=matched_scenario["intent"],
            sentiment=matched_scenario["sentiment"],
            confidence=0.94 + random.uniform(0, 0.03),
            resolution=matched_scenario["resolution"],
            response_text=matched_scenario["response"],
            extracted_entities=entities,
            reasoning_trace=f"Detected {matched_scenario['intent'].value} with {matched_scenario['sentiment'].value} sentiment in {language.value}. Keywords matched: {[kw for kw in matched_scenario['keywords'] if kw in transcript_lower]}",
            processing_time_ms=int(600 + random.uniform(0, 400)),
        )
    
    async def health_check(self) -> bool:
        return True
    
    async def close(self):
        pass


class MockTimbreClient:
    """Mock Timbre TTS client for demo."""
    
    def __init__(self, *args, **kwargs):
        pass
    
    async def synthesize(
        self,
        text: str,
        language: Language,
        voice: VoiceType = VoiceType.FEMALE_WARM,
        sample_rate: int = 22050,
        speed: float = 1.0,
        pitch: float = 1.0,
    ) -> TimbreSynthesisResponse:
        """Simulate TTS synthesis with realistic delay."""
        await asyncio.sleep(0.4 + random.uniform(0, 0.2))  # 400-600ms
        
        # Generate silence audio as placeholder
        audio_bytes = generate_silence_wav(3.0, sample_rate)
        audio_base64 = base64.b64encode(audio_bytes).decode("utf-8")
        
        return TimbreSynthesisResponse(
            audio_base64=audio_base64,
            format="wav",
            sample_rate=sample_rate,
            duration_seconds=3.0,
            processing_time_ms=int(400 + random.uniform(0, 200)),
        )
    
    async def synthesize_to_file(self, text: str, output_path: str, **kwargs) -> TimbreSynthesisResponse:
        response = await self.synthesize(text, **kwargs)
        audio_bytes = base64.b64decode(response.audio_base64)
        with open(output_path, "wb") as f:
            f.write(audio_bytes)
        return response
    
    async def health_check(self) -> bool:
        return True
    
    async def close(self):
        pass


# Auto-detect if we should use mock or real clients
def create_pipeline(use_mock: bool = True):
    """Create pipeline with mock or real clients."""
    if use_mock:
        from app.pipelines.support_bot import SupportBotPipeline
        return SupportBotPipeline(
            prisma_client=MockPrismaClient(),
            evon_client=MockEvonClient(),
            timbre_client=MockTimbreClient(),
        )
    else:
        from app.pipelines.support_bot import SupportBotPipeline
        return SupportBotPipeline()