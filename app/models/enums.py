"""Enumerations for languages, intents, and other constants."""

from enum import Enum


class Language(str, Enum):
    """Supported Indian languages with ISO codes."""
    
    # Major languages
    HINDI = "hi-IN"
    ENGLISH_INDIA = "en-IN"
    BENGALI = "bn-IN"
    TELUGU = "te-IN"
    MARATHI = "mr-IN"
    TAMIL = "ta-IN"
    GUJARATI = "gu-IN"
    URDU = "ur-IN"
    KANNADA = "kn-IN"
    MALAYALAM = "ml-IN"
    PUNJABI = "pa-IN"
    ODIA = "or-IN"
    ASSAMESE = "as-IN"
    
    # Code-mixed
    HINGLISH = "hi-en-IN"
    TANGLISH = "ta-en-IN"
    BENGLISH = "bn-en-IN"
    
    # Auto-detect
    AUTO = "auto"
    
    @property
    def display_name(self) -> str:
        names = {
            "hi-IN": "Hindi",
            "en-IN": "English (India)",
            "bn-IN": "Bengali",
            "te-IN": "Telugu",
            "mr-IN": "Marathi",
            "ta-IN": "Tamil",
            "gu-IN": "Gujarati",
            "ur-IN": "Urdu",
            "kn-IN": "Kannada",
            "ml-IN": "Malayalam",
            "pa-IN": "Punjabi",
            "or-IN": "Odia",
            "as-IN": "Assamese",
            "hi-en-IN": "Hinglish (Hindi+English)",
            "ta-en-IN": "Tanglish (Tamil+English)",
            "bn-en-IN": "Benglish (Bengali+English)",
            "auto": "Auto-detect",
        }
        return names.get(self.value, self.value)


class BotMode(str, Enum):
    """Operating mode of the bot."""
    SUPPORT = "support"
    TRANSLATE = "translate"

class Intent(str, Enum):
    """Customer support intent categories."""
    
    REFUND_REQUEST = "refund_request"
    ORDER_STATUS = "order_status"
    PRODUCT_INQUIRY = "product_inquiry"
    TECHNICAL_SUPPORT = "technical_support"
    BILLING_ISSUE = "billing_issue"
    ACCOUNT_HELP = "account_help"
    COMPLAINT = "complaint"
    CANCELLATION = "cancellation"
    FEEDBACK = "feedback"
    GENERAL_QUERY = "general_query"
    UNKNOWN = "unknown"


class Sentiment(str, Enum):
    """Customer sentiment classification."""
    
    VERY_POSITIVE = "very_positive"
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"
    VERY_NEGATIVE = "very_negative"
    FRUSTRATED = "frustrated"
    ANGRY = "angry"


class ResolutionAction(str, Enum):
    """Possible resolution actions."""
    
    APPROVE_REFUND = "approve_refund"
    DENY_REFUND = "deny_refund"
    ESCALATE = "escalate"
    PROVIDE_INFO = "provide_info"
    SCHEDULE_CALLBACK = "schedule_callback"
    TRANSFER_AGENT = "transfer_agent"
    APPLY_DISCOUNT = "apply_discount"
    REPLACE_PRODUCT = "replace_product"
    NO_ACTION = "no_action"


class VoiceType(str, Enum):
    """TTS voice options."""
    
    FEMALE_WARM = "female_warm"
    FEMALE_PROFESSIONAL = "female_professional"
    MALE_WARM = "male_warm"
    MALE_PROFESSIONAL = "male_professional"
    FEMALE_ENERGETIC = "female_energetic"
    MALE_CALM = "male_calm"


class AudioFormat(str, Enum):
    """Supported audio formats."""
    
    WAV = "wav"
    MP3 = "mp3"
    M4A = "m4a"
    OGG = "ogg"
    FLAC = "flac"