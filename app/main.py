"""FastAPI application for the Multilingual Voice Support Bot."""

import uuid
from contextlib import asynccontextmanager
from typing import Dict, Any
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

logger = structlog.get_logger()

# Global pipeline instance
pipeline: SupportBotPipeline = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global pipeline
    
    logger.info("starting_application")
    
    # Initialize pipeline
    pipeline = SupportBotPipeline()
    
    # Verify configuration
    settings = get_settings()
    if not settings.gnani_api_key:
        logger.warning("gnani_api_key_not_configured")
    
    yield
    
    # Cleanup
    logger.info("shutting_down")
    if pipeline:
        await pipeline.close()


app = FastAPI(
    title="Gnani Multilingual Voice Support Bot",
    description="Enterprise customer support bot using Gnani AI Prisma (STT), Evon (Reasoning), and Timbre (TTS)",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS for demo frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
    session_id: str = Form(default=None),
    context: str = Form(default="{}"),
):
    """Process uploaded audio file through the full pipeline."""
    if not pipeline:
        raise HTTPException(status_code=503, detail="Pipeline not initialized")
    
    # Validate file
    contents = await file.read()
    if len(contents) > get_settings().max_audio_size_mb * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large")
    
    # Save temp file for validation
    import tempfile
    import os
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file.filename.split('.')[-1]}") as tmp:
        tmp.write(contents)
        tmp_path = tmp.name
    
    try:
        if not validate_audio_file(tmp_path, get_settings().max_audio_size_mb):
            raise HTTPException(status_code=400, detail="Invalid audio file")
        
        # Convert to base64
        audio_base64 = audio_to_base64_file(tmp_path)
        
        # Parse context
        import json
        ctx = json.loads(context) if context else {}
        
        request = SupportBotRequest(
            audio_base64=audio_base64,
            audio_format=file.filename.split('.')[-1],
            language=language,
            session_id=session_id,
            context=ctx,
        )
        
        return await pipeline.process(request)
        
    finally:
        os.unlink(tmp_path)


@app.post("/api/v1/prisma/transcribe")
async def transcribe_only(
    file: UploadFile = File(...),
    language: Language = Form(default=Language.AUTO),
):
    """Transcribe only using Prisma (STT)."""
    if not pipeline:
        raise HTTPException(status_code=503, detail="Pipeline not initialized")
    
    contents = await file.read()
    import tempfile, os
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file.filename.split('.')[-1]}") as tmp:
        tmp.write(contents)
        tmp_path = tmp.name
    
    try:
        result = await pipeline.prisma.transcribe_file(tmp_path, language=language)
        return result.model_dump()
    finally:
        os.unlink(tmp_path)


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