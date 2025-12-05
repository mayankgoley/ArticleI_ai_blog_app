from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse, HttpResponse
from django.contrib import messages
from .models import BlogPost
import json
import yt_dlp
from django.conf import settings
import re
from datetime import datetime
import logging
import time

# Import custom exceptions
from .transcription.exceptions import (
    TranscriptionError,
    AudioExtractionError,
    InvalidURLError,
    DurationLimitError,
    NetworkError,
    DiskSpaceError,
    FileSystemPermissionError,
    WhisperError,
    ModelLoadError,
    TranscriptionTimeoutError,
    AudioFormatError,
    OutOfMemoryError,
    TranscriptCleaningError,
    get_user_friendly_error,
    is_user_error
)

# Configure logging for transcription operations
logger = logging.getLogger('transcription')

def index(request):
    return render(request, "index.html")

def user_login(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('/')
        else:
            messages.error(request, 'Invalid username or password')
    
    return render(request, 'login.html')

def user_signup(request):
    if request.method == 'POST':
        username = request.POST['username']
        email = request.POST['email']
        password = request.POST['password']
        confirm_password = request.POST['confirm_password']
        
        if password == confirm_password:
            try:
                user = User.objects.create_user(username, email, password)
                user.save()
                login(request, user)
                return redirect('/')
            except:
                messages.error(request, 'Error creating account')
        else:
            messages.error(request, 'Passwords do not match')
    
    return render(request, 'signup.html')

def user_logout(request):
    logout(request)
    return redirect('/')

@login_required
def all_blogs(request):
    blog_articles = BlogPost.objects.filter(user=request.user)
    return render(request, "all-blogs.html", {'blog_articles': blog_articles})

@login_required
def blog_details(request, pk):
    blog_article_detail = BlogPost.objects.get(id=pk)
    if request.user == blog_article_detail.user:
        return render(request, 'blog-details.html', {'blog_article_detail': blog_article_detail})
    else:
        return redirect('/')

def yt_title(url):
    ydl_opts = {'quiet': True}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info_dict = ydl.extract_info(url, download=False)
            return info_dict.get('title', None)
        except:
            return None

def extract_subtitles(url):
    """
    Extract existing subtitles from YouTube video.
    
    This function attempts to extract subtitles/captions from a YouTube video
    without downloading the video itself. It tries automatic captions first,
    then manual subtitles.
    
    Args:
        url: YouTube video URL
        
    Returns:
        dict: {
            'success': bool,
            'text': str,
            'method': 'subtitles' or 'description',
            'error': str (if failed)
        }
    """
    logger.info(f"Attempting to extract subtitles from: {url}")
    start_time = time.time()
    
    ydl_opts = {
        'writesubtitles': True,
        'writeautomaticsub': True,
        'subtitleslangs': ['en'],
        'skip_download': True,
        'quiet': True
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info_dict = ydl.extract_info(url, download=False)
            video_id = info_dict.get('id', 'unknown')
            video_title = info_dict.get('title', 'Unknown')
            
            # Get video description as fallback
            description = info_dict.get('description', '')
            
            # Try to get subtitles
            subtitles = info_dict.get('subtitles', {})
            auto_subtitles = info_dict.get('automatic_captions', {})
            
            subtitle_text = None
            
            # Try automatic captions first (usually more complete)
            if 'en' in auto_subtitles and auto_subtitles['en']:
                logger.debug(f"Found automatic captions for video {video_id}")
                for subtitle_info in auto_subtitles['en']:
                    if subtitle_info.get('ext') == 'json3':
                        try:
                            subtitle_url = subtitle_info['url']
                            import urllib.request
                            response = urllib.request.urlopen(subtitle_url)
                            subtitle_content = response.read().decode('utf-8')
                            subtitle_text = parse_subtitles(subtitle_content)
                            if subtitle_text and len(subtitle_text.strip()) > 100:
                                break
                        except Exception as e:
                            logger.warning(f"Failed to parse automatic caption: {str(e)}")
                            continue
            
            # Try manual subtitles if auto captions didn't work
            if not subtitle_text and 'en' in subtitles and subtitles['en']:
                logger.debug(f"Found manual subtitles for video {video_id}")
                try:
                    subtitle_url = subtitles['en'][0]['url']
                    import urllib.request
                    response = urllib.request.urlopen(subtitle_url)
                    subtitle_content = response.read().decode('utf-8')
                    subtitle_text = parse_subtitles(subtitle_content)
                except Exception as e:
                    logger.warning(f"Failed to parse manual subtitles: {str(e)}")
            
            # Return subtitles if available
            if subtitle_text and len(subtitle_text.strip()) > 100:
                elapsed_time = time.time() - start_time
                logger.info(
                    f"Subtitles extracted successfully for '{video_title}' "
                    f"(video_id: {video_id}, {len(subtitle_text)} chars, {elapsed_time:.2f}s)"
                )
                return {
                    'success': True,
                    'text': subtitle_text,
                    'method': 'subtitles',
                    'video_id': video_id,
                    'video_title': video_title
                }
            
            # Try description as fallback
            elif description and len(description.strip()) > 50:
                logger.info(f"No subtitles found for video {video_id}, using description")
                # Clean up description
                description = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', description)
                description = re.sub(r'\n+', ' ', description)
                description = re.sub(r'\s+', ' ', description).strip()
                description_text = description[:1000] + "..." if len(description) > 1000 else description
                
                return {
                    'success': True,
                    'text': description_text,
                    'method': 'description',
                    'video_id': video_id,
                    'video_title': video_title
                }
            else:
                logger.warning(f"No subtitles or description found for video {video_id}")
                return {
                    'success': False,
                    'text': '',
                    'method': 'none',
                    'error': 'No subtitles or description available',
                    'video_id': video_id,
                    'video_title': video_title
                }
                
        except Exception as e:
            logger.error(f"Error extracting subtitles: {str(e)}")
            return {
                'success': False,
                'text': '',
                'method': 'none',
                'error': f"Error processing video: {str(e)}"
            }


def yt_transcript(url):
    """
    Extract transcript from YouTube video with ASR fallback.
    
    This function implements an intelligent fallback mechanism:
    1. First, try to extract existing subtitles (fastest)
    2. If subtitles unavailable, use ASR to transcribe audio (slower but comprehensive)
    
    Args:
        url: YouTube video URL
        
    Returns:
        dict: {
            'success': bool,
            'text': str,
            'method': 'subtitles', 'asr', or 'failed',
            'language': str (for ASR),
            'video_id': str,
            'video_title': str,
            'error': str (if failed)
        }
    """
    logger.info(f"Starting transcript extraction for URL: {url}")
    overall_start_time = time.time()
    
    # Step 1: Try existing subtitle extraction
    subtitle_result = extract_subtitles(url)
    
    if subtitle_result['success'] and subtitle_result.get('method') == 'subtitles' and len(subtitle_result['text'].strip()) > 100:
        overall_time = time.time() - overall_start_time
        logger.info(
            f"Transcript extraction completed via subtitles "
            f"(total time: {overall_time:.2f}s)"
        )
        return subtitle_result
    
    # Step 2: Fallback to ASR if enabled
    if getattr(settings, 'ENABLE_ASR', True):
        logger.warning(
            f"No subtitles found for video, falling back to ASR transcription"
        )
        logger.info("STATUS: Downloading audio for transcription...")
        
        audio_path = None
        
        try:
            from .transcription.audio_extractor import extract_audio, cleanup_audio_file
            from .transcription.whisper_service import transcribe_audio
            from .transcription.transcript_cleaner import clean_transcript
            
            # Extract audio
            logger.info("Starting audio extraction for ASR")
            logger.info("STATUS: Downloading audio from video...")
            audio_start_time = time.time()
            
            # extract_audio now raises exceptions directly
            audio_result = extract_audio(url)
            audio_time = time.time() - audio_start_time
            audio_path = audio_result['audio_path']
            
            logger.info(
                f"Audio extracted successfully "
                f"({audio_result.get('file_size_mb', 0):.2f}MB, {audio_time:.2f}s)"
            )
            
            # Transcribe audio
            logger.info("Starting audio transcription with Whisper")
            logger.info("STATUS: Transcribing audio (this may take a few minutes)...")
            transcription_start_time = time.time()
            
            # transcribe_audio returns dict with success/error, check and raise if needed
            transcription = transcribe_audio(audio_path)
            transcription_time = time.time() - transcription_start_time
            
            if not transcription['success']:
                error_msg = transcription.get('error', 'Unknown transcription error')
                logger.error(f"ASR transcription failed: {error_msg}")
                # Determine which exception to raise based on error message
                if 'timeout' in error_msg.lower():
                    raise TranscriptionTimeoutError(error_msg)
                elif 'memory' in error_msg.lower():
                    raise OutOfMemoryError(error_msg)
                elif 'audio' in error_msg.lower() and 'format' in error_msg.lower():
                    raise AudioFormatError(error_msg)
                elif 'model' in error_msg.lower():
                    raise ModelLoadError(error_msg)
                else:
                    raise TranscriptionError(error_msg)
            
            # Clean the transcript
            try:
                cleaned_text = clean_transcript(transcription['text'])
            except TranscriptCleaningError as e:
                logger.warning(f"Transcript cleaning failed: {str(e)}, using original text")
                cleaned_text = transcription['text']
            
            overall_time = time.time() - overall_start_time
            logger.info(
                f"ASR transcription successful: "
                f"language={transcription.get('language', 'unknown')}, "
                f"confidence={transcription.get('confidence', 0):.2f}, "
                f"transcription_time={transcription_time:.2f}s, "
                f"total_time={overall_time:.2f}s, "
                f"chars={len(cleaned_text)}"
            )
            
            return {
                'success': True,
                'text': cleaned_text,
                'method': 'asr',
                'language': transcription.get('language', 'unknown'),
                'confidence': transcription.get('confidence', 0),
                'video_id': audio_result.get('video_id', 'unknown'),
                'video_title': audio_result.get('title', 'Unknown'),
                'processing_time': {
                    'audio_extraction': audio_time,
                    'transcription': transcription_time,
                    'total': overall_time
                }
            }
                
        except (InvalidURLError, DurationLimitError, NetworkError, DiskSpaceError,
                FileSystemPermissionError, AudioExtractionError, ModelLoadError,
                TranscriptionTimeoutError, AudioFormatError, OutOfMemoryError,
                WhisperError, TranscriptionError) as e:
            # Re-raise custom exceptions to be handled by generate_blog
            if isinstance(e, TranscriptionTimeoutError):
                logger.error(f"ASR timed out after {getattr(settings, 'ASR_TIMEOUT', 'unknown')}s: {str(e)}")
            elif isinstance(e, DurationLimitError):
                logger.error(f"Video duration exceeded limit: {str(e)}")
            else:
                logger.error(f"ASR failed with known error: {str(e)}")
            
            # Fallback to description if available
            if subtitle_result['success'] and subtitle_result.get('method') == 'description':
                logger.warning(f"Falling back to video description due to ASR error")
                return subtitle_result
                
            raise
            
        except ImportError as e:
            error_msg = "ASR module not available. Please install required dependencies."
            logger.error(f"{error_msg}: {str(e)}")
            
            # Fallback to description if available
            if subtitle_result['success'] and subtitle_result.get('method') == 'description':
                logger.warning(f"Falling back to video description due to missing ASR module")
                return subtitle_result
                
            raise TranscriptionError(error_msg)
            
        except Exception as e:
            error_msg = f"ASR failed with unexpected error: {str(e)}"
            logger.error(error_msg, exc_info=True)
            
            # Fallback to description if available
            if subtitle_result['success'] and subtitle_result.get('method') == 'description':
                logger.warning(f"Falling back to video description due to unexpected ASR error")
                return subtitle_result
                
            raise TranscriptionError(error_msg)
            
        finally:
            # Always cleanup audio file if it was created
            if audio_path and getattr(settings, 'AUTO_CLEANUP_AUDIO', True):
                try:
                    cleanup_result = cleanup_audio_file(audio_path)
                    if cleanup_result['success']:
                        logger.info(f"Audio file cleaned up: {audio_path}")
                    else:
                        logger.warning(
                            f"Failed to cleanup audio file: "
                            f"{cleanup_result.get('error', 'Unknown error')}"
                        )
                except Exception as cleanup_error:
                    logger.warning(f"Cleanup error: {str(cleanup_error)}")
    
    # No ASR available or disabled
    logger.error("No transcript available and ASR is disabled")
    
    # Fallback to description if available
    if subtitle_result['success'] and subtitle_result.get('method') == 'description':
        logger.warning(f"Using video description as ASR is disabled")
        return subtitle_result

    return {
        'success': False,
        'text': 'No transcript or description available for this video. The video might not have captions enabled.',
        'method': 'none',
        'error': 'No subtitles available and ASR is disabled'
    }

def parse_subtitles(subtitle_content):
    """Parse subtitle content and return clean text"""
    import re
    import json
    
    try:
        # Check if it's JSON format (YouTube's automatic captions)
        if subtitle_content.strip().startswith('{') or '"events"' in subtitle_content:
            try:
                # Parse JSON subtitle format
                data = json.loads(subtitle_content)
                events = data.get('events', [])
                
                text_parts = []
                for event in events:
                    segs = event.get('segs', [])
                    for seg in segs:
                        if 'utf8' in seg:
                            text_parts.append(seg['utf8'])
                
                text = ' '.join(text_parts)
                # Clean up the text
                text = re.sub(r'\s+', ' ', text)
                text = text.replace('\\n', ' ')
                return text.strip()
                
            except json.JSONDecodeError:
                pass
        
        # Handle VTT/SRT format
        text = subtitle_content
        
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', text)
        
        # Remove timestamp lines (VTT format)
        text = re.sub(r'\d+:\d+:\d+[.,]\d+ --> \d+:\d+:\d+[.,]\d+', '', text)
        
        # Remove WEBVTT header
        text = re.sub(r'WEBVTT.*?\n\n', '', text, flags=re.DOTALL)
        
        # Remove standalone numbers (subtitle sequence numbers)
        lines = text.split('\n')
        cleaned_lines = []
        
        for line in lines:
            line = line.strip()
            if line and not line.isdigit() and not re.match(r'^\d+$', line):
                # Skip timestamp-only lines
                if not re.match(r'^\d+:\d+:\d+', line):
                    cleaned_lines.append(line)
        
        # Join lines and clean up spacing
        text = ' '.join(cleaned_lines)
        text = re.sub(r'\s+', ' ', text)
        
        return text.strip()
        
    except Exception as e:
        # Fallback: just clean basic formatting
        text = re.sub(r'[{}"\[\]]', '', subtitle_content)
        text = re.sub(r'\s+', ' ', text)
        return text.strip()

def generate_blog_from_transcript(transcript, options=None):
    """Generate blog content from video transcript with AI enhancements"""
    if not transcript or len(transcript.strip()) < 50:
        return "<p>Unable to generate blog content. The video may not have sufficient transcript data or may be unavailable.</p>"
    
    if options is None:
        options = {}
    
    # Clean and format the transcript
    import re
    
    # Remove extra whitespace and clean up
    text = re.sub(r'\s+', ' ', transcript).strip()
    
    # Remove common filler words and clean up
    text = re.sub(r'\b(um|uh|like|you know|so|well)\b', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\s+', ' ', text)
    
    # Split into sentences more intelligently
    sentences = []
    # Split on sentence endings but keep the punctuation
    parts = re.split(r'([.!?]+)', text)
    
    current_sentence = ""
    for i, part in enumerate(parts):
        if re.match(r'[.!?]+', part):
            current_sentence += part
            if current_sentence.strip():
                sentences.append(current_sentence.strip())
            current_sentence = ""
        else:
            current_sentence += part
    
    # Add any remaining text
    if current_sentence.strip():
        sentences.append(current_sentence.strip())
    
    # Filter and clean sentences
    clean_sentences = []
    for sentence in sentences:
        sentence = sentence.strip()
        # Only include sentences with substantial content
        if len(sentence) > 15 and not sentence.lower().startswith(('http', 'www')):
            # Capitalize first letter
            sentence = sentence[0].upper() + sentence[1:] if sentence else sentence
            clean_sentences.append(sentence)
    
    if not clean_sentences:
        return "<p>Unable to extract meaningful content from the video transcript.</p>"
    
    # Group sentences into paragraphs
    paragraphs = []
    current_paragraph = []
    
    for sentence in clean_sentences:
        current_paragraph.append(sentence)
        
        # Create paragraph every 3-4 sentences or when we hit a natural break
        if len(current_paragraph) >= 3:
            paragraph_text = ' '.join(current_paragraph)
            paragraphs.append(paragraph_text)
            current_paragraph = []
    
    # Add remaining sentences as final paragraph
    if current_paragraph:
        paragraph_text = ' '.join(current_paragraph)
        paragraphs.append(paragraph_text)
    
    # Apply AI enhancements based on options
    writing_style = options.get('writing_style', 'default')
    article_length = options.get('article_length', 'medium')
    custom_instructions = options.get('custom_instructions', '')
    
    # Format as HTML with style-specific enhancements
    formatted_content = ""
    
    if paragraphs:
        # Add introduction based on style
        formatted_content += "<div class='mb-6'>\n"
        
        if writing_style == 'tutorial':
            formatted_content += "<h3 class='text-lg font-semibold mb-3'>📚 Tutorial Guide</h3>\n"
            formatted_content += "<p class='text-gray-600 italic mb-4'>This step-by-step tutorial is generated from a YouTube video and organized for easy learning.</p>\n"
        elif writing_style == 'professional':
            formatted_content += "<h3 class='text-lg font-semibold mb-3'>Executive Summary</h3>\n"
            formatted_content += "<p class='text-gray-600 italic mb-4'>Professional analysis and insights derived from video content.</p>\n"
        elif writing_style == 'academic':
            formatted_content += "<h3 class='text-lg font-semibold mb-3'>Academic Analysis</h3>\n"
            formatted_content += "<p class='text-gray-600 italic mb-4'>Scholarly examination of the presented material with structured analysis.</p>\n"
        else:
            formatted_content += "<h3 class='text-lg font-semibold mb-3'>Article Content</h3>\n"
            formatted_content += "<p class='text-gray-600 italic mb-4'>This article is generated from a YouTube video transcript and has been organized for better readability.</p>\n"
        
        formatted_content += "</div>\n\n"
        
        # Add summary if requested
        if options.get('add_summary'):
            summary_text = ' '.join(paragraphs[:2])[:200] + "..."
            formatted_content += "<div class='bg-blue-50 p-4 rounded-lg mb-6'>\n"
            formatted_content += "<h4 class='font-semibold mb-2'>📋 Quick Summary</h4>\n"
            formatted_content += f"<p class='text-sm text-gray-700'>{summary_text}</p>\n"
            formatted_content += "</div>\n\n"
        
        # Adjust content based on length preference
        if article_length == 'short':
            paragraphs = paragraphs[:3]  # Keep only first 3 paragraphs
        elif article_length == 'comprehensive':
            # Add more detailed sections
            formatted_content += "<h4 class='text-lg font-medium mb-3'>🔍 Detailed Analysis</h4>\n"
        
        # Add main content with style-specific formatting
        for i, paragraph in enumerate(paragraphs):
            if len(paragraph.strip()) > 30:
                if writing_style == 'listicle':
                    formatted_content += f"<div class='mb-4 p-3 bg-gray-50 rounded'>\n"
                    formatted_content += f"<h5 class='font-medium mb-2'>{i+1}. Key Point</h5>\n"
                    formatted_content += f"<p class='leading-relaxed'>{paragraph}</p>\n"
                    formatted_content += "</div>\n\n"
                elif writing_style == 'tutorial':
                    formatted_content += f"<div class='mb-4 p-3 border-l-4 border-blue-500 bg-blue-50'>\n"
                    formatted_content += f"<h5 class='font-medium mb-2'>Step {i+1}</h5>\n"
                    formatted_content += f"<p class='leading-relaxed'>{paragraph}</p>\n"
                    formatted_content += "</div>\n\n"
                else:
                    formatted_content += f"<p class='mb-4 leading-relaxed'>{paragraph}</p>\n\n"
                
                # Add subheadings for longer content
                if len(paragraphs) > 6 and i > 0 and (i + 1) % 3 == 0 and i < len(paragraphs) - 1:
                    section_num = (i // 3) + 1
                    formatted_content += f"<h4 class='text-md font-medium mt-6 mb-3'>Key Points - Part {section_num}</h4>\n"
        
        # Add tags if requested
        if options.get('add_tags'):
            # Generate simple tags based on content
            common_words = ['tutorial', 'guide', 'tips', 'how-to', 'beginner', 'advanced', 'coding', 'development']
            content_lower = ' '.join(paragraphs).lower()
            found_tags = [word for word in common_words if word in content_lower]
            
            if found_tags:
                formatted_content += "<div class='mt-6 p-4 bg-gray-50 rounded-lg'>\n"
                formatted_content += "<h4 class='font-medium mb-2'>🏷️ Tags</h4>\n"
                formatted_content += "<div class='flex flex-wrap gap-2'>\n"
                for tag in found_tags[:5]:  # Limit to 5 tags
                    formatted_content += f"<span class='bg-blue-100 text-blue-800 px-2 py-1 rounded text-sm'>{tag}</span>\n"
                formatted_content += "</div>\n</div>\n"
        
        # Add SEO section if requested
        if options.get('add_seo'):
            formatted_content += "<div class='mt-6 p-4 bg-green-50 rounded-lg'>\n"
            formatted_content += "<h4 class='font-medium mb-2'>🎯 SEO Keywords</h4>\n"
            formatted_content += "<p class='text-sm text-gray-700'>Key topics covered: video content, tutorial, guide, tips, learning</p>\n"
            formatted_content += "</div>\n"
    else:
        formatted_content = "<p>Content processed successfully, but no substantial text could be extracted from the video.</p>"
    
    return formatted_content

@csrf_exempt
def generate_blog(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            yt_link = data.get('link', '').strip()
            
            if not yt_link:
                logger.warning("Blog generation attempted without YouTube link")
                return JsonResponse({'error': 'YouTube link is required'}, status=400)
            
            # Basic URL validation
            if 'youtube.com' not in yt_link and 'youtu.be' not in yt_link:
                logger.warning(f"Invalid YouTube URL provided: {yt_link}")
                return JsonResponse({'error': 'Please provide a valid YouTube URL'}, status=400)
                
        except json.JSONDecodeError:
            logger.error("Invalid JSON data in blog generation request")
            return JsonResponse({'error': 'Invalid JSON data'}, status=400)
        except Exception as e:
            logger.error(f"Invalid request format: {str(e)}")
            return JsonResponse({'error': 'Invalid request format'}, status=400)
        
        try:
            logger.info(f"Starting blog generation for URL: {yt_link}")
            generation_start_time = time.time()
            
            # Get video title
            title = yt_title(yt_link)
            if not title:
                title = "YouTube Video"
            
            logger.info(f"Video title retrieved: {title}")
            
            # Get transcript with status tracking
            try:
                transcript_result = yt_transcript(yt_link)
            except InvalidURLError as e:
                logger.error(f"Invalid URL: {str(e)}")
                return JsonResponse({
                    'error': e.get_user_message(),
                    'success': False,
                    'error_type': 'invalid_url'
                }, status=400)
            except DurationLimitError as e:
                logger.error(f"Duration limit exceeded: {str(e)}")
                return JsonResponse({
                    'error': e.get_user_message(),
                    'success': False,
                    'error_type': 'duration_limit'
                }, status=400)
            except NetworkError as e:
                logger.error(f"Network error: {str(e)}")
                return JsonResponse({
                    'error': e.get_user_message(),
                    'success': False,
                    'error_type': 'network_error'
                }, status=503)
            except DiskSpaceError as e:
                logger.error(f"Disk space error: {str(e)}")
                return JsonResponse({
                    'error': e.get_user_message(),
                    'success': False,
                    'error_type': 'disk_space'
                }, status=507)
            except FileSystemPermissionError as e:
                logger.error(f"File system permission error: {str(e)}")
                return JsonResponse({
                    'error': e.get_user_message(),
                    'success': False,
                    'error_type': 'permission_error'
                }, status=500)
            except AudioExtractionError as e:
                logger.error(f"Audio extraction error: {str(e)}")
                return JsonResponse({
                    'error': e.get_user_message(),
                    'success': False,
                    'error_type': 'audio_extraction'
                }, status=400)
            except ModelLoadError as e:
                logger.error(f"Model load error: {str(e)}")
                return JsonResponse({
                    'error': e.get_user_message(),
                    'success': False,
                    'error_type': 'model_load'
                }, status=503)
            except TranscriptionTimeoutError as e:
                logger.error(f"Transcription timeout: {str(e)}")
                return JsonResponse({
                    'error': e.get_user_message(),
                    'success': False,
                    'error_type': 'timeout'
                }, status=408)
            except AudioFormatError as e:
                logger.error(f"Audio format error: {str(e)}")
                return JsonResponse({
                    'error': e.get_user_message(),
                    'success': False,
                    'error_type': 'audio_format'
                }, status=400)
            except OutOfMemoryError as e:
                logger.error(f"Out of memory error: {str(e)}")
                return JsonResponse({
                    'error': e.get_user_message(),
                    'success': False,
                    'error_type': 'out_of_memory'
                }, status=507)
            except WhisperError as e:
                logger.error(f"Whisper error: {str(e)}")
                return JsonResponse({
                    'error': e.get_user_message(),
                    'success': False,
                    'error_type': 'whisper_error'
                }, status=500)
            except TranscriptionError as e:
                logger.error(f"Transcription error: {str(e)}")
                return JsonResponse({
                    'error': e.get_user_message(),
                    'success': False,
                    'error_type': 'transcription'
                }, status=500)
            
            # Handle transcript extraction failure (for non-exception cases)
            if not transcript_result.get('success', False):
                error_msg = transcript_result.get('error', 'Failed to extract transcript')
                logger.error(f"Transcript extraction failed: {error_msg}")
                
                # Use utility function to get user-friendly message
                user_error = "Unable to extract transcript from the video. Please try a different video."
                
                return JsonResponse({
                    'error': user_error,
                    'success': False,
                    'method': transcript_result.get('method', 'unknown')
                }, status=400)
            
            # Extract transcript text
            transcription = transcript_result.get('text', '')
            method = transcript_result.get('method', 'unknown')
            
            # Log transcription method and metadata
            if method == 'asr':
                processing_time = transcript_result.get('processing_time', {})
                logger.info(
                    f"Transcript obtained via ASR: "
                    f"language={transcript_result.get('language', 'unknown')}, "
                    f"confidence={transcript_result.get('confidence', 0):.2f}, "
                    f"audio_extraction_time={processing_time.get('audio_extraction', 0):.2f}s, "
                    f"transcription_time={processing_time.get('transcription', 0):.2f}s"
                )
            elif method == 'subtitles':
                logger.info(f"Transcript obtained via subtitles")
            elif method == 'description':
                logger.info(f"Transcript obtained via video description")
            
            # Prepare AI options
            ai_options = {
                'writing_style': data.get('writing_style', 'default'),
                'article_length': data.get('article_length', 'medium'),
                'custom_instructions': data.get('custom_instructions', ''),
                'add_seo': data.get('add_seo', False),
                'add_summary': data.get('add_summary', False),
                'add_tags': data.get('add_tags', False)
            }
            
            logger.info(f"Generating blog content with options: {ai_options}")
            
            # Generate blog content with AI enhancements
            blog_content = generate_blog_from_transcript(transcription, ai_options)
            
            # Save to database if user is authenticated
            if request.user.is_authenticated:
                try:
                    blog_article = BlogPost.objects.create(
                        user=request.user,
                        youtube_title=title,
                        youtube_link=yt_link,
                        generated_content=blog_content
                    )
                    blog_article.save()
                    logger.info(
                        f"Blog article saved to database: "
                        f"id={blog_article.id}, user={request.user.username}"
                    )
                except Exception as e:
                    logger.error(f"Failed to save blog article to database: {str(e)}")
                    # Continue even if saving fails
            
            generation_time = time.time() - generation_start_time
            logger.info(
                f"Blog generation completed successfully: "
                f"method={method}, total_time={generation_time:.2f}s"
            )
            
            # Prepare response with metadata
            response_data = {
                'content': blog_content,
                'title': title,
                'success': True,
                'method': method,
                'transcript': transcription  # Include original transcript
            }
            
            # Add ASR-specific metadata if applicable
            if method == 'asr':
                response_data['transcription_info'] = {
                    'language': transcript_result.get('language', 'unknown'),
                    'confidence': transcript_result.get('confidence', 0),
                    'processing_time': transcript_result.get('processing_time', {})
                }
            
            return JsonResponse(response_data)
            
        except TranscriptionError as e:
            # Catch any remaining transcription errors
            logger.error(f"Transcription error: {str(e)}", exc_info=True)
            status_code = 400 if is_user_error(e) else 500
            return JsonResponse({
                'error': e.get_user_message(),
                'success': False,
                'error_type': 'transcription'
            }, status=status_code)
            
        except Exception as e:
            logger.error(
                f"Unexpected error during blog generation: {str(e)}",
                exc_info=True
            )
            # Use utility function to get user-friendly error
            user_error = get_user_friendly_error(e)
            return JsonResponse({
                'error': user_error,
                'success': False,
                'error_type': 'unexpected'
            }, status=500)
    
    logger.warning(f"Invalid HTTP method for generate_blog: {request.method}")
    return JsonResponse({'error': 'Only POST method allowed'}, status=405)

@login_required
@csrf_exempt
def delete_blog(request, pk):
    """Delete a blog article"""
    if request.method == 'POST':
        try:
            blog_article = get_object_or_404(BlogPost, id=pk, user=request.user)
            article_title = blog_article.youtube_title
            blog_article.delete()
            
            logger.info(f"Article deleted: {article_title} (id: {pk}) by user: {request.user.username}")
            
            return JsonResponse({
                'success': True,
                'message': 'Article deleted successfully'
            })
        except Exception as e:
            logger.error(f"Error deleting article {pk}: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)
    
    return JsonResponse({'error': 'Only POST method allowed'}, status=405)


@login_required
def download_blog(request, pk):
    """Download blog article as text file"""
    blog_article = get_object_or_404(BlogPost, id=pk, user=request.user)
    
    # Clean HTML tags from content for plain text
    content = blog_article.generated_content
    content = re.sub(r'<[^>]+>', '', content)  # Remove HTML tags
    content = re.sub(r'\s+', ' ', content)     # Clean up whitespace
    content = content.strip()
    
    # Create the text content
    text_content = f"""
{blog_article.youtube_title}
{'=' * len(blog_article.youtube_title)}

Generated on: {blog_article.created_at.strftime('%B %d, %Y at %I:%M %p')}
Source Video: {blog_article.youtube_link}

Article Content:
{'-' * 50}

{content}

{'-' * 50}
Generated by Article I - AI Blog Generator
"""
    
    # Create filename (sanitize title for filename)
    safe_title = re.sub(r'[^\w\s-]', '', blog_article.youtube_title)
    safe_title = re.sub(r'[-\s]+', '-', safe_title)
    filename = f"{safe_title[:50]}-article.txt"
    
    # Create HTTP response with file download
    response = HttpResponse(text_content, content_type='text/plain')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    return response

@csrf_exempt
def enhance_content(request):
    """Enhance existing blog content with AI"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            content = data.get('content', '')
            enhancement_type = data.get('enhancement_type', '')
            title = data.get('title', '')
            
            if not content:
                return JsonResponse({'error': 'No content provided'}, status=400)
            
            # Apply different enhancements based on type
            enhanced_content = apply_content_enhancement(content, enhancement_type, title)
            
            return JsonResponse({
                'enhanced_content': enhanced_content,
                'success': True
            })
            
        except Exception as e:
            return JsonResponse({
                'error': f'Enhancement failed: {str(e)}',
                'success': False
            }, status=500)
    
    return JsonResponse({'error': 'Only POST method allowed'}, status=405)

def apply_content_enhancement(content, enhancement_type, title):
    """Apply specific content enhancements"""
    # Remove existing HTML tags for processing
    clean_content = re.sub(r'<[^>]+>', '', content)
    clean_content = re.sub(r'\s+', ' ', clean_content).strip()
    
    if enhancement_type == 'improve':
        # Improve writing quality
        sentences = clean_content.split('. ')
        improved_sentences = []
        
        for sentence in sentences:
            sentence = sentence.strip()
            if sentence:
                # Basic improvements: capitalize, add punctuation
                sentence = sentence[0].upper() + sentence[1:] if sentence else sentence
                if not sentence.endswith('.'):
                    sentence += '.'
                improved_sentences.append(sentence)
        
        improved_content = ' '.join(improved_sentences)
        
        return f"""
        <div class='bg-purple-50 p-4 rounded-lg mb-4'>
            <h4 class='font-semibold text-purple-800 mb-2'>✨ Enhanced Version</h4>
            <p class='text-sm text-purple-600'>Content has been improved for better readability and flow.</p>
        </div>
        <div class='prose max-w-none'>
            <p class='leading-relaxed'>{improved_content}</p>
        </div>
        """
    
    elif enhancement_type == 'summarize':
        # Create a summary
        sentences = clean_content.split('. ')
        key_sentences = sentences[:3]  # Take first 3 sentences as summary
        summary = '. '.join(key_sentences) + '.'
        
        return f"""
        <div class='bg-indigo-50 p-4 rounded-lg mb-4'>
            <h4 class='font-semibold text-indigo-800 mb-2'>📝 Summary</h4>
            <p class='text-sm text-indigo-600'>Key points extracted from the original content.</p>
        </div>
        <div class='bg-white p-4 border-l-4 border-indigo-500'>
            <p class='leading-relaxed font-medium'>{summary}</p>
        </div>
        <details class='mt-4'>
            <summary class='cursor-pointer text-indigo-600 hover:text-indigo-800'>View Full Content</summary>
            <div class='mt-2 p-4 bg-gray-50 rounded'>
                <p class='leading-relaxed'>{clean_content}</p>
            </div>
        </details>
        """
    
    elif enhancement_type == 'expand':
        # Expand content with additional sections
        paragraphs = clean_content.split('\n\n')
        
        expanded_content = f"""
        <div class='bg-orange-50 p-4 rounded-lg mb-4'>
            <h4 class='font-semibold text-orange-800 mb-2'>📈 Expanded Content</h4>
            <p class='text-sm text-orange-600'>Additional context and details have been added.</p>
        </div>
        
        <h3 class='text-lg font-semibold mb-3'>Introduction</h3>
        <p class='mb-4 leading-relaxed'>This comprehensive guide covers the key concepts presented in the video, providing detailed explanations and practical insights.</p>
        
        <h3 class='text-lg font-semibold mb-3'>Main Content</h3>
        <p class='mb-4 leading-relaxed'>{clean_content}</p>
        
        <h3 class='text-lg font-semibold mb-3'>Key Takeaways</h3>
        <ul class='list-disc pl-6 mb-4 space-y-2'>
            <li>Understanding the core concepts is essential for implementation</li>
            <li>Practical application requires careful consideration of the presented methods</li>
            <li>Further exploration of these topics can lead to deeper insights</li>
        </ul>
        
        <h3 class='text-lg font-semibold mb-3'>Conclusion</h3>
        <p class='leading-relaxed'>The information presented provides a solid foundation for understanding the topic and can serve as a starting point for further learning and exploration.</p>
        """
        
        return expanded_content
    
    elif enhancement_type == 'seo':
        # Add SEO optimization
        return f"""
        <div class='bg-pink-50 p-4 rounded-lg mb-4'>
            <h4 class='font-semibold text-pink-800 mb-2'>🎯 SEO Optimized</h4>
            <p class='text-sm text-pink-600'>Content has been optimized for search engines.</p>
        </div>
        
        <article class='prose max-w-none'>
            <h1 class='text-2xl font-bold mb-4'>{title}</h1>
            
            <div class='bg-blue-50 p-4 rounded-lg mb-6'>
                <h2 class='text-lg font-semibold mb-2'>📋 Article Overview</h2>
                <p class='text-sm'>This comprehensive guide covers essential information about the topic, providing valuable insights and practical knowledge for readers interested in learning more.</p>
            </div>
            
            <h2 class='text-xl font-semibold mb-3'>Main Content</h2>
            <p class='mb-4 leading-relaxed'>{clean_content}</p>
            
            <div class='bg-gray-50 p-4 rounded-lg mt-6'>
                <h3 class='font-semibold mb-2'>🔍 Related Keywords</h3>
                <div class='flex flex-wrap gap-2'>
                    <span class='bg-blue-100 text-blue-800 px-2 py-1 rounded text-sm'>tutorial</span>
                    <span class='bg-blue-100 text-blue-800 px-2 py-1 rounded text-sm'>guide</span>
                    <span class='bg-blue-100 text-blue-800 px-2 py-1 rounded text-sm'>how-to</span>
                    <span class='bg-blue-100 text-blue-800 px-2 py-1 rounded text-sm'>tips</span>
                    <span class='bg-blue-100 text-blue-800 px-2 py-1 rounded text-sm'>learning</span>
                </div>
            </div>
        </article>
        """
    
    return content  # Return original if no enhancement type matches
