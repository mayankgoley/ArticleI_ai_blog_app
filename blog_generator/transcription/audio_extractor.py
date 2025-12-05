"""
Audio extraction module for YouTube videos.

This module handles downloading and extracting audio from YouTube videos
using yt-dlp, with proper error handling and validation.
"""

import os
import logging
import time
from pathlib import Path
from typing import Dict, Optional
import yt_dlp
import shutil
import base64

from .config import (
    TEMP_AUDIO_DIR,
    AUDIO_FORMAT,
    AUDIO_SAMPLE_RATE,
    AUDIO_CHANNELS,
    MAX_VIDEO_DURATION,
    MIN_VIDEO_DURATION,
    MAX_AUDIO_FILE_SIZE_MB,
    ensure_temp_directory
)
from .exceptions import (
    AudioExtractionError,
    InvalidURLError,
    DurationLimitError,
    NetworkError,
    DiskSpaceError,
    FileSystemPermissionError
)

logger = logging.getLogger(__name__)


# ============================================================================
# Core Functions
# ============================================================================

def _setup_cookies() -> Optional[str]:
    """
    Setup cookies from environment variable if available.
    Returns path to cookies file or None.
    """
    cookies_path = Path('cookies/cookies.txt')
    
    # Check if cookies provided via env var (secure way for Render)
    cookies_b64 = os.environ.get('YOUTUBE_COOKIES_BASE64')
    if cookies_b64:
        try:
            # Ensure directory exists
            cookies_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Decode and write to file
            cookies_content = base64.b64decode(cookies_b64)
            with open(cookies_path, 'wb') as f:
                f.write(cookies_content)
            logger.info("Successfully loaded YouTube cookies from environment variable")
            return str(cookies_path)
        except Exception as e:
            logger.error(f"Failed to load cookies from environment variable: {e}")
            
    # Return path if file exists (local dev or manually added)
    if cookies_path.exists():
        return str(cookies_path)
        
    return None

def get_audio_info(youtube_url: str) -> Dict:
    """
    Get audio metadata from a YouTube video without downloading.
    
    Args:
        youtube_url: YouTube video URL
        
    Returns:
        dict: {
            'success': bool,
            'duration': float (seconds),
            'title': str,
            'video_id': str,
            'language': str,
            'error': str (if failed)
        }
        
    Raises:
        InvalidURLError: If the URL is invalid
        NetworkError: If network errors occur
    """
    logger.info(f"Fetching audio info for URL: {youtube_url}")
    
    # Setup cookies
    cookies_file = _setup_cookies()
    
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': False,
        # YouTube-specific options to bypass bot detection
        'extractor_args': {
            'youtube': {
                'player_client': ['android', 'ios', 'web'],
                'skip': ['hls', 'dash']
            }
        },
        # Use cookies if available
        'cookiefile': cookies_file,
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(youtube_url, download=False)
            
            if not info:
                raise InvalidURLError("Unable to extract video information")
            
            duration = info.get('duration', 0)
            title = info.get('title', 'Unknown')
            video_id = info.get('id', 'unknown')
            language = info.get('language', 'unknown')
            
            logger.info(
                f"Video info retrieved: {title} "
                f"(duration: {duration}s, id: {video_id})"
            )
            
            return {
                'success': True,
                'duration': duration,
                'title': title,
                'video_id': video_id,
                'language': language
            }
            
    except yt_dlp.utils.DownloadError as e:
        error_msg = str(e)
        logger.error(f"Failed to fetch video info: {error_msg}")
        
        if 'not available' in error_msg.lower() or 'private' in error_msg.lower():
            raise InvalidURLError("Video is not available or is private")
        elif 'network' in error_msg.lower() or 'connection' in error_msg.lower():
            raise NetworkError(f"Network error while fetching video info: {error_msg}")
        else:
            raise InvalidURLError(f"Invalid YouTube URL or video unavailable: {error_msg}")
            
    except Exception as e:
        logger.error(f"Unexpected error fetching video info: {str(e)}")
        raise AudioExtractionError(f"Failed to fetch video information: {str(e)}")



def validate_video_duration(duration: float) -> None:
    """
    Validate that video duration is within acceptable limits.
    
    Args:
        duration: Video duration in seconds
        
    Raises:
        DurationLimitError: If duration is outside acceptable range
    """
    if duration < MIN_VIDEO_DURATION:
        raise DurationLimitError(
            f"Video is too short ({duration}s). "
            f"Minimum duration is {MIN_VIDEO_DURATION}s"
        )
    
    if duration > MAX_VIDEO_DURATION:
        minutes = MAX_VIDEO_DURATION / 60
        raise DurationLimitError(
            f"Video exceeds maximum duration of {minutes:.0f} minutes. "
            f"Video duration: {duration / 60:.1f} minutes"
        )
    
    logger.debug(f"Video duration validated: {duration}s")


def check_disk_space(required_mb: float = 100) -> None:
    """
    Check if there's sufficient disk space available.
    
    Args:
        required_mb: Required disk space in MB
        
    Raises:
        DiskSpaceError: If insufficient disk space
    """
    try:
        stat = os.statvfs(TEMP_AUDIO_DIR)
        available_mb = (stat.f_bavail * stat.f_frsize) / (1024 * 1024)
        
        if available_mb < required_mb:
            raise DiskSpaceError(
                f"Insufficient disk space. Required: {required_mb}MB, "
                f"Available: {available_mb:.1f}MB"
            )
        
        logger.debug(f"Disk space check passed: {available_mb:.1f}MB available")
        
    except AttributeError:
        # statvfs not available on Windows
        logger.warning("Disk space check not available on this platform")
    except Exception as e:
        logger.warning(f"Could not check disk space: {str(e)}")



def extract_audio(youtube_url: str, output_path: Optional[str] = None) -> Dict:
    """
    Extract audio from a YouTube video and save as WAV file.
    
    This function downloads audio from a YouTube video, converts it to
    WAV format (16kHz, mono) optimized for Whisper transcription, and
    saves it to the specified path.
    
    Args:
        youtube_url: YouTube video URL
        output_path: Optional custom output path. If None, generates automatic path.
        
    Returns:
        dict: {
            'success': bool,
            'audio_path': str,
            'duration': float,
            'video_id': str,
            'title': str,
            'file_size_mb': float,
            'error': str (if failed)
        }
        
    Raises:
        InvalidURLError: If the URL is invalid
        DurationLimitError: If video duration exceeds limits
        NetworkError: If network errors occur
        DiskSpaceError: If insufficient disk space
        FileSystemPermissionError: If file system permission errors occur
        AudioExtractionError: For other extraction errors
    """
    logger.info(f"Starting audio extraction for URL: {youtube_url}")
    
    try:
        # Ensure temp directory exists
        ensure_temp_directory()
        
        # Check disk space
        check_disk_space(required_mb=200)
        
        # Get video info and validate duration
        info = get_audio_info(youtube_url)
        duration = info['duration']
        video_id = info['video_id']
        title = info['title']
        
        validate_video_duration(duration)
        
        # Generate output path if not provided
        if output_path is None:
            timestamp = int(time.time())
            filename = f"{video_id}_{timestamp}.{AUDIO_FORMAT}"
            output_path = TEMP_AUDIO_DIR / filename
        else:
            output_path = Path(output_path)
        
        # Ensure parent directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Downloading audio to: {output_path}")
        
        # Setup cookies
        cookies_file = _setup_cookies()
        
        # Configure yt-dlp options for audio extraction
        ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': AUDIO_FORMAT,
                'preferredquality': '192',
            }],
            'outtmpl': str(output_path.with_suffix('')),  # yt-dlp adds extension
            'quiet': False,
            'no_warnings': False,
            'postprocessor_args': [
                '-ar', str(AUDIO_SAMPLE_RATE),  # Sample rate: 16kHz
                '-ac', str(AUDIO_CHANNELS),      # Channels: mono
            ],
            # FFmpeg location (dynamically resolved)
            'ffmpeg_location': shutil.which('ffmpeg') or '/usr/bin/ffmpeg',
            # Force IPv4 (helps with some data center IP blocks)
            'source_address': '0.0.0.0',
            # YouTube-specific options to bypass bot detection
            'extractor_args': {
                'youtube': {
                    'player_client': ['android', 'ios', 'web'],
                    'skip': ['hls', 'dash']
                }
            },
            # Use cookies if available (helps with rate limiting)
            'cookiefile': cookies_file,
        }
        
        # Download and extract audio
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([youtube_url])
        except yt_dlp.utils.DownloadError as e:
            error_msg = str(e)
            logger.error(f"Download failed: {error_msg}")
            
            if 'not available' in error_msg.lower():
                raise InvalidURLError("Video is not available or is private")
            elif 'network' in error_msg.lower() or 'timeout' in error_msg.lower():
                raise NetworkError(f"Network error during download: {error_msg}")
            else:
                raise AudioExtractionError(f"Download failed: {error_msg}")
        
        # Verify the output file exists
        final_path = output_path.with_suffix(f'.{AUDIO_FORMAT}')
        if not final_path.exists():
            raise AudioExtractionError(
                f"Audio file was not created at expected path: {final_path}"
            )
        
        # Get file size
        file_size_bytes = final_path.stat().st_size
        file_size_mb = file_size_bytes / (1024 * 1024)
        
        # Validate file size
        if file_size_mb > MAX_AUDIO_FILE_SIZE_MB:
            # Clean up the file
            try:
                final_path.unlink()
            except Exception:
                pass
            raise AudioExtractionError(
                f"Audio file too large ({file_size_mb:.1f}MB). "
                f"Maximum allowed: {MAX_AUDIO_FILE_SIZE_MB}MB"
            )
        
        logger.info(
            f"Audio extraction successful: {final_path} "
            f"({file_size_mb:.2f}MB, {duration}s)"
        )
        
        return {
            'success': True,
            'audio_path': str(final_path),
            'duration': duration,
            'video_id': video_id,
            'title': title,
            'file_size_mb': file_size_mb
        }
        
    except (InvalidURLError, DurationLimitError, NetworkError, 
            DiskSpaceError, AudioExtractionError) as e:
        # Re-raise known exceptions for proper error handling
        logger.error(f"Audio extraction failed: {str(e)}")
        raise
        
    except OSError as e:
        error_msg = str(e)
        logger.error(f"File system error: {error_msg}")
        
        if 'permission' in error_msg.lower():
            raise FileSystemPermissionError(
                f"Permission denied when accessing file system: {error_msg}"
            )
        else:
            raise AudioExtractionError(f"File system error: {error_msg}")
            
    except Exception as e:
        error_msg = f"Unexpected error during audio extraction: {str(e)}"
        logger.error(error_msg)
        raise AudioExtractionError(error_msg)



def cleanup_audio_file(audio_path: str) -> Dict:
    """
    Delete a temporary audio file.
    
    Args:
        audio_path: Path to the audio file to delete
        
    Returns:
        dict: {
            'success': bool,
            'path': str,
            'error': str (if failed)
        }
    """
    logger.info(f"Cleaning up audio file: {audio_path}")
    
    try:
        path = Path(audio_path)
        
        if not path.exists():
            logger.warning(f"Audio file does not exist: {audio_path}")
            return {
                'success': True,
                'path': audio_path,
                'message': 'File does not exist (already cleaned up)'
            }
        
        # Delete the file
        path.unlink()
        
        logger.info(f"Audio file deleted successfully: {audio_path}")
        
        return {
            'success': True,
            'path': audio_path
        }
        
    except OSError as e:
        error_msg = f"Failed to delete audio file: {str(e)}"
        logger.error(error_msg)
        
        return {
            'success': False,
            'path': audio_path,
            'error': error_msg
        }
        
    except Exception as e:
        error_msg = f"Unexpected error during cleanup: {str(e)}"
        logger.error(error_msg)
        
        return {
            'success': False,
            'path': audio_path,
            'error': error_msg
        }


def cleanup_old_audio_files(max_age_hours: int = 24) -> Dict:
    """
    Clean up old audio files from the temp directory.
    
    Args:
        max_age_hours: Maximum age of files to keep (in hours)
        
    Returns:
        dict: {
            'success': bool,
            'deleted_count': int,
            'failed_count': int,
            'errors': list
        }
    """
    logger.info(f"Cleaning up audio files older than {max_age_hours} hours")
    
    try:
        ensure_temp_directory()
        
        current_time = time.time()
        max_age_seconds = max_age_hours * 3600
        
        deleted_count = 0
        failed_count = 0
        errors = []
        
        # Iterate through files in temp directory
        for file_path in TEMP_AUDIO_DIR.glob(f'*.{AUDIO_FORMAT}'):
            try:
                # Check file age
                file_age = current_time - file_path.stat().st_mtime
                
                if file_age > max_age_seconds:
                    file_path.unlink()
                    deleted_count += 1
                    logger.debug(f"Deleted old file: {file_path}")
                    
            except Exception as e:
                failed_count += 1
                error_msg = f"Failed to delete {file_path}: {str(e)}"
                errors.append(error_msg)
                logger.warning(error_msg)
        
        logger.info(
            f"Cleanup complete: {deleted_count} deleted, {failed_count} failed"
        )
        
        return {
            'success': True,
            'deleted_count': deleted_count,
            'failed_count': failed_count,
            'errors': errors
        }
        
    except Exception as e:
        error_msg = f"Failed to clean up old files: {str(e)}"
        logger.error(error_msg)
        
        return {
            'success': False,
            'deleted_count': 0,
            'failed_count': 0,
            'errors': [error_msg]
        }
