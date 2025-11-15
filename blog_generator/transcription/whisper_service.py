"""
Whisper transcription service module.

This module provides speech-to-text transcription capabilities using
OpenAI's Whisper model, with support for automatic language detection,
model caching, and comprehensive error handling.
"""

import os
import logging
import time
import signal
from pathlib import Path
from typing import Dict, Optional
import torch

from .config import (
    WHISPER_MODEL_SIZE,
    WHISPER_DEVICE,
    ASR_TIMEOUT,
    AUDIO_FORMAT,
    AUDIO_SAMPLE_RATE,
    DEFAULT_LANGUAGE,
    SUPPORTED_LANGUAGES,
    VALID_MODEL_SIZES
)
from .exceptions import (
    WhisperError,
    ModelLoadError,
    TranscriptionError,
    AudioFormatError,
    TranscriptionTimeoutError,
    OutOfMemoryError
)

logger = logging.getLogger(__name__)


# ============================================================================
# Global Model Cache
# ============================================================================

_whisper_model = None
_model_size_loaded = None


# ============================================================================
# Timeout Handler
# ============================================================================

class TimeoutException(Exception):
    """Exception raised when operation times out."""
    pass


def timeout_handler(signum, frame):
    """Signal handler for timeout."""
    raise TimeoutException("Operation timed out")


# ============================================================================
# Model Loading Functions
# ============================================================================

def load_whisper_model(model_size: Optional[str] = None, device: Optional[str] = None, force_reload: bool = False) -> object:
    """
    Load Whisper model with caching to avoid reloading.
    
    The model is loaded once and cached in memory. Subsequent calls return
    the cached model unless force_reload is True or a different model size
    is requested.
    
    Args:
        model_size: Whisper model size ('tiny', 'base', 'small', 'medium', 'large').
                   Defaults to configured WHISPER_MODEL_SIZE.
        device: Device to load model on ('cpu' or 'cuda').
               Defaults to configured WHISPER_DEVICE.
        force_reload: Force reload the model even if cached.
        
    Returns:
        Whisper model object
        
    Raises:
        ModelLoadError: If model fails to load
        OutOfMemoryError: If insufficient memory to load model
    """
    global _whisper_model, _model_size_loaded
    
    # Use configured values if not provided
    model_size = model_size or WHISPER_MODEL_SIZE
    device = device or WHISPER_DEVICE
    
    # Validate model size
    if model_size not in VALID_MODEL_SIZES:
        logger.warning(
            f"Invalid model size '{model_size}'. "
            f"Valid options: {', '.join(VALID_MODEL_SIZES.keys())}. "
            f"Using 'base' instead."
        )
        model_size = 'base'
    
    # Validate device
    if device not in ['cpu', 'cuda']:
        logger.warning(f"Invalid device '{device}'. Using 'cpu' instead.")
        device = 'cpu'
    
    # Check if CUDA is available when requested
    if device == 'cuda' and not torch.cuda.is_available():
        logger.warning("CUDA requested but not available. Falling back to CPU.")
        device = 'cpu'
    
    # Return cached model if available and same size
    if not force_reload and _whisper_model is not None and _model_size_loaded == model_size:
        logger.debug(f"Using cached Whisper model: {model_size}")
        return _whisper_model
    
    # Load new model
    logger.info(f"Loading Whisper model: {model_size} on {device}")
    
    try:
        import whisper
        
        # Get model info for logging
        model_info = VALID_MODEL_SIZES.get(model_size, {})
        memory_gb = model_info.get('memory_gb', 'unknown')
        logger.info(f"Model requires approximately {memory_gb}GB of RAM")
        
        # Load the model
        start_time = time.time()
        model = whisper.load_model(model_size, device=device)
        load_time = time.time() - start_time
        
        # Cache the model
        _whisper_model = model
        _model_size_loaded = model_size
        
        logger.info(
            f"Whisper model loaded successfully in {load_time:.2f}s: "
            f"{model_size} on {device}"
        )
        
        return model
        
    except ImportError as e:
        error_msg = (
            "Whisper library not installed. "
            "Install with: pip install openai-whisper"
        )
        logger.error(error_msg)
        raise ModelLoadError(error_msg) from e
        
    except torch.cuda.OutOfMemoryError as e:
        error_msg = (
            f"Insufficient GPU memory to load {model_size} model. "
            f"Try a smaller model or use CPU."
        )
        logger.error(error_msg)
        raise OutOfMemoryError(error_msg) from e
        
    except MemoryError as e:
        error_msg = (
            f"Insufficient system memory to load {model_size} model. "
            f"Try a smaller model (e.g., 'tiny' or 'base')."
        )
        logger.error(error_msg)
        raise OutOfMemoryError(error_msg) from e
        
    except Exception as e:
        error_msg = f"Failed to load Whisper model: {str(e)}"
        logger.error(error_msg)
        raise ModelLoadError(error_msg) from e


def unload_whisper_model() -> None:
    """
    Unload the cached Whisper model to free memory.
    
    This can be useful for freeing up resources when the model
    is not expected to be used for a while.
    """
    global _whisper_model, _model_size_loaded
    
    if _whisper_model is not None:
        logger.info(f"Unloading Whisper model: {_model_size_loaded}")
        _whisper_model = None
        _model_size_loaded = None
        
        # Force garbage collection
        import gc
        gc.collect()
        
        # Clear CUDA cache if available
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        
        logger.info("Whisper model unloaded successfully")
    else:
        logger.debug("No Whisper model loaded to unload")


def get_model_info() -> Dict:
    """
    Get information about the currently loaded model.
    
    Returns:
        dict: {
            'loaded': bool,
            'model_size': str or None,
            'device': str or None,
            'memory_gb': float or None
        }
    """
    if _whisper_model is None:
        return {
            'loaded': False,
            'model_size': None,
            'device': None,
            'memory_gb': None
        }
    
    device = next(_whisper_model.parameters()).device
    model_info = VALID_MODEL_SIZES.get(_model_size_loaded, {})
    
    return {
        'loaded': True,
        'model_size': _model_size_loaded,
        'device': str(device),
        'memory_gb': model_info.get('memory_gb')
    }


# ============================================================================
# Audio Validation Functions
# ============================================================================

def validate_audio_file(audio_path: str) -> None:
    """
    Validate that audio file exists and has correct format.
    
    Args:
        audio_path: Path to audio file
        
    Raises:
        AudioFormatError: If audio file is invalid
    """
    path = Path(audio_path)
    
    # Check if file exists
    if not path.exists():
        raise AudioFormatError(f"Audio file does not exist: {audio_path}")
    
    # Check if file is readable
    if not os.access(path, os.R_OK):
        raise AudioFormatError(f"Audio file is not readable: {audio_path}")
    
    # Check file size
    file_size = path.stat().st_size
    if file_size == 0:
        raise AudioFormatError(f"Audio file is empty: {audio_path}")
    
    # Check file extension
    if path.suffix.lower() not in ['.wav', '.mp3', '.m4a', '.flac', '.ogg']:
        logger.warning(
            f"Audio file has unexpected extension: {path.suffix}. "
            f"Whisper may still be able to process it."
        )
    
    logger.debug(f"Audio file validated: {audio_path} ({file_size} bytes)")


def check_audio_corruption(audio_path: str) -> bool:
    """
    Check if audio file is corrupted by attempting to read it.
    
    Args:
        audio_path: Path to audio file
        
    Returns:
        bool: True if file appears valid, False if corrupted
    """
    try:
        import whisper
        
        # Try to load audio
        audio = whisper.load_audio(audio_path)
        
        # Check if audio data is valid
        if audio is None or len(audio) == 0:
            return False
        
        return True
        
    except Exception as e:
        logger.error(f"Audio file appears corrupted: {str(e)}")
        return False


# ============================================================================
# Transcription Functions
# ============================================================================

def transcribe_audio(
    audio_path: str,
    language: Optional[str] = None,
    model_size: Optional[str] = None,
    timeout: Optional[int] = None
) -> Dict:
    """
    Transcribe audio file using Whisper with automatic language detection.
    
    This function handles the complete transcription process including:
    - Audio validation
    - Model loading
    - Language detection
    - Transcription with timeout handling
    - Error handling for various failure modes
    
    Args:
        audio_path: Path to audio file (WAV format recommended)
        language: Optional language code (e.g., 'en', 'es'). If None, auto-detects.
        model_size: Optional model size override
        timeout: Optional timeout in seconds (defaults to ASR_TIMEOUT)
        
    Returns:
        dict: {
            'success': bool,
            'text': str,
            'language': str,
            'confidence': float,
            'duration': float,
            'error': str (if failed)
        }
        
    Raises:
        AudioFormatError: If audio file is invalid
        TranscriptionTimeoutError: If transcription times out
        OutOfMemoryError: If system runs out of memory
        TranscriptionError: For other transcription errors
    """
    logger.info(f"Starting transcription for: {audio_path}")
    
    # Use default timeout if not provided
    timeout = timeout or ASR_TIMEOUT
    
    try:
        # Validate audio file
        validate_audio_file(audio_path)
        
        # Check for corruption
        if not check_audio_corruption(audio_path):
            raise AudioFormatError(
                "Audio file appears to be corrupted or invalid"
            )
        
        # Validate language if provided
        if language and language not in SUPPORTED_LANGUAGES:
            logger.warning(
                f"Unsupported language '{language}'. "
                f"Will attempt auto-detection."
            )
            language = None
        
        # Load Whisper model
        try:
            model = load_whisper_model(model_size=model_size)
        except (ModelLoadError, OutOfMemoryError) as e:
            raise  # Re-raise model loading errors
        
        # Prepare transcription options
        transcribe_options = {
            'language': language or DEFAULT_LANGUAGE,
            'task': 'transcribe',
            'verbose': False
        }
        
        # Remove language if None (for auto-detection)
        if transcribe_options['language'] is None:
            del transcribe_options['language']
        
        logger.info(
            f"Transcribing with options: {transcribe_options} "
            f"(timeout: {timeout}s)"
        )
        
        # Transcribe with timeout handling
        start_time = time.time()
        
        try:
            # Set up timeout (Unix-like systems only)
            if hasattr(signal, 'SIGALRM'):
                signal.signal(signal.SIGALRM, timeout_handler)
                signal.alarm(timeout)
            
            # Perform transcription
            result = model.transcribe(audio_path, **transcribe_options)
            
            # Cancel timeout
            if hasattr(signal, 'SIGALRM'):
                signal.alarm(0)
            
        except TimeoutException:
            raise TranscriptionTimeoutError(
                f"Transcription timed out after {timeout} seconds. "
                f"Try a shorter video or increase timeout."
            )
        
        transcription_time = time.time() - start_time
        
        # Extract results
        text = result.get('text', '').strip()
        detected_language = result.get('language', 'unknown')
        
        # Calculate confidence (Whisper doesn't provide direct confidence,
        # so we use segment-level probabilities if available)
        segments = result.get('segments', [])
        if segments:
            # Average of segment probabilities
            confidences = [seg.get('no_speech_prob', 0) for seg in segments]
            # Convert no_speech_prob to confidence (inverse)
            avg_confidence = 1.0 - (sum(confidences) / len(confidences))
        else:
            avg_confidence = 0.0
        
        # Validate transcription result
        if not text:
            raise TranscriptionError(
                "Transcription produced empty text. "
                "Audio may be silent or unintelligible."
            )
        
        logger.info(
            f"Transcription successful: {len(text)} characters, "
            f"language: {detected_language}, "
            f"time: {transcription_time:.2f}s, "
            f"confidence: {avg_confidence:.2f}"
        )
        
        return {
            'success': True,
            'text': text,
            'language': detected_language,
            'confidence': avg_confidence,
            'duration': transcription_time
        }
        
    except AudioFormatError as e:
        logger.error(f"Audio format error: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }
        
    except TranscriptionTimeoutError as e:
        logger.error(f"Transcription timeout: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }
        
    except torch.cuda.OutOfMemoryError as e:
        error_msg = (
            "GPU out of memory during transcription. "
            "Try using CPU or a smaller model."
        )
        logger.error(error_msg)
        return {
            'success': False,
            'error': error_msg
        }
        
    except MemoryError as e:
        error_msg = (
            "System out of memory during transcription. "
            "Try a shorter video or smaller model."
        )
        logger.error(error_msg)
        return {
            'success': False,
            'error': error_msg
        }
        
    except Exception as e:
        error_msg = f"Transcription failed: {str(e)}"
        logger.error(error_msg)
        return {
            'success': False,
            'error': error_msg
        }
        
    finally:
        # Ensure timeout is cancelled
        if hasattr(signal, 'SIGALRM'):
            signal.alarm(0)


def transcribe_audio_with_timestamps(
    audio_path: str,
    language: Optional[str] = None,
    model_size: Optional[str] = None
) -> Dict:
    """
    Transcribe audio with word-level timestamps.
    
    This is useful for creating subtitles or time-aligned transcripts.
    
    Args:
        audio_path: Path to audio file
        language: Optional language code
        model_size: Optional model size override
        
    Returns:
        dict: {
            'success': bool,
            'text': str,
            'segments': list of dicts with 'start', 'end', 'text',
            'language': str,
            'error': str (if failed)
        }
    """
    logger.info(f"Starting transcription with timestamps for: {audio_path}")
    
    try:
        # Validate audio file
        validate_audio_file(audio_path)
        
        # Load model
        model = load_whisper_model(model_size=model_size)
        
        # Prepare options
        transcribe_options = {
            'language': language or DEFAULT_LANGUAGE,
            'task': 'transcribe',
            'verbose': False,
            'word_timestamps': True
        }
        
        if transcribe_options['language'] is None:
            del transcribe_options['language']
        
        # Transcribe
        result = model.transcribe(audio_path, **transcribe_options)
        
        # Extract results
        text = result.get('text', '').strip()
        segments = result.get('segments', [])
        detected_language = result.get('language', 'unknown')
        
        # Format segments
        formatted_segments = []
        for seg in segments:
            formatted_segments.append({
                'start': seg.get('start', 0),
                'end': seg.get('end', 0),
                'text': seg.get('text', '').strip()
            })
        
        logger.info(
            f"Transcription with timestamps successful: "
            f"{len(formatted_segments)} segments"
        )
        
        return {
            'success': True,
            'text': text,
            'segments': formatted_segments,
            'language': detected_language
        }
        
    except Exception as e:
        error_msg = f"Transcription with timestamps failed: {str(e)}"
        logger.error(error_msg)
        return {
            'success': False,
            'error': error_msg
        }
