"""
Custom exception classes for the transcription system.

This module defines a hierarchy of exceptions for handling various
error conditions in the audio extraction and transcription process.
All exceptions inherit from TranscriptionError for easy catching.
"""


# ============================================================================
# Base Exception
# ============================================================================

class TranscriptionError(Exception):
    """
    Base exception for all transcription-related errors.
    
    All custom exceptions in the transcription system inherit from this class,
    allowing for easy catching of any transcription-related error.
    """
    
    def __init__(self, message: str, user_message: str = None):
        """
        Initialize the exception.
        
        Args:
            message: Technical error message for logging
            user_message: User-friendly message (optional, defaults to message)
        """
        super().__init__(message)
        self.message = message
        self.user_message = user_message or message
    
    def get_user_message(self) -> str:
        """Get user-friendly error message."""
        return self.user_message


# ============================================================================
# Audio Extraction Exceptions
# ============================================================================

class AudioExtractionError(TranscriptionError):
    """Base exception for audio extraction errors."""
    pass


class InvalidURLError(AudioExtractionError):
    """Raised when the provided URL is invalid or video is unavailable."""
    
    def __init__(self, message: str):
        user_message = "Please provide a valid YouTube URL. The video may be private or unavailable."
        super().__init__(message, user_message)


class DurationLimitError(AudioExtractionError):
    """Raised when video duration exceeds the maximum limit."""
    
    def __init__(self, message: str):
        # Extract duration info if present in message for user-friendly display
        user_message = message if "minute" in message.lower() else \
            "Video exceeds maximum duration limit. Please try a shorter video."
        super().__init__(message, user_message)


class NetworkError(AudioExtractionError):
    """Raised when network-related errors occur."""
    
    def __init__(self, message: str):
        user_message = "Network error occurred. Please check your connection and try again."
        super().__init__(message, user_message)


class DiskSpaceError(AudioExtractionError):
    """Raised when there's insufficient disk space."""
    
    def __init__(self, message: str):
        user_message = "Server storage is full. Please contact the administrator."
        super().__init__(message, user_message)


class FileSystemPermissionError(AudioExtractionError):
    """Raised when file system permission errors occur."""
    
    def __init__(self, message: str):
        user_message = "File system error occurred. Please contact the administrator."
        super().__init__(message, user_message)


# ============================================================================
# Whisper/ASR Exceptions
# ============================================================================

class WhisperError(TranscriptionError):
    """Base exception for Whisper transcription errors."""
    pass


class ModelLoadError(WhisperError):
    """Raised when Whisper model fails to load."""
    
    def __init__(self, message: str):
        user_message = "Transcription service is temporarily unavailable. Please try again later."
        super().__init__(message, user_message)


class TranscriptionTimeoutError(WhisperError):
    """Raised when transcription times out."""
    
    def __init__(self, message: str):
        user_message = "Transcription timed out. The video may be too long. Please try a shorter video."
        super().__init__(message, user_message)


class AudioFormatError(WhisperError):
    """Raised when audio format is invalid."""
    
    def __init__(self, message: str):
        user_message = "Audio file is corrupted or invalid. Please try a different video."
        super().__init__(message, user_message)


class OutOfMemoryError(WhisperError):
    """Raised when system runs out of memory during transcription."""
    
    def __init__(self, message: str):
        user_message = "Video is too large to process. Please try a shorter video or contact the administrator."
        super().__init__(message, user_message)


# ============================================================================
# Transcript Cleaning Exceptions
# ============================================================================

class TranscriptCleaningError(TranscriptionError):
    """Raised when transcript cleaning fails."""
    
    def __init__(self, message: str):
        user_message = "Failed to process transcript text. The content may be invalid."
        super().__init__(message, user_message)


# ============================================================================
# Utility Functions
# ============================================================================

def get_user_friendly_error(exception: Exception) -> str:
    """
    Convert any exception to a user-friendly error message.
    
    Args:
        exception: The exception to convert
        
    Returns:
        User-friendly error message string
    """
    if isinstance(exception, TranscriptionError):
        return exception.get_user_message()
    
    # Handle common exception types
    error_str = str(exception).lower()
    
    if 'network' in error_str or 'connection' in error_str or 'timeout' in error_str:
        return "Network error occurred. Please check your connection and try again."
    elif 'permission' in error_str or 'access denied' in error_str:
        return "File system error occurred. Please contact the administrator."
    elif 'memory' in error_str or 'out of memory' in error_str:
        return "Video is too large to process. Please try a shorter video."
    elif 'not found' in error_str or 'unavailable' in error_str:
        return "Video not found or unavailable. Please check the URL and try again."
    elif 'invalid' in error_str or 'corrupted' in error_str:
        return "Invalid or corrupted content. Please try a different video."
    else:
        return "An unexpected error occurred. Please try again or contact support."


def is_user_error(exception: Exception) -> bool:
    """
    Determine if an error is due to user input (4xx) or server issue (5xx).
    
    Args:
        exception: The exception to check
        
    Returns:
        True if user error (4xx), False if server error (5xx)
    """
    user_error_types = (
        InvalidURLError,
        DurationLimitError,
        AudioFormatError,
    )
    
    return isinstance(exception, user_error_types)
