"""
Utility functions for Deep Researcher
"""

import base64
import os
import re
from io import BytesIO
from typing import Optional

from PIL import Image


def clean_filename(filename: str) -> str:
    """Clean a string to make it suitable for use as a filename
    
    Args:
        filename: String to clean
        
    Returns:
        str: Cleaned filename
    """
    # Replace invalid characters with underscores
    cleaned = re.sub(r'[\\/*?:"<>|]', '_', filename)
    # Replace multiple spaces/underscores with single underscore
    cleaned = re.sub(r'[\s_]+', '_', cleaned)
    # Remove leading/trailing underscores and spaces
    cleaned = cleaned.strip('_').strip()
    # Limit length
    return cleaned[:50]


def save_screenshot(base64_image: str, filepath: str) -> Optional[str]:
    """Save a base64 encoded image to a file
    
    Args:
        base64_image: Base64 encoded image string
        filepath: Path to save the file
        
    Returns:
        Optional[str]: Path to saved file or None if failed
    """
    try:
        # Make sure the directory exists
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        # Decode the image
        img_data = base64.b64decode(base64_image)
        img = Image.open(BytesIO(img_data))
        
        # Save the image
        img.save(filepath)
        return filepath
    except Exception as e:
        import logging
        logger = logging.getLogger("deep_researcher.utils")
        logger.error(f"Error saving screenshot to {filepath}: {e}")
        return None


def format_time_elapsed(seconds: float) -> str:
    """Format seconds into a human-readable time string
    
    Args:
        seconds: Number of seconds
        
    Returns:
        str: Formatted time string
    """
    if seconds < 60:
        return f"{seconds:.1f} seconds"
    elif seconds < 3600:
        minutes = seconds // 60
        remaining_seconds = seconds % 60
        return f"{int(minutes)} minutes, {int(remaining_seconds)} seconds"
    else:
        hours = seconds // 3600
        remaining = seconds % 3600
        minutes = remaining // 60
        seconds = remaining % 60
        return f"{int(hours)} hours, {int(minutes)} minutes, {int(seconds)} seconds"


def truncate_text(text: str, max_length: int = 5000, keep_start: int = 3000, keep_end: int = 2000) -> str:
    """Truncate text to a maximum length while preserving beginning and end
    
    Args:
        text: Text to truncate
        max_length: Maximum length
        keep_start: How much of the beginning to keep
        keep_end: How much of the end to keep
        
    Returns:
        str: Truncated text
    """
    if not text:
        return ""
        
    if len(text) <= max_length:
        return text
        
    # If keep_start + keep_end > max_length, adjust
    if keep_start + keep_end > max_length:
        ratio = max_length / (keep_start + keep_end)
        keep_start = int(keep_start * ratio)
        keep_end = int(keep_end * ratio)
    
    return f"{text[:keep_start]}\n\n[...content truncated...]\n\n{text[-keep_end:]}"
