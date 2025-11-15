#!/usr/bin/env python3
"""
Setup script for AI Blog Generator
"""

import subprocess
import sys
import os

def run_command(command, description):
    """Run a command and handle errors"""
    print(f"\n{description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✓ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ {description} failed: {e}")
        print(f"Error output: {e.stderr}")
        return False

def main():
    print("🚀 Setting up AI Blog Generator...")
    
    # Install dependencies
    if not run_command("pip install -r requirements.txt", "Installing Python dependencies"):
        print("Failed to install dependencies. Please install manually:")
        print("pip install Django==5.2.7 yt-dlp==2023.12.30")
        return
    
    # Make migrations
    if not run_command("python manage.py makemigrations", "Creating database migrations"):
        return
    
    # Run migrations
    if not run_command("python manage.py migrate", "Applying database migrations"):
        return
    
    # Create superuser (optional)
    print("\n📝 Would you like to create a superuser account? (y/n): ", end="")
    create_superuser = input().lower().strip()
    
    if create_superuser in ['y', 'yes']:
        print("Creating superuser account...")
        os.system("python manage.py createsuperuser")
    
    print("\n🎉 Setup completed successfully!")
    print("\nTo start the development server, run:")
    print("python manage.py runserver")
    print("\nThen visit: http://127.0.0.1:8000")

if __name__ == "__main__":
    main()