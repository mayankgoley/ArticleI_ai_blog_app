"""
Whisper transcription service module.

This module provides speech-to-text transcription capabilities using
faster-whisper (optimized Whisper implementation), with support for 
automatic language detection, model caching, and comprehensive error handling.

faster-whisper is a lightweight alternative to openai-whisper that:
- Works on Render and other cloud platforms without system dependencies
- Doesn't require PyTorch or CUDA
- Uses ONNX Runtime for efficient CPU inference
- Provides better performance and lower memory usage
"""

import os
import logging
import time
import signal
from pathlib import Path
from typing import Dict, Optional

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
    Load faster-whisper model with caching to avoid reloading.
    
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
        faster-whisper WhisperModel object
        
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
    
    # Validate device - faster-whisper uses different device names
    if device not in ['cpu', 'cuda']:
        logger.warning(f"Invalid device '{device}'. Using 'cpu' instead.")
        device = 'cpu'
    
    # For faster-whisper, we'll use cpu for compatibility
    # CUDA support can be added later if needed
    if device == 'cuda':
        logger.info("faster-whisper: Using CPU for maximum compatibility on Render")
        device = 'cpu'
    
    # Return cached model if available and same size
    if not force_reload and _whisper_model is not None and _model_size_loaded == model_size:
        logger.debug(f"Using cached faster-whisper model: {model_size}")
        return _whisper_model
    
    # Load new model
    logger.info(f"Loading faster-whisper model: {model_size} on {device}")
    
    try:
        from faster_whisper import WhisperModel
        
        # Get model info for logging
        model_info = VALID_MODEL_SIZES.get(model_size, {})
        memory_gb = model_info.get('memory_gb', 'unknown')
        logger.info(f"Model requires approximately {memory_gb}GB of RAM")
        
        # Load the model
        start_time = time.time()
        
        # faster-whisper parameters
        # compute_type: "int8" for CPU (faster, less memory), "float16" for GPU
        compute_type = "int8" if device == "cpu" else "float16"
        
        model = WhisperModel(
            model_size,
            device=device,
            compute_type=compute_type,
            download_root=None,  # Use default cache directory
            local_files_only=False
        )
        
        load_time = time.time() - start_time
        
        # Cache the model
        _whisper_model = model
        _model_size_loaded = model_size
        
        logger.info(
            f"faster-whisper model loaded successfully in {load_time:.2f}s: "
            f"{model_size} on {device} (compute_type: {compute_type})"
        )
        
        return model
        
    except ImportError as e:
        error_msg = (
            "faster-whisper library not installed. "
            "Install with: pip install faster-whisper"
        )
        logger.error(error_msg)
        raise ModelLoadError(error_msg) from e
        
    except MemoryError as e:
        error_msg = (
            f"Insufficient system memory to load {model_size} model. "
            f"Try a smaller model (e.g., 'tiny' or 'base')."
        )
        logger.error(error_msg)
        raise OutOfMemoryError(error_msg) from e
        
    except Exception as e:
        error_msg = f"Failed to load faster-whisper model: {str(e)}"
        logger.error(error_msg)
        raise ModelLoadError(error_msg) from e


def unload_whisper_model() -> None:
    """
    Unload the cached faster-whisper model to free memory.
    
    This can be useful for freeing up resources when the model
    is not expected to be used for a while.
    """
    global _whisper_model, _model_size_loaded
    
    if _whisper_model is not None:
        logger.info(f"Unloading faster-whisper model: {_model_size_loaded}")
        _whisper_model = None
        _model_size_loaded = None
        
        # Force garbage collection
        import gc
        gc.collect()
        
        logger.info("faster-whisper model unloaded successfully")
    else:
        logger.debug("No faster-whisper model loaded to unload")


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
        # For faster-whisper, we'll do a basic file check
        # The actual audio validation happens during transcription
        path = Path(audio_path)
        
        # Check file size is reasonable
        file_size = path.stat().st_size
        if file_size < 1000:  # Less than 1KB is suspicious
            logger.warning(f"Audio file is very small: {file_size} bytes")
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
        
        # Prepare transcription options for faster-whisper
        lang = language or DEFAULT_LANGUAGE
        
        logger.info(
            f"Transcribing with faster-whisper: language={lang or 'auto'} "
            f"(timeout: {timeout}s)"
        )
        
        # Transcribe with timeout handling
        start_time = time.time()
        
        try:
            # Set up timeout (Unix-like systems only)
            if hasattr(signal, 'SIGALRM'):
                signal.signal(signal.SIGALRM, timeout_handler)
                signal.alarm(timeout)
            
            # Perform transcription with faster-whisper
            # faster-whisper returns segments generator and info
            segments, info = model.transcribe(
                audio_path,
                language=lang,
                task='transcribe',
                beam_size=5,
                vad_filter=True,  # Voice activity detection
                vad_parameters=dict(min_silence_duration_ms=500)
            )
            
            # Collect all segments and build full text
            all_segments = list(segments)
            text = ' '.join([segment.text for segment in all_segments]).strip()
            
            # Cancel timeout
            if hasattr(signal, 'SIGALRM'):
                signal.alarm(0)
            
        except TimeoutException:
            raise TranscriptionTimeoutError(
                f"Transcription timed out after {timeout} seconds. "
                f"Try a shorter video or increase timeout."
            )
        
        transcription_time = time.time() - start_time
        
        # Extract results from faster-whisper info object
        detected_language = info.language if hasattr(info, 'language') else 'unknown'
        
        # Calculate confidence from segments
        if all_segments:
            # Average of segment average probabilities
            confidences = [seg.avg_logprob for seg in all_segments if hasattr(seg, 'avg_logprob')]
            if confidences:
                # Convert log probabilities to confidence (0-1 scale)
                # avg_logprob is typically negative, closer to 0 is better
                import math
                avg_confidence = sum([math.exp(c) for c in confidences]) / len(confidences)
                avg_confidence = min(1.0, max(0.0, avg_confidence))  # Clamp to 0-1
            else:
                avg_confidence = 0.8  # Default confidence if not available
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
    Transcribe audio with word-level timestamps using faster-whisper.
    
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
        
        # Prepare language
        lang = language or DEFAULT_LANGUAGE
        
        # Transcribe with faster-whisper
        segments_gen, info = model.transcribe(
            audio_path,
            language=lang,
            task='transcribe',
            beam_size=5,
            word_timestamps=True,
            vad_filter=True
        )
        
        # Collect segments
        all_segments = list(segments_gen)
        
        # Extract full text
        text = ' '.join([seg.text for seg in all_segments]).strip()
        detected_language = info.language if hasattr(info, 'language') else 'unknown'
        
        # Format segments with timestamps
        formatted_segments = []
        for seg in all_segments:
            formatted_segments.append({
                'start': seg.start,
                'end': seg.end,
                'text': seg.text.strip()
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
