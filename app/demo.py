"""Gradio demo interface for the Multilingual Voice Support Bot."""

import base64
import io
import tempfile
import os
from typing import Optional, Tuple
import gradio as gr
import numpy as np
import structlog

from app.core.config import get_settings
from app.pipelines.support_bot import SupportBotPipeline
from app.models.enums import Language, Intent, Sentiment, ResolutionAction, BotMode
from app.utils.audio import decode_audio_base64, encode_audio_base64
from app.services.mock_clients import create_pipeline

logger = structlog.get_logger()

# Global pipeline for demo
_demo_pipeline: Optional[SupportBotPipeline] = None


def get_demo_pipeline() -> SupportBotPipeline:
    """Get or create demo pipeline instance."""
    global _demo_pipeline
    if _demo_pipeline is None:
        # Use mock clients if no API key configured
        settings = get_settings()
        # Empty key or any documented placeholder value means "run in mock/demo mode".
        use_mock = not settings.gnani_api_key or settings.gnani_api_key.startswith("your_")
        if use_mock:
            logger.info("using_mock_clients_for_demo")
        _demo_pipeline = create_pipeline(use_mock=use_mock)
    return _demo_pipeline


async def process_audio_demo(
    audio_file: str,
    language: str,
    session_id: str,
    context_json: str,
    mode: str,
) -> Tuple[str, str, str, str, str, str, str, str, str]:
    """
    Process audio through the pipeline and return results for Gradio.
    
    Returns:
        Tuple of (transcript, detected_language, intent, sentiment, resolution, 
                 response_text, response_audio_path, latency_info, error)
    """
    if audio_file is None:
        return "", "", "", "", "", "", "", "", "Please upload or record audio first."
    
    pipeline = get_demo_pipeline()
    
    try:
        # Read audio file and convert to base64
        with open(audio_file, "rb") as f:
            audio_base64 = base64.b64encode(f.read()).decode("utf-8")
        
        # Parse language
        lang = Language(language) if language != "auto" else Language.AUTO
        
        # Parse context
        context = {}
        if context_json.strip():
            import json
            context = json.loads(context_json)
        
        # Process through pipeline
        from app.models.schemas import SupportBotRequest
        request = SupportBotRequest(
            audio_base64=audio_base64,
            audio_format="wav",
            language=lang,
            session_id=session_id if session_id.strip() else None,
            context=context,
            mode=BotMode(mode),
        )
        response = await pipeline.process(request)
        
        # Save response audio to temp file for Gradio playback
        audio_bytes = base64.b64decode(response.response_audio_base64)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
            tmp.write(audio_bytes)
            response_audio_path = tmp.name
        
        # Format latency info
        latency_lines = [f"Total: {response.total_latency_ms}ms"]
        for stage, ms in response.latency_breakdown.items():
            if stage != "total_ms":
                latency_lines.append(f"  {stage}: {ms}ms")
        latency_info = "\n".join(latency_lines)
        
        return (
            response.transcript,
            response.detected_language.display_name,
            response.intent.value,
            response.sentiment.value,
            response.resolution.value,
            response.response_text,
            response_audio_path,
            latency_info,
            "",  # No error
        )
        
    except Exception as e:
        logger.error("demo_process_failed", error=str(e))
        return "", "", "", "", "", "", "", "", f"Error: {str(e)}"


async def process_microphone_demo(
    audio: Tuple[int, np.ndarray],
    language: str,
    session_id: str,
    context_json: str,
    mode: str,
) -> Tuple[str, str, str, str, str, str, str, str, str]:
    """Process microphone input from Gradio."""
    if audio is None:
        return "", "", "", "", "", "", "", "", "Please record audio first."
    
    sr, audio_data = audio
    
    # Save to temp file
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
        import soundfile as sf
        sf.write(tmp.name, audio_data, sr)
        return await process_audio_demo(tmp.name, language, session_id, context_json, mode)


def create_demo_interface() -> gr.Blocks:
    """Create the Gradio demo interface."""
    
    # Custom CSS for better styling
    css = """
    .gradio-container {
        max-width: 1200px !important;
    }
    .latency-box {
        font-family: 'Monospace', monospace;
        background: #1e1e1e;
        color: #00ff00;
        padding: 10px;
        border-radius: 5px;
        white-space: pre;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 15px;
        border-radius: 10px;
        text-align: center;
    }
    .header-text {
        text-align: center;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: bold;
    }
    .mode-badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.85em;
        font-weight: bold;
        margin-left: 10px;
    }
    .mode-mock { background: #fff3cd; color: #856404; }
    .mode-real { background: #d4edda; color: #155724; }
    """
    
    with gr.Blocks(css=css, title="Gnani Multilingual Voice Support Bot") as demo:
        # Header
        gr.HTML("""
        <div style="text-align: center; padding: 20px;">
            <h1 class="header-text" style="font-size: 2.5em;">🎙️ Gnani Multilingual Voice Support Bot</h1>
            <p style="font-size: 1.2em; color: #666;">
                Powered by <strong>Prisma (STT)</strong> + <strong>Evon (Reasoning)</strong> + <strong>Timbre (TTS)</strong>
            </p>
            <p style="color: #888;">
                <em>Great Indian AI Internship Challenge 2026 Entry</em>
            </p>
            <div id="mode-indicator" style="margin-top: 10px;"></div>
        </div>
        """)
        
        with gr.Row():
            # Left column: Input
            with gr.Column(scale=1):
                gr.HTML("<h3>📥 Input</h3>")
                
                # Audio input tabs
                with gr.Tabs():
                    with gr.TabItem("📁 Upload File"):
                        audio_file = gr.Audio(
                            label="Upload Audio File",
                            type="filepath",
                            format="wav",
                        )
                    
                    with gr.TabItem("🎤 Record Microphone"):
                        audio_mic = gr.Audio(
                            label="Record from Microphone",
                            type="numpy",
                            format="wav",
                        )
                
                # Mode selection
                mode = gr.Radio(
                    choices=[
                        ("Support Agent", "SUPPORT"),
                        ("Real-time Translator", "TRANSLATE"),
                    ],
                    value="SUPPORT",
                    label="Bot Mode",
                )
                
                # Language selection
                language = gr.Dropdown(
                    label="Language (Auto-detect recommended)",
                    choices=[
                        ("Auto-detect", "auto"),
                        ("Hindi (हिंदी)", "hi-IN"),
                        ("English (India)", "en-IN"),
                        ("Hinglish (Hindi+English)", "hi-en-IN"),
                        ("Tamil (தமிழ்)", "ta-IN"),
                        ("Tanglish (Tamil+English)", "ta-en-IN"),
                        ("Bengali (বাংলা)", "bn-IN"),
                        ("Telugu (తెలుగు)", "te-IN"),
                        ("Marathi (मराठी)", "mr-IN"),
                        ("Gujarati (ગુજરાતી)", "gu-IN"),
                        ("Kannada (ಕನ್ನಡ)", "kn-IN"),
                        ("Malayalam (മലയാളം)", "ml-IN"),
                        ("Punjabi (ਪੰਜਾਬੀ)", "pa-IN"),
                    ],
                    value="auto",
                )
                
                # Session ID (optional)
                session_id = gr.Textbox(
                    label="Session ID (optional - for conversation continuity)",
                    placeholder="Leave blank for new session",
                    value="",
                )
                
                # Context JSON (optional)
                context_json = gr.Textbox(
                    label="Context JSON (optional)",
                    placeholder='{"customer_tier": "premium", "order_id": "12345"}',
                    value="{}",
                    lines=3,
                )
                
                # Process button
                process_btn = gr.Button("🚀 Process", variant="primary", size="lg")
                
                # Error display
                error_output = gr.Textbox(
                    label="Status / Errors",
                    interactive=False,
                    visible=False,
                )
            
            # Right column: Output
            with gr.Column(scale=1):
                gr.HTML("<h3>📤 Output</h3>")
                
                # Results in cards
                with gr.Row():
                    with gr.Column():
                        transcript = gr.Textbox(
                            label="📝 Transcript (Prisma)",
                            lines=3,
                            interactive=False,
                        )
                        detected_lang = gr.Textbox(
                            label="🌐 Detected Language",
                            interactive=False,
                        )
                    
                    with gr.Column():
                        intent = gr.Textbox(
                            label="🎯 Intent (Evon)",
                            interactive=False,
                        )
                        sentiment = gr.Textbox(
                            label="😊 Sentiment",
                            interactive=False,
                        )
                
                with gr.Row():
                    with gr.Column():
                        resolution = gr.Textbox(
                            label="⚡ Resolution Action",
                            interactive=False,
                        )
                    
                    with gr.Column():
                        pass  # Spacer
                
                # Response text
                response_text = gr.Textbox(
                    label="💬 Bot Response (Evon Generated)",
                    lines=3,
                    interactive=False,
                )
                
                # Response audio
                response_audio = gr.Audio(
                    label="🔊 Bot Voice Response (Timbre)",
                    type="filepath",
                    interactive=False,
                )
                
                # Latency info
                latency_info = gr.Textbox(
                    label="⏱️ Latency Breakdown",
                    lines=6,
                    interactive=False,
                    elem_classes=["latency-box"],
                )
        
        # Demo scenarios section
        gr.HTML("<hr style='margin: 30px 0;'>")
        gr.HTML("<h2 class='header-text' style='font-size: 1.5em;'>🎬 Demo Scenarios</h2>")
        gr.HTML("<p style='color: #666;'>Click a scenario to run it with simulated audio (works without API keys)</p>")
        
        with gr.Row():
            scenario_buttons = []
            scenarios = [
                ("Hinglish Refund (Noisy)", "hinglish_refund_noisy.wav", "hi-en-IN"),
                ("Tamil Complaint", "tamil_complaint.wav", "ta-IN"),
                ("English Order Status", "english_order_status.wav", "en-IN"),
                ("Bengali Technical", "bengali_technical.wav", "bn-IN"),
            ]
            
            for name, filename, lang in scenarios:
                btn = gr.Button(f"▶ {name}", size="sm")
                scenario_buttons.append((btn, filename, lang))
        
        # Wire up event handlers
        async def run_demo(file_path, lang, sess_id, ctx, mode):
            results = await process_audio_demo(file_path, lang, sess_id, ctx, mode)
            return results
        
        async def run_mic(audio, lang, sess_id, ctx, mode):
            results = await process_microphone_demo(audio, lang, sess_id, ctx, mode)
            return results
        
        # File upload processing
        process_btn.click(
            fn=run_demo,
            inputs=[audio_file, language, session_id, context_json, mode],
            outputs=[
                transcript, detected_lang, intent, sentiment, resolution,
                response_text, response_audio, latency_info, error_output
            ],
        ).then(
            fn=lambda err: gr.update(visible=bool(err)),
            inputs=[error_output],
            outputs=[error_output],
        )
        
        # Microphone processing
        audio_mic.change(
            fn=run_mic,
            inputs=[audio_mic, language, session_id, context_json, mode],
            outputs=[
                transcript, detected_lang, intent, sentiment, resolution,
                response_text, response_audio, latency_info, error_output
            ],
        ).then(
            fn=lambda err: gr.update(visible=bool(err)),
            inputs=[error_output],
            outputs=[error_output],
        )
        
        # Scenario buttons
        for btn, filename, lang in scenario_buttons:
            btn.click(
                fn=lambda f=filename, l=lang: run_demo(
                    f"assets/sample_audio/{f}", l, "", "{}", "SUPPORT"
                ),
                inputs=[],
                outputs=[
                    transcript, detected_lang, intent, sentiment, resolution,
                    response_text, response_audio, latency_info, error_output
                ],
            ).then(
                fn=lambda err: gr.update(visible=bool(err)),
                inputs=[error_output],
                outputs=[error_output],
            )
        
        # Footer
        gr.HTML("""
        <div style="text-align: center; padding: 20px; color: #888; border-top: 1px solid #eee; margin-top: 30px;">
            <p>Built for <strong>#GnaniAI #GreatIndianAIInternshipChallenge</strong></p>
            <p>GitHub: <a href="https://github.com/Salaz8117/gnani-multilingual-support-bot" target="_blank">Salaz8117/gnani-multilingual-support-bot</a></p>
        </div>
        """)
        
        # Add JavaScript to show mode indicator
        gr.HTML("""
        <script>
        setTimeout(() => {
            const indicator = document.getElementById('mode-indicator');
            if (indicator) {
                // Check if mock mode by looking for a hidden element we'll add
                indicator.innerHTML = '<span class="mode-badge mode-mock">🎭 Demo Mode (Mock APIs)</span>';
            }
        }, 500);
        </script>
        """)
    
    return demo


def launch_demo():
    """Launch the Gradio demo."""
    settings = get_settings()
    demo = create_demo_interface()
    demo.launch(
        server_name="0.0.0.0",
        server_port=settings.demo_port,
        share=False,
        show_error=True,
    )


if __name__ == "__main__":
    launch_demo()