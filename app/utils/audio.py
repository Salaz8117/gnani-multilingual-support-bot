"""Audio processing utilities."""

import base64
import io
from typing import Optional, Tuple
import numpy as np
from pydub import AudioSegment
import soundfile as sf


def decode_audio_base64(audio_base64: str) -> bytes:
    """Decode base64 audio to bytes."""
    return base64.b64decode(audio_base64)


def encode_audio_base64(audio_bytes: bytes) -> str:
    """Encode audio bytes to base64."""
    return base64.b64encode(audio_bytes).decode("utf-8")


def load_audio(file_path: str, target_sr: int = 16000) -> Tuple[np.ndarray, int]:
    """Load audio file and resample to target sample rate."""
    audio, sr = sf.read(file_path)
    
    # Convert to mono if stereo
    if len(audio.shape) > 1:
        audio = np.mean(audio, axis=1)
    
    # Resample if needed
    if sr != target_sr:
        import librosa
        audio = librosa.resample(audio, orig_sr=sr, target_sr=target_sr)
        sr = target_sr
    
    return audio, sr


def save_audio(audio: np.ndarray, file_path: str, sample_rate: int = 16000):
    """Save audio array to file."""
    sf.write(file_path, audio, sample_rate)


def convert_audio_format(
    input_path: str,
    output_path: str,
    target_format: str = "wav",
    target_sr: int = 16000,
):
    """Convert audio file to target format and sample rate."""
    audio = AudioSegment.from_file(input_path)
    
    # Convert to mono
    audio = audio.set_channels(1)
    
    # Resample
    audio = audio.set_frame_rate(target_sr)
    
    # Export
    audio.export(output_path, format=target_format)


def get_audio_duration(file_path: str) -> float:
    """Get audio duration in seconds."""
    audio = AudioSegment.from_file(file_path)
    return len(audio) / 1000.0


def validate_audio_file(file_path: str, max_size_mb: int = 25) -> bool:
    """Validate audio file size and format."""
    import os
    
    # Check file size
    size_mb = os.path.getsize(file_path) / (1024 * 1024)
    if size_mb > max_size_mb:
        return False
    
    # Check if readable
    try:
        AudioSegment.from_file(file_path)
        return True
    except Exception:
        return False


def split_audio_on_silence(
    file_path: str,
    min_silence_len: int = 500,
    silence_thresh: int = -40,
    keep_silence: int = 100,
) -> list:
    """Split audio on silence for processing long files."""
    audio = AudioSegment.from_file(file_path)
    
    from pydub.silence import split_on_silence
    chunks = split_on_silence(
        audio,
        min_silence_len=min_silence_len,
        silence_thresh=silence_thresh,
        keep_silence=keep_silence,
    )
    
    return chunks


def normalize_audio(audio: np.ndarray, target_db: float = -20.0) -> np.ndarray:
    """Normalize audio to target dB level."""
    import librosa
    
    # Calculate current RMS
    rms = np.sqrt(np.mean(audio**2))
    if rms == 0:
        return audio
    
    # Target RMS for target_db
    target_rms = 10**(target_db / 20.0)
    
    # Scale
    return audio * (target_rms / rms)


def audio_to_base64_file(file_path: str) -> str:
    """Convert audio file directly to base64."""
    with open(file_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def base64_to_audio_file(base64_str: str, output_path: str):
    """Save base64 audio to file."""
    audio_bytes = base64.b64decode(base64_str)
    with open(output_path, "wb") as f:
        f.write(audio_bytes)