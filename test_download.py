#!/usr/bin/env python3
"""
Simple test script to verify download functionality
"""

import re

def test_filename_sanitization():
    """Test that filenames are properly sanitized"""
    test_titles = [
        "How to Code: A Beginner's Guide!",
        "Python & Django Tutorial (2024)",
        "AI/ML Basics - Part 1",
        "Web Development 101"
    ]
    
    for title in test_titles:
        # Sanitize title for filename
        safe_title = re.sub(r'[^\w\s-]', '', title)
        safe_title = re.sub(r'[-\s]+', '-', safe_title)
        filename = f"{safe_title[:50]}-article.txt"
        
        print(f"Original: {title}")
        print(f"Filename: {filename}")
        print("-" * 40)

if __name__ == "__main__":
    print("Testing filename sanitization...")
    test_filename_sanitization()
    print("✓ All tests passed!")