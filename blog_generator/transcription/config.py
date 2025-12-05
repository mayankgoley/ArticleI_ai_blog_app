"""
Configuration management for the transcription module.

This module provides centralized configuration for ASR (Automatic Speech Recognition)
features, including Whisper model settings, audio processing parameters, and
resource management options.
"""

from pathlib import Path
import logging
import os

logger = logging.getLogger(__name__)


# ============================================================================
# Helper function to safely get Django settings
# ============================================================================

def _get_setting(name, default=None):
    """Safely get a Django setting, returning default if Django not configured."""
    try:
        from django.conf import settings
        return getattr(settings, name, default)
    except Exception:
        return default


# ============================================================================
# Whisper Model Configuration
# ============================================================================

# Valid Whisper model sizes with their characteristics
VALID_MODEL_SIZES = {
    'tiny': {'memory_gb': 1, 'speed': 'fastest', 'accuracy': 'lowest'},
    'base': {'memory_gb': 1.5, 'speed': 'fast', 'accuracy': 'good'},
    'small': {'memory_gb': 2.5, 'speed': 'medium', 'accuracy': 'better'},
    'medium': {'memory_gb': 5, 'speed': 'slow', 'accuracy': 'high'},
    'large': {'memory_gb': 10, 'speed': 'slowest', 'accuracy': 'highest'}
}

# Whisper model size to use (tiny, base, small, medium, large)
WHISPER_MODEL_SIZE = _get_setting('WHISPER_MODEL_SIZE', 'base')

# Device to run Whisper on ('cpu' or 'cuda')
WHISPER_DEVICE = _get_setting('WHISPER_DEVICE', 'cpu')

# Valid device options
VALID_DEVICES = ['cpu', 'cuda']


# ============================================================================
# Audio Processing Configuration
# ============================================================================

# Directory for temporary audio files
_base_dir = _get_setting('BASE_DIR', Path.cwd())
_temp_dir = _get_setting('TEMP_AUDIO_DIR', _base_dir / 'temp_audio')
TEMP_AUDIO_DIR = Path(_temp_dir)

# Audio format settings (optimized for Whisper)
AUDIO_FORMAT = 'wav'
AUDIO_SAMPLE_RATE = 16000  # 16kHz is optimal for Whisper
AUDIO_CHANNELS = 1  # Mono audio

# Audio quality settings for extraction
AUDIO_QUALITY = {
    'format': AUDIO_FORMAT,
    'sample_rate': AUDIO_SAMPLE_RATE,
    'channels': AUDIO_CHANNELS,
    'codec': 'pcm_s16le'  # 16-bit PCM
}


# ============================================================================
# Processing Limits and Timeouts
# ============================================================================

# Maximum video duration in seconds (default: 4 hours)
MAX_VIDEO_DURATION = _get_setting('MAX_VIDEO_DURATION', 14400)

# Minimum video duration in seconds (default: 1 second)
MIN_VIDEO_DURATION = _get_setting('MIN_VIDEO_DURATION', 1)

# ASR processing timeout in seconds (default: 240 minutes)
ASR_TIMEOUT = _get_setting('ASR_TIMEOUT', 14400)

# Maximum file size for audio files in MB (default: 1000MB)
MAX_AUDIO_FILE_SIZE_MB = _get_setting('MAX_AUDIO_FILE_SIZE_MB', 1000)


# ============================================================================
# Feature Flags
# ============================================================================

# Enable/disable ASR functionality
ENABLE_ASR = _get_setting('ENABLE_ASR', True)

# Automatically clean up audio files after processing
AUTO_CLEANUP_AUDIO = _get_setting('AUTO_CLEANUP_AUDIO', True)

# Cleanup delay in seconds (0 = immediate)
CLEANUP_DELAY = _get_setting('CLEANUP_DELAY', 0)


# ============================================================================
# Language Configuration
# ============================================================================

# Supported languages for transcription
SUPPORTED_LANGUAGES = [
    'en',  # English
    'es',  # Spanish
    'fr',  # French
    'de',  # German
    'it',  # Italian
    'pt',  # Portuguese
    'nl',  # Dutch
    'pl',  # Polish
    'ru',  # Russian
    'ja',  # Japanese
    'ko',  # Korean
    'zh',  # Chinese
    'ar',  # Arabic
    'hi',  # Hindi
]

# Default language (None = auto-detect)
DEFAULT_LANGUAGE = _get_setting('DEFAULT_TRANSCRIPTION_LANGUAGE', None)


# ============================================================================
# Transcript Cleaning Configuration
# ============================================================================

# Filler words to remove during transcript cleaning
FILLER_WORDS = [
    'um', 'uh', 'like', 'you know', 'i mean', 'sort of', 'kind of',
    'basically', 'actually', 'literally', 'right', 'okay', 'so'
]

# Enable/disable filler word removal
REMOVE_FILLER_WORDS = _get_setting('REMOVE_FILLER_WORDS', True)


# ============================================================================
# Logging Configuration
# ============================================================================

# Log level for transcription operations
TRANSCRIPTION_LOG_LEVEL = _get_setting('TRANSCRIPTION_LOG_LEVEL', 'INFO')


# ============================================================================
# Configuration Validation
# ============================================================================

def validate_configuration():
    """
    Validate all configuration settings and log warnings for invalid values.
    
    Returns:
        tuple: (is_valid: bool, errors: list)
    """
    errors = []
    
    # Validate Whisper model size
    if WHISPER_MODEL_SIZE not in VALID_MODEL_SIZES:
        errors.append(
            f"Invalid WHISPER_MODEL_SIZE '{WHISPER_MODEL_SIZE}'. "
            f"Must be one of: {', '.join(VALID_MODEL_SIZES.keys())}. "
            f"Defaulting to 'base'."
        )
    
    # Validate device
    if WHISPER_DEVICE not in VALID_DEVICES:
        errors.append(
            f"Invalid WHISPER_DEVICE '{WHISPER_DEVICE}'. "
            f"Must be one of: {', '.join(VALID_DEVICES)}. "
            f"Defaulting to 'cpu'."
        )
    
    # Validate video duration limits
    if MAX_VIDEO_DURATION <= 0:
        errors.append(
            f"Invalid MAX_VIDEO_DURATION '{MAX_VIDEO_DURATION}'. "
            f"Must be greater than 0. Defaulting to 3600 seconds."
        )
    
    if MIN_VIDEO_DURATION < 0:
        errors.append(
            f"Invalid MIN_VIDEO_DURATION '{MIN_VIDEO_DURATION}'. "
            f"Must be non-negative. Defaulting to 1 second."
        )
    
    if MIN_VIDEO_DURATION >= MAX_VIDEO_DURATION:
        errors.append(
            f"MIN_VIDEO_DURATION ({MIN_VIDEO_DURATION}) must be less than "
            f"MAX_VIDEO_DURATION ({MAX_VIDEO_DURATION})."
        )
    
    # Validate timeout
    if ASR_TIMEOUT <= 0:
        errors.append(
            f"Invalid ASR_TIMEOUT '{ASR_TIMEOUT}'. "
            f"Must be greater than 0. Defaulting to 300 seconds."
        )
    
    # Validate audio file size limit
    if MAX_AUDIO_FILE_SIZE_MB <= 0:
        errors.append(
            f"Invalid MAX_AUDIO_FILE_SIZE_MB '{MAX_AUDIO_FILE_SIZE_MB}'. "
            f"Must be greater than 0. Defaulting to 500 MB."
        )
    
    # Validate temp directory
    if not TEMP_AUDIO_DIR:
        errors.append("TEMP_AUDIO_DIR is not configured.")
    
    # Validate language
    if DEFAULT_LANGUAGE and DEFAULT_LANGUAGE not in SUPPORTED_LANGUAGES:
        errors.append(
            f"Invalid DEFAULT_TRANSCRIPTION_LANGUAGE '{DEFAULT_LANGUAGE}'. "
            f"Must be one of: {', '.join(SUPPORTED_LANGUAGES)} or None for auto-detect."
        )
    
    # Log errors
    for error in errors:
        logger.warning(f"Configuration validation: {error}")
    
    is_valid = len(errors) == 0
    return is_valid, errors


def get_model_info(model_size=None):
    """
    Get information about a Whisper model size.
    
    Args:
        model_size: Model size to get info for (defaults to configured size)
        
    Returns:
        dict: Model information including memory requirements and characteristics
    """
    size = model_size or WHISPER_MODEL_SIZE
    
    if size not in VALID_MODEL_SIZES:
        logger.warning(f"Unknown model size '{size}', returning info for 'base'")
        size = 'base'
    
    return {
        'size': size,
        **VALID_MODEL_SIZES[size]
    }


def ensure_temp_directory():
    """
    Ensure the temporary audio directory exists.
    
    Returns:
        Path: Path to the temp directory
        
    Raises:
        OSError: If directory cannot be created
    """
    try:
        TEMP_AUDIO_DIR.mkdir(parents=True, exist_ok=True)
        logger.debug(f"Temp audio directory ensured at: {TEMP_AUDIO_DIR}")
        return TEMP_AUDIO_DIR
    except OSError as e:
        logger.error(f"Failed to create temp audio directory: {e}")
        raise


def get_configuration_summary():
    """
    Get a summary of current configuration settings.
    
    Returns:
        dict: Configuration summary
    """
    return {
        'whisper': {
            'model_size': WHISPER_MODEL_SIZE,
            'device': WHISPER_DEVICE,
            'model_info': get_model_info()
        },
        'audio': {
            'format': AUDIO_FORMAT,
            'sample_rate': AUDIO_SAMPLE_RATE,
            'channels': AUDIO_CHANNELS,
            'temp_dir': str(TEMP_AUDIO_DIR)
        },
        'limits': {
            'max_video_duration': MAX_VIDEO_DURATION,
            'min_video_duration': MIN_VIDEO_DURATION,
            'asr_timeout': ASR_TIMEOUT,
            'max_file_size_mb': MAX_AUDIO_FILE_SIZE_MB
        },
        'features': {
            'asr_enabled': ENABLE_ASR,
            'auto_cleanup': AUTO_CLEANUP_AUDIO,
            'remove_filler_words': REMOVE_FILLER_WORDS
        },
        'language': {
            'default': DEFAULT_LANGUAGE,
            'supported': SUPPORTED_LANGUAGES
        }
    }


# ============================================================================
# Initialize Configuration
# ============================================================================

# Validate configuration on module import (only if Django is configured)
try:
    _is_valid, _errors = validate_configuration()

    if not _is_valid:
        logger.warning(
            f"Configuration validation found {len(_errors)} issue(s). "
            "Check logs for details."
        )

    # Ensure temp directory exists
    try:
        ensure_temp_directory()
    except OSError:
        logger.error("Failed to initialize temp audio directory")
except Exception as e:
    # Silently fail if Django isn't configured yet
    logger.debug(f"Configuration initialization deferred: {e}")
