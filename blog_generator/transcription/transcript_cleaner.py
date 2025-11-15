"""
Transcript cleaning utilities for ASR-generated transcripts.

This module provides functions to clean and normalize transcribed text,
removing filler words, fixing spacing and punctuation, and normalizing formatting.
"""

import re
import logging
from .exceptions import TranscriptCleaningError

logger = logging.getLogger(__name__)


# Common filler words to remove
FILLER_WORDS = [
    r'\bum\b', r'\buh\b', r'\blike\b', r'\byou know\b', r'\bI mean\b',
    r'\bso\b', r'\bbasically\b', r'\bactually\b', r'\bliterally\b',
    r'\bkind of\b', r'\bsort of\b', r'\byeah\b', r'\bokay\b', r'\bwell\b',
    r'\bright\b', r'\balright\b', r'\bmm\b', r'\bhmm\b', r'\buh-huh\b',
    r'\buh huh\b', r'\bmm-hmm\b', r'\bmm hmm\b'
]


def remove_timestamps(text: str) -> str:
    """
    Remove timestamp patterns from transcript text.
    
    Handles various timestamp formats:
    - [00:00:00]
    - [0:00]
    - (00:00)
    - 00:00:00 -->
    - <00:00:00>
    
    Args:
        text: Input text with potential timestamps
        
    Returns:
        Text with timestamps removed
    """
    # Remove square bracket timestamps [00:00:00] or [0:00]
    text = re.sub(r'\[\d{1,2}:\d{2}(?::\d{2})?\]', '', text)
    
    # Remove parenthesis timestamps (00:00)
    text = re.sub(r'\(\d{1,2}:\d{2}(?::\d{2})?\)', '', text)
    
    # Remove SRT-style timestamps (00:00:00 --> 00:00:00)
    text = re.sub(r'\d{2}:\d{2}:\d{2}(?:,\d{3})?\s*-->\s*\d{2}:\d{2}:\d{2}(?:,\d{3})?', '', text)
    
    # Remove angle bracket timestamps <00:00:00>
    text = re.sub(r'<\d{1,2}:\d{2}(?::\d{2})?>', '', text)
    
    # Remove standalone timestamps at start of lines
    text = re.sub(r'^\d{1,2}:\d{2}(?::\d{2})?\s*', '', text, flags=re.MULTILINE)
    
    return text


def remove_filler_words(text: str) -> str:
    """
    Remove common filler words from transcript.
    
    Args:
        text: Input text with filler words
        
    Returns:
        Text with filler words removed
    """
    cleaned_text = text
    
    for filler in FILLER_WORDS:
        # Remove filler words (case-insensitive), preserving surrounding spaces
        cleaned_text = re.sub(filler, ' ', cleaned_text, flags=re.IGNORECASE)
    
    return cleaned_text


def fix_spacing(text: str) -> str:
    """
    Fix spacing issues in transcript.
    
    - Remove multiple spaces
    - Fix spacing around punctuation
    - Remove spaces at start/end of lines
    
    Args:
        text: Input text with spacing issues
        
    Returns:
        Text with corrected spacing
    """
    # Remove multiple spaces
    text = re.sub(r' {2,}', ' ', text)
    
    # Remove spaces before punctuation
    text = re.sub(r'\s+([.,!?;:])', r'\1', text)
    
    # Ensure space after punctuation (if not at end of string)
    text = re.sub(r'([.,!?;:])([A-Za-z])', r'\1 \2', text)
    
    # Remove spaces at start and end of lines
    text = re.sub(r'^\s+|\s+$', '', text, flags=re.MULTILINE)
    
    return text


def fix_punctuation(text: str) -> str:
    """
    Fix common punctuation issues in transcripts.
    
    - Ensure sentences start with capital letters
    - Remove multiple punctuation marks
    - Add periods to sentences without ending punctuation
    
    Args:
        text: Input text with punctuation issues
        
    Returns:
        Text with corrected punctuation
    """
    # Remove multiple punctuation marks
    text = re.sub(r'([.,!?;:]){2,}', r'\1', text)
    
    # Capitalize first letter of sentences (after . ! ?)
    text = re.sub(r'([.!?]\s+)([a-z])', lambda m: m.group(1) + m.group(2).upper(), text)
    
    # Capitalize first letter of text
    if text:
        text = text[0].upper() + text[1:] if len(text) > 1 else text.upper()
    
    # Add period at end if missing
    if text and not text[-1] in '.!?':
        text += '.'
    
    return text


def normalize_whitespace(text: str) -> str:
    """
    Normalize whitespace in transcript.
    
    - Convert multiple newlines to double newlines (paragraph breaks)
    - Remove trailing/leading whitespace
    - Normalize line endings
    
    Args:
        text: Input text with irregular whitespace
        
    Returns:
        Text with normalized whitespace
    """
    # Normalize line endings to \n
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    
    # Remove multiple consecutive newlines (keep max 2 for paragraph breaks)
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    # Remove trailing/leading whitespace from entire text
    text = text.strip()
    
    return text


def clean_transcript(text: str) -> str:
    """
    Clean and normalize transcript text.
    
    Performs the following operations:
    1. Remove timestamps
    2. Remove filler words
    3. Fix spacing
    4. Fix punctuation
    5. Normalize whitespace
    
    Args:
        text: Raw transcript text
        
    Returns:
        Cleaned and normalized transcript text
        
    Raises:
        TranscriptCleaningError: If cleaning fails
    """
    if not text or not isinstance(text, str):
        logger.warning("Empty or invalid text provided for cleaning")
        return ""
    
    try:
        # Step 1: Remove timestamps
        cleaned = remove_timestamps(text)
        
        # Step 2: Remove filler words
        cleaned = remove_filler_words(cleaned)
        
        # Step 3: Fix spacing
        cleaned = fix_spacing(cleaned)
        
        # Step 4: Fix punctuation
        cleaned = fix_punctuation(cleaned)
        
        # Step 5: Normalize whitespace
        cleaned = normalize_whitespace(cleaned)
        
        # Validate result
        if not cleaned or len(cleaned.strip()) < 10:
            logger.warning("Cleaning resulted in very short or empty text")
            # Return original text if cleaning produced nothing useful
            return text.strip()
        
        logger.debug(f"Transcript cleaned: {len(text)} -> {len(cleaned)} chars")
        return cleaned
        
    except Exception as e:
        error_msg = f"Failed to clean transcript: {str(e)}"
        logger.error(error_msg)
        # Return original text rather than failing completely
        logger.info("Returning original text due to cleaning error")
        return text.strip()


def segment_transcript(text: str, max_segment_length: int = 500) -> list:
    """
    Split transcript into logical segments for blog generation.
    
    Attempts to split at sentence boundaries while respecting max length.
    
    Args:
        text: Cleaned transcript text
        max_segment_length: Maximum characters per segment
        
    Returns:
        List of text segments
    """
    if not text:
        return []
    
    # Split into sentences
    sentences = re.split(r'(?<=[.!?])\s+', text)
    
    segments = []
    current_segment = ""
    
    for sentence in sentences:
        # If adding this sentence would exceed max length
        if len(current_segment) + len(sentence) + 1 > max_segment_length:
            # Save current segment if not empty
            if current_segment:
                segments.append(current_segment.strip())
                current_segment = sentence
            else:
                # Single sentence exceeds max length, add it anyway
                segments.append(sentence.strip())
        else:
            # Add sentence to current segment
            if current_segment:
                current_segment += " " + sentence
            else:
                current_segment = sentence
    
    # Add remaining segment
    if current_segment:
        segments.append(current_segment.strip())
    
    return segments
