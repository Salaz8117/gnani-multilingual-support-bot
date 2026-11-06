# 🌐 Multilingual Voice Customer Support Bot

> **Built for the Great Indian AI Internship Challenge 2026**  
> Powered by **Gnani AI**: Prisma (STT) + Evon (Reasoning) + Timbre (TTS)

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-green.svg)](https://fastapi.tiangolo.com)
[![Gradio](https://img.shields.io/badge/Gradio-4.0+-orange.svg)](https://gradio.app)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 🎯 Problem Statement

Indian enterprises handle **millions of customer calls daily** across **20+ languages**, **noisy telephone lines**, and **code-mixed speech (Hinglish, Tanglish, etc.)**. Existing solutions fail at:
- ✅ **Noisy telephonic audio** (background chatter, line static, low bitrate)
- ✅ **Code-mixed speech** (Hindi+English, Tamil+English, etc.)
- ✅ **Regional language coverage** (beyond Hindi/English)
- ✅ **Sub-second latency** for real-time conversation

---

## 🏆 Award Categories Targeted

| Category | How We Win |
|----------|------------|
| 🗣️ **Regional Languages** | Prisma supports 15+ Indian languages natively |
| 🔀 **Hinglish/Code-Mixed Voice** | Evon reasons over mixed-language transcripts |
| 📞 **Noisy Telephonic Audio** | Prisma trained on real call-center audio |
| 🌍 **Real-World Impact** | Enterprise-ready, deployable architecture |
| 👤 **Best Solo Project** | Single-developer full stack |
| ⏱️ **Best 60-Second Demo** | Scripted end-to-end flow |

---

## 🏗️ Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Audio     │────▶│  PRISMA     │────▶│    EVON     │────▶│   TIMBRE    │
│  Input      │     │   (STT)     │     │ (Reasoning) │     │   (TTS)     │
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
       │                   │                   │                   │
       ▼                   ▼                   ▼                   ▼
  • File upload       • Transcript        • Intent detection   • Voice response
  • Live mic          • Language ID       • Sentiment analysis  • Same language
  • Twilio webhook    • Noise robustness  • Resolution logic   • Code-mixed TTS
                      • Code-mixed support                      
```

---

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- Gnani AI API credentials (get 5,000 credits at [gnani.ai/internship](https://gnani.ai/internship))

### Installation

```bash
# Clone and enter
cd gnani-multilingual-support-bot

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install runtime and development dependencies
pip install -r requirements.txt
# requirements.txt delegates to the project dependencies and [dev] extra in pyproject.toml.
# For runtime dependencies only, use: pip install -e .

# Configure environment
cp .env.example .env
# Edit .env with your Gnani AI API keys
```

### Configuration

```bash
# .env
GNANI_API_KEY=your_api_key_here
GNANI_BASE_URL=https://api.gnani.ai/v1  # Or your gateway URL

# Optional: For Twilio integration
TWILIO_ACCOUNT_SID=xxx
TWILIO_AUTH_TOKEN=xxx
TWILIO_PHONE_NUMBER=+1xxxxxxxxxx

# CORS allowed origins (comma-separated); never use "*" with credentials
CORS_ORIGINS=http://localhost:3000,http://localhost:7860
```

### Run the Demo

```bash
# Terminal 1: Start API server
python -m uvicorn app.main:app --reload --port 8000

# Terminal 2: Launch Gradio UI
python app/demo.py
```

Open http://localhost:7860 for the interactive demo.

**Demo Mode:** The standalone Gradio UI uses simulated responses when `GNANI_API_KEY` is unset or left at the example placeholder, so the scenario buttons work without credentials. The FastAPI server requires a real key and raises `ConfigurationError` during startup if it is missing; set `GNANI_API_KEY` in `.env` before starting the API.

---

## 📁 Project Structure

```
gnani-multilingual-support-bot/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application
│   ├── demo.py              # Gradio demo interface
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py        # Settings management
│   │   └── exceptions.py    # Custom exceptions
│   ├── models/
│   │   ├── __init__.py
│   │   ├── schemas.py       # Pydantic models
│   │   └── enums.py         # Language, Intent enums
│   ├── services/
│   │   ├── __init__.py
│   │   ├── prisma.py        # Prisma STT client
│   │   ├── evon.py          # Evon reasoning client
│   │   └── timbre.py        # Timbre TTS client
│   ├── pipelines/
│   │   ├── __init__.py
│   │   └── support_bot.py   # Main orchestration pipeline
│   └── utils/
│       ├── __init__.py
│       ├── audio.py         # Audio processing helpers
│       └── logging.py       # Structured logging
├── tests/
│   ├── __init__.py
│   ├── test_prisma.py
│   ├── test_evon.py
│   ├── test_timbre.py
│   └── test_pipeline.py
├── assets/
│   ├── sample_audio/        # Demo audio files
│   └── prompts/             # System prompts for Evon
├── scripts/
│   ├── generate_demo.py     # Create demo video assets
│   └── benchmark.py         # Latency/accuracy benchmarks
├── .env.example
├── .gitignore
├── requirements.txt
├── pyproject.toml
├── Dockerfile
├── docker-compose.yml
└── LICENSE
```

---

## 🔧 API Usage

### Prisma (Speech-to-Text)
```python
from app.services.prisma import PrismaClient

client = PrismaClient(api_key="your_key")
result = await client.transcribe(
    audio_file="call.wav",
    language="hi-IN",  # or "auto" for detection
    enable_diarization=True
)
# result: {"text": "मुझे refund चाहिए order 1234 ke liye", "language": "hi-IN", "confidence": 0.94}
```

### Evon (Reasoning)
```python
from app.services.evon import EvonClient

client = EvonClient(api_key="your_key")
result = await client.reason(
    transcript="I want refund for order 1234",
    language="en-IN",
    context={"customer_tier": "premium", "order_history": [...]}
)
# result: {"intent": "refund_request", "sentiment": "frustrated", "resolution": "approved", "response": "..."}
```

### Timbre (Text-to-Speech)
```python
from app.services.timbre import TimbreClient

client = TimbreClient(api_key="your_key")
audio_bytes = await client.synthesize(
    text="Maaf kijiye, aapka refund process kar diya gaya hai",
    language="hi-IN",
    voice="female_warm"
)
# Returns WAV/MP3 bytes
```

---

## 🎬 60-Second Demo Flow

1. **Play noisy call center audio** (background chatter, poor line quality)
2. **Prisma transcribes** → Shows clean Hinglish transcript with language detection
3. **Evon reasons** → Intent: refund_request | Sentiment: frustrated | Resolution: approve
4. **Timbre responds** → Speaks back in same Hinglish tone: *"Maaf kijiye, aapka refund..."*
5. **Dashboard** → Latency: 1.2s | Languages: 12 | CSAT prediction: 94%

---

## 🧪 Testing

```bash
# Unit tests
pytest tests/ -v

# Integration test (requires API keys)
pytest tests/test_pipeline.py -v -k "integration"

# Benchmark
python scripts/benchmark.py
```

---

## 🐳 Docker Deployment

```bash
# Build
docker build -t gnani-support-bot .

# Run
docker run -p 8000:8000 --env-file .env gnani-support-bot

# Or with docker-compose
docker-compose up -d
```

---

## 📊 Evaluation Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| **STT WER (noisy)** | < 15% | Prisma on call-center test set |
| **STT WER (code-mixed)** | < 12% | Prisma on Hinglish test set |
| **Intent Accuracy** | > 90% | Evon on support ticket dataset |
| **End-to-End Latency** | < 2s | P95 across 100 requests |
| **TTS MOS** | > 4.0 | Subjective evaluation |

---

## 🤝 Contributing

This is a competition entry — but PRs for bug fixes welcome!

---

## 📄 License

MIT License — see [LICENSE](LICENSE)

---

## 🙏 Acknowledgments

- **Gnani AI** for providing Prisma, Evon, and Timbre APIs
- **Great Indian AI Internship Challenge** organizers
- **Open source community** for FastAPI, Gradio, and Pydantic

---

## 📞 Contact

**Participant:** [Your Name]  
**GitHub:** [@Salaz8117](https://github.com/Salaz8117)  
**LinkedIn:** [Your LinkedIn]  
**X/Twitter:** [Your Handle]  

**Tags:** `#GnaniAI` `#GreatIndianAIInternshipChallenge`