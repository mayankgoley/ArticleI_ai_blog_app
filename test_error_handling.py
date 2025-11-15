#!/usr/bin/env python
"""
Test script to verify comprehensive error handling in the transcription system.

This script tests:
1. Custom exception classes
2. User-friendly error messages
3. Exception hierarchy
4. Error type detection
"""

import sys
import os

# Add the project to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from blog_generator.transcription.exceptions import (
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


def test_exception_hierarchy():
    """Test that exception hierarchy is correct."""
    print("Testing exception hierarchy...")
    
    # Test AudioExtractionError hierarchy
    assert issubclass(AudioExtractionError, TranscriptionError)
    assert issubclass(InvalidURLError, AudioExtractionError)
    assert issubclass(DurationLimitError, AudioExtractionError)
    assert issubclass(NetworkError, AudioExtractionError)
    assert issubclass(DiskSpaceError, AudioExtractionError)
    assert issubclass(FileSystemPermissionError, AudioExtractionError)
    
    # Test WhisperError hierarchy
    assert issubclass(WhisperError, TranscriptionError)
    assert issubclass(ModelLoadError, WhisperError)
    assert issubclass(TranscriptionTimeoutError, WhisperError)
    assert issubclass(AudioFormatError, WhisperError)
    assert issubclass(OutOfMemoryError, WhisperError)
    
    # Test TranscriptCleaningError hierarchy
    assert issubclass(TranscriptCleaningError, TranscriptionError)
    
    print("✓ Exception hierarchy is correct")


def test_user_messages():
    """Test that user-friendly messages are generated correctly."""
    print("\nTesting user-friendly error messages...")
    
    test_cases = [
        (InvalidURLError("Technical: video ID not found"), 
         "Please provide a valid YouTube URL"),
        
        (DurationLimitError("Video exceeds maximum duration of 60 minutes. Video duration: 75.5 minutes"),
         "Video exceeds maximum duration of 60 minutes"),
        
        (NetworkError("Connection timeout after 30 seconds"),
         "Network error occurred"),
        
        (DiskSpaceError("Insufficient disk space. Required: 200MB, Available: 50MB"),
         "Server storage is full"),
        
        (FileSystemPermissionError("Permission denied when accessing /tmp/audio"),
         "File system error occurred"),
        
        (ModelLoadError("Failed to load Whisper model: model file not found"),
         "Transcription service is temporarily unavailable"),
        
        (TranscriptionTimeoutError("Transcription timed out after 300 seconds"),
         "Transcription timed out"),
        
        (AudioFormatError("Audio file is corrupted or invalid"),
         "Audio file is corrupted or invalid"),
        
        (OutOfMemoryError("Insufficient GPU memory to load large model"),
         "Video is too large to process"),
        
        (TranscriptCleaningError("Failed to parse transcript text"),
         "Failed to process transcript text"),
    ]
    
    for exception, expected_substring in test_cases:
        user_msg = exception.get_user_message()
        assert expected_substring.lower() in user_msg.lower(), \
            f"Expected '{expected_substring}' in '{user_msg}'"
        print(f"✓ {exception.__class__.__name__}: {user_msg}")
    
    print("✓ All user messages are correct")


def test_user_error_detection():
    """Test that user errors are correctly identified."""
    print("\nTesting user error detection...")
    
    # User errors (4xx)
    user_errors = [
        InvalidURLError("Invalid URL"),
        DurationLimitError("Duration exceeded"),
        AudioFormatError("Invalid format"),
    ]
    
    for error in user_errors:
        assert is_user_error(error), f"{error.__class__.__name__} should be a user error"
        print(f"✓ {error.__class__.__name__} correctly identified as user error")
    
    # Server errors (5xx)
    server_errors = [
        NetworkError("Network error"),
        DiskSpaceError("Disk full"),
        FileSystemPermissionError("Permission denied"),
        ModelLoadError("Model load failed"),
        TranscriptionTimeoutError("Timeout"),
        OutOfMemoryError("Out of memory"),
        WhisperError("Whisper error"),
        TranscriptionError("Generic error"),
    ]
    
    for error in server_errors:
        assert not is_user_error(error), f"{error.__class__.__name__} should be a server error"
        print(f"✓ {error.__class__.__name__} correctly identified as server error")
    
    print("✓ User error detection is correct")


def test_generic_error_handling():
    """Test handling of generic exceptions."""
    print("\nTesting generic error handling...")
    
    test_cases = [
        (Exception("Network connection failed"), "Network error occurred"),
        (Exception("Permission denied"), "File system error occurred"),
        (Exception("Out of memory"), "Video is too large to process"),
        (Exception("File not found"), "Video not found or unavailable"),
        (Exception("Invalid data"), "Invalid or corrupted content"),
        (Exception("Some random error"), "An unexpected error occurred"),
    ]
    
    for exception, expected_substring in test_cases:
        user_msg = get_user_friendly_error(exception)
        assert expected_substring.lower() in user_msg.lower(), \
            f"Expected '{expected_substring}' in '{user_msg}' for {exception}"
        print(f"✓ Generic error '{str(exception)[:30]}...' -> '{user_msg}'")
    
    print("✓ Generic error handling is correct")


def test_exception_catching():
    """Test that exceptions can be caught properly."""
    print("\nTesting exception catching...")
    
    # Test catching specific exception
    try:
        raise InvalidURLError("Test error")
    except InvalidURLError as e:
        print(f"✓ Caught InvalidURLError: {e.get_user_message()}")
    
    # Test catching parent exception
    try:
        raise DurationLimitError("Test error")
    except AudioExtractionError as e:
        print(f"✓ Caught DurationLimitError as AudioExtractionError: {e.get_user_message()}")
    
    # Test catching base exception
    try:
        raise ModelLoadError("Test error")
    except TranscriptionError as e:
        print(f"✓ Caught ModelLoadError as TranscriptionError: {e.get_user_message()}")
    
    print("✓ Exception catching works correctly")


def test_error_message_security():
    """Test that error messages don't expose internal details."""
    print("\nTesting error message security...")
    
    # Create exceptions with internal details
    exceptions = [
        InvalidURLError("Database connection failed at /internal/path/db.sqlite"),
        NetworkError("Failed to connect to internal server 192.168.1.100:5432"),
        FileSystemPermissionError("Permission denied: /var/www/secret/config.py"),
    ]
    
    for exception in exceptions:
        user_msg = exception.get_user_message()
        
        # Check that internal details are not exposed
        assert "/internal/" not in user_msg, "Internal path exposed"
        assert "192.168" not in user_msg, "Internal IP exposed"
        assert "/var/www/" not in user_msg, "Internal path exposed"
        assert "config.py" not in user_msg, "Internal file exposed"
        
        print(f"✓ {exception.__class__.__name__} doesn't expose internal details")
    
    print("✓ Error messages are secure")


def main():
    """Run all tests."""
    print("=" * 70)
    print("COMPREHENSIVE ERROR HANDLING TEST SUITE")
    print("=" * 70)
    
    try:
        test_exception_hierarchy()
        test_user_messages()
        test_user_error_detection()
        test_generic_error_handling()
        test_exception_catching()
        test_error_message_security()
        
        print("\n" + "=" * 70)
        print("✓ ALL TESTS PASSED!")
        print("=" * 70)
        return 0
        
    except AssertionError as e:
        print(f"\n✗ TEST FAILED: {e}")
        return 1
    except Exception as e:
        print(f"\n✗ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
