# Render Deployment Setup Guide

## Quick Fix for "Invalid HTTP_HOST" Error

If you're seeing this error:
```
Invalid HTTP_HOST header: 'articlei-ai-blog-app-4.onrender.com'
```

**The fix is already applied!** Your code now includes the Render domain in `ALLOWED_HOSTS`.

Just commit and push:
```bash
git add -A
git commit -m "Fix ALLOWED_HOSTS for Render deployment"
git push origin main
```

Render will automatically redeploy, and your app will work! 🎉

---

## Complete Render Setup

### Step 1: Create Web Service on Render

1. Go to https://dashboard.render.com/
2. Click **"New +"** → **"Web Service"**
3. Connect your GitHub repository
4. Configure:
   - **Name**: `articlei-ai-blog-app` (or your choice)
   - **Environment**: `Python 3`
   - **Build Command**: 
     ```bash
     pip install -r requirements.txt && python manage.py migrate
     ```
   - **Start Command**: 
     ```bash
     gunicorn ai_blog_app.wsgi:application
     ```

### Step 2: Add Environment Variables

Click **"Advanced"** → **"Add Environment Variable"** and add these:

#### Required Variables

```bash
# Python version
PYTHON_VERSION=3.10.12

# Django secret key (generate a new one!)
SECRET_KEY=your-generated-secret-key-here

# Debug mode (False for production)
DEBUG=False

# Allowed hosts (your Render domain)
ALLOWED_HOSTS=articlei-ai-blog-app-4.onrender.com

# Disable static file collection (for now)
DISABLE_COLLECTSTATIC=1
```

#### ASR Configuration (Recommended for Free Tier)

```bash
# Use tiny model for 512MB RAM limit
WHISPER_MODEL_SIZE=tiny

# Limit video duration to 5 minutes
MAX_VIDEO_DURATION=300

# Timeout after 2 minutes
ASR_TIMEOUT=120

# Enable ASR
ENABLE_ASR=True

# Auto cleanup temp files
AUTO_CLEANUP_AUDIO=True

# Use CPU (no GPU on free tier)
WHISPER_DEVICE=cpu
```

### Step 3: Generate a Secure SECRET_KEY

**Important:** Never use the default SECRET_KEY in production!

Generate a new one:
```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Copy the output and use it as your `SECRET_KEY` environment variable.

### Step 4: Update ALLOWED_HOSTS (If Needed)

If your Render domain is different from `articlei-ai-blog-app-4.onrender.com`:

1. Find your actual domain in the Render dashboard
2. Update the environment variable:
   ```bash
   ALLOWED_HOSTS=your-actual-domain.onrender.com
   ```

Or update `ai_blog_app/settings.py`:
```python
ALLOWED_HOSTS = config(
    'ALLOWED_HOSTS',
    default='localhost,127.0.0.1,your-actual-domain.onrender.com',
    cast=Csv()
)
```

### Step 5: Deploy

Click **"Create Web Service"** and wait for deployment (5-10 minutes).

---

## Environment Variables Reference

### Django Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `SECRET_KEY` | (insecure default) | Django secret key - **MUST change in production** |
| `DEBUG` | `True` | Debug mode - set to `False` in production |
| `ALLOWED_HOSTS` | `localhost,127.0.0.1` | Comma-separated list of allowed domains |

### ASR Settings

| Variable | Default | Free Tier | Paid Tier |
|----------|---------|-----------|-----------|
| `WHISPER_MODEL_SIZE` | `base` | `tiny` | `base` or `small` |
| `MAX_VIDEO_DURATION` | `3600` (60 min) | `300` (5 min) | `1800` (30 min) |
| `ASR_TIMEOUT` | `300` (5 min) | `120` (2 min) | `300` (5 min) |
| `ENABLE_ASR` | `True` | `True` | `True` |
| `AUTO_CLEANUP_AUDIO` | `True` | `True` | `True` |
| `WHISPER_DEVICE` | `cpu` | `cpu` | `cpu` |

### Model Size vs RAM Requirements

| Model | RAM Required | Render Tier | Speed | Accuracy |
|-------|--------------|-------------|-------|----------|
| `tiny` | ~400MB | ✅ Free (512MB) | Fastest | Good |
| `base` | ~600MB | ❌ Free / ✅ Starter | Fast | Better |
| `small` | ~1.2GB | ❌ Free / ✅ Standard | Medium | Great |
| `medium` | ~2.5GB | ❌ Free / ✅ Pro | Slow | Excellent |

---

## Troubleshooting

### Error: "Invalid HTTP_HOST header"

**Solution:** Update `ALLOWED_HOSTS` environment variable with your Render domain.

```bash
ALLOWED_HOSTS=your-app.onrender.com
```

### Error: "Out of memory"

**Solution:** Use smaller model for free tier.

```bash
WHISPER_MODEL_SIZE=tiny
MAX_VIDEO_DURATION=300
```

### Error: "Transcription timeout"

**Solution:** Reduce timeout or video duration limit.

```bash
ASR_TIMEOUT=120
MAX_VIDEO_DURATION=300
```

### Error: "Application failed to start"

**Check logs:**
1. Go to Render dashboard
2. Click on your service
3. Click "Logs" tab
4. Look for error messages

**Common causes:**
- Missing environment variables
- Database migration failed
- Dependency installation failed

### Error: "Static files not loading"

**Solution:** Add WhiteNoise for static file serving.

1. Install WhiteNoise:
   ```bash
   pip install whitenoise
   ```

2. Update `requirements.txt`:
   ```
   whitenoise==6.6.0
   ```

3. Update `settings.py`:
   ```python
   MIDDLEWARE = [
       'django.middleware.security.SecurityMiddleware',
       'whitenoise.middleware.WhiteNoiseMiddleware',  # Add this
       # ... other middleware
   ]
   ```

---

## Monitoring Your App

### View Logs

```bash
# In Render dashboard
Services → Your Service → Logs
```

### Check Status

```bash
# In Render dashboard
Services → Your Service → Events
```

### Test Your App

1. Visit your Render URL: `https://your-app.onrender.com`
2. Sign up for an account
3. Try generating a blog from a short YouTube video (1-2 minutes)
4. Check logs for any errors

---

## Upgrading from Free Tier

If you need better performance:

### Starter Tier ($7/month)
- 512MB RAM (same as free)
- No sleep after inactivity
- Use `tiny` model

### Standard Tier ($25/month)
- 2GB RAM
- Use `base` model
- Longer videos (up to 30 minutes)

Update environment variables after upgrading:
```bash
WHISPER_MODEL_SIZE=base
MAX_VIDEO_DURATION=1800
ASR_TIMEOUT=300
```

---

## Security Checklist

Before going to production:

- [ ] Changed `SECRET_KEY` to a secure random value
- [ ] Set `DEBUG=False`
- [ ] Updated `ALLOWED_HOSTS` with your domain
- [ ] Reviewed all environment variables
- [ ] Tested the application thoroughly
- [ ] Set up error monitoring (optional: Sentry)
- [ ] Configured database backups (if using PostgreSQL)

---

## Next Steps

1. **Test your deployment** - Try generating a blog post
2. **Monitor logs** - Watch for errors or warnings
3. **Optimize settings** - Adjust based on usage
4. **Add monitoring** - Consider Sentry for error tracking
5. **Set up CI/CD** - Automate deployments with GitHub Actions

---

## Support

- **Render Docs**: https://render.com/docs
- **Django Docs**: https://docs.djangoproject.com/
- **faster-whisper**: https://github.com/guillaumekln/faster-whisper

For issues specific to this project, check:
- `README.md` - Full documentation
- `DEPLOYMENT.md` - Detailed deployment guide
- `TROUBLESHOOTING.md` - Common issues and solutions

---

**Last Updated**: November 2024
