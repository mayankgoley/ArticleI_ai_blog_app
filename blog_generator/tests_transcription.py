"""
Unit tests for transcription components.

Tests for audio_extractor.py, whisper_service.py, and transcript_cleaner.py
"""

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from django.test import TestCase

from blog_generator.transcription import (
    audio_extractor,
    whisper_service,
    transcript_cleaner,
    exceptions
)


# ============================================================================
# Audio Extractor Tests
# ============================================================================

class AudioExtractorTests(TestCase):
    """Tests for audio_extractor.py functions."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.valid_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        self.invalid_url = "https://invalid-url.com/video"
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Clean up test fixtures."""
        # Clean up temp directory
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    @patch('blog_generator.transcription.audio_extractor.yt_dlp.YoutubeDL')
    def test_get_audio_info_success(self, mock_ydl_class):
        """Test successful audio info extraction."""
        # Mock the YoutubeDL instance
        mock_ydl = MagicMock()
        mock_ydl_class.return_value.__enter__.return_value = mock_ydl
        
        # Mock video info
        mock_ydl.extract_info.return_value = {
            'duration': 180,
            'title': 'Test Video',
            'id': 'test123',
            'language': 'en'
        }
        
        result = audio_extractor.get_audio_info(self.valid_url)
        
        self.assertTrue(result['success'])
        self.assertEqual(result['duration'], 180)
        self.assertEqual(result['title'], 'Test Video')
        self.assertEqual(result['video_id'], 'test123')
        self.assertEqual(result['language'], 'en')
    
    @patch('blog_generator.transcription.audio_extractor.yt_dlp.YoutubeDL')
    def test_get_audio_info_invalid_url(self, mock_ydl_class):
        """Test handling of invalid URLs."""
        mock_ydl = MagicMock()
        mock_ydl_class.return_value.__enter__.return_value = mock_ydl
        
        # Simulate download error
        import yt_dlp
        mock_ydl.extract_info.side_effect = yt_dlp.utils.DownloadError("Video not available")
        
        with self.assertRaises(exceptions.InvalidURLError):
            audio_extractor.get_audio_info(self.invalid_url)
    
    def test_validate_video_duration_too_short(self):
        """Test rejection of videos that are too short."""
        # Check the MIN_VIDEO_DURATION from config
        from blog_generator.transcription.config import MIN_VIDEO_DURATION
        if MIN_VIDEO_DURATION > 0:
            with self.assertRaises(exceptions.DurationLimitError):
                audio_extractor.validate_video_duration(MIN_VIDEO_DURATION - 1)
    
    def test_validate_video_duration_too_long(self):
        """Test rejection of videos exceeding duration limit."""
        with self.assertRaises(exceptions.DurationLimitError):
            audio_extractor.validate_video_duration(4000)  # More than 3600 seconds
    
    def test_validate_video_duration_valid(self):
        """Test acceptance of valid video duration."""
        # Should not raise exception
        try:
            audio_extractor.validate_video_duration(300)  # 5 minutes
            audio_extractor.validate_video_duration(1800)  # 30 minutes
        except exceptions.DurationLimitError:
            self.fail("validate_video_duration raised DurationLimitError unexpectedly")
    
    def test_cleanup_audio_file_success(self):
        """Test successful audio file cleanup."""
        # Create a temporary file
        temp_file = os.path.join(self.temp_dir, 'test_audio.wav')
        with open(temp_file, 'w') as f:
            f.write('test')
        
        result = audio_extractor.cleanup_audio_file(temp_file)
        
        self.assertTrue(result['success'])
        self.assertFalse(os.path.exists(temp_file))
    
    def test_cleanup_audio_file_nonexistent(self):
        """Test cleanup of non-existent file."""
        nonexistent_file = os.path.join(self.temp_dir, 'nonexistent.wav')
        
        result = audio_extractor.cleanup_audio_file(nonexistent_file)
        
        # Should succeed (file already gone)
        self.assertTrue(result['success'])


# ============================================================================
# Whisper Service Tests
# ============================================================================

class WhisperServiceTests(TestCase):
    """Tests for whisper_service.py functions."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.test_audio_path = os.path.join(self.temp_dir, 'test_audio.wav')
        
        # Create a dummy audio file
        with open(self.test_audio_path, 'wb') as f:
            f.write(b'RIFF' + b'\x00' * 100)  # Minimal WAV header
    
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
        
        # Unload any cached model
        whisper_service.unload_whisper_model()
    
    def test_validate_audio_file_exists(self):
        """Test validation of existing audio file."""
        # Should not raise exception
        try:
            whisper_service.validate_audio_file(self.test_audio_path)
        except exceptions.AudioFormatError:
            self.fail("validate_audio_file raised AudioFormatError unexpectedly")
    
    def test_validate_audio_file_not_exists(self):
        """Test validation of non-existent audio file."""
        with self.assertRaises(exceptions.AudioFormatError):
            whisper_service.validate_audio_file('/nonexistent/file.wav')
    
    def test_validate_audio_file_empty(self):
        """Test validation of empty audio file."""
        empty_file = os.path.join(self.temp_dir, 'empty.wav')
        with open(empty_file, 'w') as f:
            pass  # Create empty file
        
        with self.assertRaises(exceptions.AudioFormatError):
            whisper_service.validate_audio_file(empty_file)
    
    @patch('whisper.load_model')
    def test_load_whisper_model_success(self, mock_load_model):
        """Test successful Whisper model loading."""
        mock_model = MagicMock()
        mock_load_model.return_value = mock_model
        
        # Unload any cached model first
        whisper_service.unload_whisper_model()
        
        model = whisper_service.load_whisper_model('base')
        
        self.assertIsNotNone(model)
        mock_load_model.assert_called_once()
    
    @patch('whisper.load_model')
    def test_load_whisper_model_caching(self, mock_load_model):
        """Test that model is loaded once and cached."""
        mock_model = MagicMock()
        mock_load_model.return_value = mock_model
        
        # Unload any cached model first
        whisper_service.unload_whisper_model()
        
        # Load model twice
        model1 = whisper_service.load_whisper_model('base')
        model2 = whisper_service.load_whisper_model('base')
        
        # Should only call load_model once (second call uses cache)
        self.assertEqual(mock_load_model.call_count, 1)
        self.assertEqual(model1, model2)
    
    @patch('whisper.load_model')
    def test_load_whisper_model_invalid_size(self, mock_load_model):
        """Test handling of invalid model size."""
        mock_model = MagicMock()
        mock_load_model.return_value = mock_model
        
        # Unload any cached model first
        whisper_service.unload_whisper_model()
        
        # Should default to 'base' for invalid size
        model = whisper_service.load_whisper_model('invalid_size')
        
        # Should still load successfully with default
        self.assertIsNotNone(model)
    
    def test_get_model_info_no_model_loaded(self):
        """Test get_model_info when no model is loaded."""
        whisper_service.unload_whisper_model()
        
        info = whisper_service.get_model_info()
        
        self.assertFalse(info['loaded'])
        self.assertIsNone(info['model_size'])
    
    def test_unload_whisper_model(self):
        """Test unloading Whisper model."""
        # Unload should not raise exception even if no model loaded
        try:
            whisper_service.unload_whisper_model()
        except Exception as e:
            self.fail(f"unload_whisper_model raised exception: {e}")


# ============================================================================
# Transcript Cleaner Tests
# ============================================================================

class TranscriptCleanerTests(TestCase):
    """Tests for transcript_cleaner.py functions."""
    
    def test_remove_timestamps_square_brackets(self):
        """Test removal of square bracket timestamps."""
        text = "[00:00:00] Hello world [00:01:30] This is a test"
        result = transcript_cleaner.remove_timestamps(text)
        
        self.assertNotIn('[00:00:00]', result)
        self.assertNotIn('[00:01:30]', result)
        self.assertIn('Hello world', result)
        self.assertIn('This is a test', result)
    
    def test_remove_timestamps_parentheses(self):
        """Test removal of parenthesis timestamps."""
        text = "(00:00) Hello (01:30) world"
        result = transcript_cleaner.remove_timestamps(text)
        
        self.assertNotIn('(00:00)', result)
        self.assertNotIn('(01:30)', result)
        self.assertIn('Hello', result)
        self.assertIn('world', result)
    
    def test_remove_filler_words(self):
        """Test removal of filler words."""
        text = "Um, so like, you know, this is basically a test, right?"
        result = transcript_cleaner.remove_filler_words(text)
        
        # Filler words should be removed
        self.assertNotIn('Um', result.lower())
        self.assertNotIn('like', result.lower())
        self.assertNotIn('you know', result.lower())
        
        # Content words should remain
        self.assertIn('test', result)
    
    def test_fix_spacing_multiple_spaces(self):
        """Test fixing multiple spaces."""
        text = "Hello    world   test"
        result = transcript_cleaner.fix_spacing(text)
        
        self.assertEqual(result, "Hello world test")
    
    def test_fix_spacing_punctuation(self):
        """Test fixing spacing around punctuation."""
        text = "Hello , world . Test !"
        result = transcript_cleaner.fix_spacing(text)
        
        self.assertEqual(result, "Hello, world. Test!")
    
    def test_fix_punctuation_capitalize_sentences(self):
        """Test capitalizing first letter of sentences."""
        text = "hello world. this is a test. another sentence."
        result = transcript_cleaner.fix_punctuation(text)
        
        self.assertTrue(result.startswith('H'))
        self.assertIn('. T', result)
        self.assertIn('. A', result)
    
    def test_fix_punctuation_add_period(self):
        """Test adding period at end if missing."""
        text = "Hello world"
        result = transcript_cleaner.fix_punctuation(text)
        
        self.assertTrue(result.endswith('.'))
    
    def test_normalize_whitespace(self):
        """Test normalizing whitespace."""
        text = "  Hello\n\n\n\nworld  \n\n  test  "
        result = transcript_cleaner.normalize_whitespace(text)
        
        # Should have at most 2 consecutive newlines
        self.assertNotIn('\n\n\n', result)
        # Should be stripped
        self.assertFalse(result.startswith(' '))
        self.assertFalse(result.endswith(' '))
    
    def test_clean_transcript_full_pipeline(self):
        """Test complete transcript cleaning pipeline."""
        text = """
        [00:00] Um, so like, hello    world .
        [00:30] this is basically a test , you know ?
        """
        
        result = transcript_cleaner.clean_transcript(text)
        
        # Timestamps should be removed
        self.assertNotIn('[00:00]', result)
        self.assertNotIn('[00:30]', result)
        
        # Should be properly formatted
        if result:  # Only check if result is not empty
            self.assertTrue(result[0].isupper() or not result[0].isalpha())  # Starts with capital or non-letter
        self.assertNotIn('  ', result)  # No double spaces
        
        # Should have content
        self.assertGreater(len(result), 0)
    
    def test_clean_transcript_empty_input(self):
        """Test cleaning empty transcript."""
        result = transcript_cleaner.clean_transcript("")
        
        self.assertEqual(result, "")
    
    def test_clean_transcript_preserves_content(self):
        """Test that cleaning preserves important content."""
        text = "The quick brown fox jumps over the lazy dog."
        result = transcript_cleaner.clean_transcript(text)
        
        # All important words should be preserved
        self.assertIn('quick', result)
        self.assertIn('brown', result)
        self.assertIn('fox', result)
        self.assertIn('jumps', result)
    
    def test_segment_transcript_basic(self):
        """Test basic transcript segmentation."""
        text = "First sentence. Second sentence. Third sentence."
        result = transcript_cleaner.segment_transcript(text, max_segment_length=50)
        
        self.assertIsInstance(result, list)
        self.assertGreater(len(result), 0)
        
        # Each segment should be within max length (or single sentence exceeds it)
        for segment in result:
            self.assertLessEqual(len(segment), 100)  # Reasonable upper bound
    
    def test_segment_transcript_empty(self):
        """Test segmentation of empty transcript."""
        result = transcript_cleaner.segment_transcript("")
        
        self.assertEqual(result, [])
    
    def test_segment_transcript_respects_sentences(self):
        """Test that segmentation respects sentence boundaries."""
        text = "First. Second. Third."
        result = transcript_cleaner.segment_transcript(text, max_segment_length=10)
        
        # Should split at sentence boundaries
        for segment in result:
            # Each segment should be a complete sentence or sentences
            self.assertTrue(segment.endswith('.') or segment.endswith('!') or segment.endswith('?'))


# ============================================================================
# Error Handling Tests
# ============================================================================

class ErrorHandlingTests(TestCase):
    """Tests for error handling scenarios."""
    
    def test_invalid_url_error_user_message(self):
        """Test InvalidURLError provides user-friendly message."""
        error = exceptions.InvalidURLError("Technical error message")
        
        user_msg = error.get_user_message()
        
        # Should be user-friendly
        self.assertIn('valid', user_msg.lower())
        self.assertNotIn('Technical', user_msg)
    
    def test_duration_limit_error_user_message(self):
        """Test DurationLimitError provides user-friendly message."""
        error = exceptions.DurationLimitError("Video exceeds 60 minutes")
        
        user_msg = error.get_user_message()
        
        # Should mention duration
        self.assertIn('minute', user_msg.lower())
    
    def test_network_error_user_message(self):
        """Test NetworkError provides user-friendly message."""
        error = exceptions.NetworkError("Connection timeout")
        
        user_msg = error.get_user_message()
        
        # Should mention network/connection
        self.assertIn('network', user_msg.lower())
    
    def test_model_load_error_user_message(self):
        """Test ModelLoadError provides user-friendly message."""
        error = exceptions.ModelLoadError("Failed to load model")
        
        user_msg = error.get_user_message()
        
        # Should not expose technical details
        self.assertNotIn('model', user_msg.lower())
        self.assertIn('service', user_msg.lower())
    
    def test_get_user_friendly_error_transcription_error(self):
        """Test get_user_friendly_error with TranscriptionError."""
        error = exceptions.InvalidURLError("Test error")
        
        msg = exceptions.get_user_friendly_error(error)
        
        self.assertIsInstance(msg, str)
        self.assertGreater(len(msg), 0)
    
    def test_get_user_friendly_error_generic_exception(self):
        """Test get_user_friendly_error with generic exception."""
        error = Exception("Network connection failed")
        
        msg = exceptions.get_user_friendly_error(error)
        
        # Should detect network-related error
        self.assertIn('network', msg.lower())
    
    def test_is_user_error_invalid_url(self):
        """Test is_user_error identifies user errors correctly."""
        error = exceptions.InvalidURLError("Bad URL")
        
        self.assertTrue(exceptions.is_user_error(error))
    
    def test_is_user_error_server_error(self):
        """Test is_user_error identifies server errors correctly."""
        error = exceptions.ModelLoadError("Model failed")
        
        self.assertFalse(exceptions.is_user_error(error))


if __name__ == '__main__':
    unittest.main()
