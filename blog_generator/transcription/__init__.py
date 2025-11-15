"""
Transcription module for automatic speech recognition (ASR) functionality.

This module provides audio extraction, transcription, and text cleaning
capabilities for YouTube videos without subtitles.
"""

__version__ = '1.0.0'

# Export custom exceptions for easy importing
from .exceptions import (
    # Base exceptions
    TranscriptionError,
    
    # Audio extraction exceptions
    AudioExtractionError,
    InvalidURLError,
    DurationLimitError,
    NetworkError,
    DiskSpaceError,
    FileSystemPermissionError,
    
    # Whisper/ASR exceptions
    WhisperError,
    ModelLoadError,
    TranscriptionTimeoutError,
    AudioFormatError,
    OutOfMemoryError,
    
    # Transcript cleaning exceptions
    TranscriptCleaningError,
    
    # Utility functions
    get_user_friendly_error,
    is_user_error,
)

__all__ = [
    # Exceptions
    'TranscriptionError',
    'AudioExtractionError',
    'InvalidURLError',
    'DurationLimitError',
    'NetworkError',
    'DiskSpaceError',
    'FileSystemPermissionError',
    'WhisperError',
    'ModelLoadError',
    'TranscriptionTimeoutError',
    'AudioFormatError',
    'OutOfMemoryError',
    'TranscriptCleaningError',
    # Utilities
    'get_user_friendly_error',
    'is_user_error',
]
