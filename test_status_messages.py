#!/usr/bin/env python3
"""
Test script to verify status messages are properly logged during transcription.
This script checks that the logging statements are in place.
"""

import os
import sys

# Add the project directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_status_logging():
    """Test that status messages are logged in views.py"""
    views_path = os.path.join(os.path.dirname(__file__), 'blog_generator', 'views.py')
    
    with open(views_path, 'r') as f:
        content = f.read()
    
    # Check for status logging statements
    status_checks = [
        'STATUS: Downloading audio for transcription',
        'STATUS: Downloading audio from video',
        'STATUS: Transcribing audio (this may take a few minutes)',
    ]
    
    print("Checking for status logging statements in views.py...")
    all_found = True
    
    for status_msg in status_checks:
        if status_msg in content:
            print(f"✓ Found: {status_msg}")
        else:
            print(f"✗ Missing: {status_msg}")
            all_found = False
    
    return all_found

def test_template_status_ui():
    """Test that status UI elements are in the template"""
    template_path = os.path.join(os.path.dirname(__file__), 'templates', 'index.html')
    
    with open(template_path, 'r') as f:
        content = f.read()
    
    # Check for UI elements
    ui_checks = [
        'id="statusMessages"',
        'id="statusText"',
        'id="statusDetail"',
        'id="progressBar"',
        'id="progressText"',
        'showStatus',
        'hideStatus',
        'updateProgress',
        'Downloading audio for transcription',
        'Transcribing audio (this may take a few minutes)',
    ]
    
    print("\nChecking for status UI elements in template...")
    all_found = True
    
    for ui_element in ui_checks:
        if ui_element in content:
            print(f"✓ Found: {ui_element}")
        else:
            print(f"✗ Missing: {ui_element}")
            all_found = False
    
    return all_found

def test_error_handling():
    """Test that error messages are properly handled"""
    template_path = os.path.join(os.path.dirname(__file__), 'templates', 'index.html')
    
    with open(template_path, 'r') as f:
        content = f.read()
    
    # Check for error handling
    error_checks = [
        'showError',
        'error_type',
        'duration_limit',
        'network_error',
        'invalid_url',
        'timeout',
        'audio_extraction',
        'model_load',
    ]
    
    print("\nChecking for error handling in template...")
    all_found = True
    
    for error_check in error_checks:
        if error_check in content:
            print(f"✓ Found: {error_check}")
        else:
            print(f"✗ Missing: {error_check}")
            all_found = False
    
    return all_found

if __name__ == '__main__':
    print("=" * 60)
    print("Testing Status Messages Implementation")
    print("=" * 60)
    
    test1 = test_status_logging()
    test2 = test_template_status_ui()
    test3 = test_error_handling()
    
    print("\n" + "=" * 60)
    if test1 and test2 and test3:
        print("✓ All tests passed!")
        print("=" * 60)
        sys.exit(0)
    else:
        print("✗ Some tests failed")
        print("=" * 60)
        sys.exit(1)
