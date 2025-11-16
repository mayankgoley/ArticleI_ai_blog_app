# Quick Start Guide

## Running Locally

### 1. Install Dependencies

```bash
# Install system dependencies (macOS)
brew install pkg-config ffmpeg

# Install Python dependencies
pip install -r requirements.txt
```

### 2. Run Database Migrations

```bash
python manage.py migrate
```

### 3. Create Superuser (Optional)

```bash
python manage.py createsuperuser
```

### 4. Start the Development Server

```bash
python manage.py runserver
```

### 5. Access the Application

Open your browser and go to:
```
http://127.0.0.1:8000
```

## What Just Happened?

✅ **Migrated to faster-whisper** - No more PyTorch/CUDA dependencies
✅ **Installed all dependencies** - Including ONNX Runtime for CPU inference
✅ **Server is running** - Application is accessible at localhost:8000

## Testing the Application

1. **Sign up** for a new account or **log in**
2. **Paste a YouTube URL** (try a short video first, 1-2 minutes)
3. **Click "Generate Article"**
4. **Wait** for processing:
   - With subtitles: ~5-10 seconds
   - Without subtitles (ASR): ~2-5 minutes for short videos

## Common Commands

```bash
# Start server
python manage.py runserver

# Run migrations
python manage.py migrate

# Create migrations
python manage.py makemigrations

# Create superuser
python manage.py createsuperuser

# Run tests
python manage.py test

# Check for issues
python manage.py check

# Open Django shell
python manage.py shell
```

## Troubleshooting

### "Module not found" errors
```bash
pip install -r requirements.txt
```

### "ffmpeg not found"
```bash
# macOS
brew install ffmpeg

# Ubuntu/Debian
sudo apt install ffmpeg
```

### "pkg-config not found"
```bash
# macOS
brew install pkg-config

# Ubuntu/Debian
sudo apt install pkg-config
```

### Database errors
```bash
python manage.py migrate
```

### Port already in use
```bash
# Use a different port
python manage.py runserver 8080
```

## Next Steps

### For Local Development
- Use `base` or `small` Whisper model for better accuracy
- Increase `MAX_VIDEO_DURATION` if needed
- Enable DEBUG mode in settings.py

### For Render Deployment
1. Push code to GitHub
2. Follow instructions in `DEPLOYMENT.md`
3. Use `tiny` model for free tier (512MB RAM limit)

## Configuration

Edit `ai_blog_app/settings.py` to customize:

```python
# ASR Settings
WHISPER_MODEL_SIZE = 'base'  # tiny, base, small, medium, large
MAX_VIDEO_DURATION = 3600    # 60 minutes
ASR_TIMEOUT = 300            # 5 minutes
ENABLE_ASR = True
AUTO_CLEANUP_AUDIO = True
```

## Resources

- **Full Documentation**: See `README.md`
- **Deployment Guide**: See `DEPLOYMENT.md`
- **Migration Info**: See `MIGRATION_TO_FASTER_WHISPER.md`

---

**Need Help?** Check the troubleshooting section in `README.md` or create an issue on GitHub.
