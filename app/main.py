"""FastAPI application for the Multilingual Voice Support Bot."""

import json
import os
import tempfile
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict, Optional
import structlog

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.core.exceptions import (
    GnaniAPIError,
    PrismaError,
    EvonError,
    TimbreError,
    AudioProcessingError,
    ConfigurationError,
    PipelineError,
)
from app.pipelines.support_bot import SupportBotPipeline
from app.models.schemas import (
    SupportBotRequest,
    SupportBotResponse,
    HealthCheckResponse,
    ErrorResponse,
)
from app.models.enums import Language
from app.utils.audio import decode_audio_base64, validate_audio_file, audio_to_base64_file
from app.utils.logging import configure_logging

logger = structlog.get_logger()

# Global pipeline instance
pipeline: Optional[SupportBotPipeline] = None

_ALLOWED_AUDIO_FORMATS = {"wav", "mp3", "m4a", "ogg", "flac", "aac", "opus", "webm"}


def _safe_suffix(filename: Optional[str]) -> str:
    """Return a lowercase container extension from an upload name, or '' if unusable."""
    if not filename:
        return ""
    ext = Path(filename).suffix.lstrip(".").lower()
    return ext if ext in _ALLOWED_AUDIO_FORMATS else ""


def _parse_context(raw: str) -> Dict[str, Any]:
    """Parse the context form field into a dict, rejecting malformed JSON with 400."""
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="context must be valid JSON") from exc
    if not isinstance(parsed, dict):
        raise HTTPException(status_code=400, detail="context must be a JSON object")
    return parsed


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global pipeline

    configure_logging()
    logger.info("starting_application")

    settings = get_settings()
    if not settings.gnani_api_key:
        raise ConfigurationError(
            "GNANI_API_KEY is not configured", missing_keys=["GNANI_API_KEY"]
        )

    # Initialize pipeline
    pipeline = SupportBotPipeline()

    yield

    # Cleanup
    logger.info("shutting_down")
    if pipeline:
        await pipeline.close()
        pipeline = None


app = FastAPI(
    title="Gnani Multilingual Voice Support Bot",
    description="Enterprise customer support bot using Gnani AI Prisma (STT), Evon (Reasoning), and Timbre (TTS)",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS — explicit origins from settings; never pair "*" with credentials.
_origins = get_settings().cors_origins_list
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials="*" not in _origins,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization"],
)


# Exception handlers
@app.exception_handler(GnaniAPIError)
async def gnani_api_error_handler(request, exc: GnaniAPIError):
    logger.error("gnani_api_error", service=exc.service, error=exc.message, status_code=exc.status_code)
    return JSONResponse(
        status_code=exc.status_code or 502,
        content=ErrorResponse(
            error=f"{exc.service}_error",
            detail=exc.message,
            service=exc.service,
        ).model_dump(),
    )


@app.exception_handler(PipelineError)
async def pipeline_error_handler(request, exc: PipelineError):
    logger.error("pipeline_error", stage=exc.stage, error=exc.message)
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error="pipeline_error",
            detail=exc.message,
            service=exc.stage,
        ).model_dump(),
    )


@app.exception_handler(ConfigurationError)
async def config_error_handler(request, exc: ConfigurationError):
    logger.error("config_error", missing_keys=exc.missing_keys)
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error="configuration_error",
            detail=exc.message,
        ).model_dump(),
    )


# Routes
@app.get("/health", response_model=HealthCheckResponse)
async def health_check():
    """Health check endpoint."""
    services = {"prisma": "unknown", "evon": "unknown", "timbre": "unknown"}
    
    if pipeline:
        try:
            health = await pipeline.health_check()
            services = {k: "up" if v else "down" for k, v in health.items()}
        except Exception:
            services = {k: "down" for k in services}
    
    overall = "healthy" if all(v == "up" for v in services.values()) else "degraded"
    
    return HealthCheckResponse(
        status=overall,
        services=services,
    )


@app.post("/api/v1/process", response_model=SupportBotResponse)
async def process_audio_base64(request: SupportBotRequest):
    """Process base64 encoded audio through the full pipeline."""
    if not pipeline:
        raise HTTPException(status_code=503, detail="Pipeline not initialized")
    
    try:
        return await pipeline.process(request)
    except Exception as e:
        logger.error("process_failed", error=str(e))
        raise


@app.post("/api/v1/process/file", response_model=SupportBotResponse)
async def process_audio_file(
    file: UploadFile = File(...),
    language: Language = Form(default=Language.AUTO),
    session_id: Optional[str] = Form(default=None),
    context: str = Form(default="{}"),
):
    """Process uploaded audio file through the full pipeline."""
    if not pipeline:
        raise HTTPException(status_code=503, detail="Pipeline not initialized")

    settings = get_settings()
    audio_format = _safe_suffix(file.filename)
    if not audio_format:
        raise HTTPException(status_code=400, detail="Unsupported or missing audio file extension")

    contents = await file.read()
    max_bytes = settings.max_audio_size_mb * 1024 * 1024
    if not contents:
        raise HTTPException(status_code=400, detail="Empty upload")
    if len(contents) > max_bytes:
        raise HTTPException(status_code=413, detail="File too large")

    ctx = _parse_context(context)

    with tempfile.NamedTemporaryFile(delete=False, suffix=f".{audio_format}") as tmp:
        tmp.write(contents)
        tmp_path = tmp.name

    try:
        if not validate_audio_file(tmp_path, settings.max_audio_size_mb):
            raise HTTPException(status_code=400, detail="Invalid audio file")

        audio_base64 = audio_to_base64_file(tmp_path)

        request = SupportBotRequest(
            audio_base64=audio_base64,
            audio_format=audio_format,
            language=language,
            session_id=session_id,
            context=ctx,
        )

        return await pipeline.process(request)

    finally:
        Path(tmp_path).unlink(missing_ok=True)


@app.post("/api/v1/prisma/transcribe")
async def transcribe_only(
    file: UploadFile = File(...),
    language: Language = Form(default=Language.AUTO),
):
    """Transcribe only using Prisma (STT)."""
    if not pipeline:
        raise HTTPException(status_code=503, detail="Pipeline not initialized")

    settings = get_settings()
    audio_format = _safe_suffix(file.filename)
    if not audio_format:
        raise HTTPException(status_code=400, detail="Unsupported or missing audio file extension")

    contents = await file.read()
    max_bytes = settings.max_audio_size_mb * 1024 * 1024
    if not contents:
        raise HTTPException(status_code=400, detail="Empty upload")
    if len(contents) > max_bytes:
        raise HTTPException(status_code=413, detail="File too large")

    with tempfile.NamedTemporaryFile(delete=False, suffix=f".{audio_format}") as tmp:
        tmp.write(contents)
        tmp_path = tmp.name

    try:
        result = await pipeline.prisma.transcribe_file(tmp_path, language=language)
        return result.model_dump()
    finally:
        Path(tmp_path).unlink(missing_ok=True)


@app.get("/api/v1/demo/scenarios")
async def get_demo_scenarios():
    """Get predefined demo scenarios for testing."""
    return {
        "scenarios": [
            {
                "id": "hinglish_refund",
                "name": "Hinglish Refund Request (Noisy)",
                "description": "Customer asks for refund in Hinglish with background noise",
                "audio_file": "assets/sample_audio/hinglish_refund_noisy.wav",
                "expected_intent": "refund_request",
                "expected_language": "hi-en-IN",
            },
            {
                "id": "tamil_complaint",
                "name": "Tamil Product Complaint",
                "description": "Customer complains about defective product in Tamil",
                "audio_file": "assets/sample_audio/tamil_complaint.wav",
                "expected_intent": "complaint",
                "expected_language": "ta-IN",
            },
            {
                "id": "english_order_status",
                "name": "English Order Status Query",
                "description": "Customer checks order status in Indian English",
                "audio_file": "assets/sample_audio/english_order_status.wav",
                "expected_intent": "order_status",
                "expected_language": "en-IN",
            },
            {
                "id": "bengali_technical",
                "name": "Bengali Technical Support",
                "description": "Customer needs technical help in Bengali",
                "audio_file": "assets/sample_audio/bengali_technical.wav",
                "expected_intent": "technical_support",
                "expected_language": "bn-IN",
            },
        ]
    }


@app.get("/")
async def root():
    """Root endpoint with API info."""
    return {
        "name": "Gnani Multilingual Voice Support Bot",
        "version": "0.1.0",
        "description": "Enterprise customer support using Gnani AI Prisma + Evon + Timbre",
        "docs": "/docs",
        "health": "/health",
        "demo": "/api/v1/demo/scenarios",
    }


if __name__ == "__main__":
    import uvicorn
    settings = get_settings()
    uvicorn.run("app.main:app", host="0.0.0.0", port=settings.api_port, reload=settings.debug)