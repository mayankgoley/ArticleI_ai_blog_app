# Deployment Guide

This guide covers deploying the AI Blog Generator to various cloud platforms.

## Table of Contents
- [Render Deployment (Recommended)](#render-deployment-recommended)
- [Heroku Deployment](#heroku-deployment)
- [Railway Deployment](#railway-deployment)
- [DigitalOcean App Platform](#digitalocean-app-platform)
- [Troubleshooting](#troubleshooting)

---

## Render Deployment (Recommended)

Render is the recommended platform because:
- ✅ Free tier available
- ✅ Automatic HTTPS
- ✅ Works perfectly with `faster-whisper`
- ✅ No credit card required for free tier
- ✅ Includes ffmpeg in build environment

### Prerequisites
- GitHub account with your code pushed
- Render account (sign up at https://render.com)

### Step-by-Step Instructions

#### 1. Prepare Your Repository

Ensure these files are in your repository:
- `requirements.txt` (with faster-whisper, not openai-whisper)
- `runtime.txt` (with `python-3.10.12`)
- `Procfile` (with `web: gunicorn ai_blog_app.wsgi:application`)

#### 2. Push to GitHub

```bash
git add -A
git commit -m "Prepare for Render deployment"
git push origin main
```

#### 3. Create Web Service on Render

1. Go to https://dashboard.render.com/
2. Click **"New +"** → **"Web Service"**
3. Connect your GitHub repository
4. Select your repository from the list

#### 4. Configure Service Settings

**Basic Settings:**
- **Name**: `ai-blog-generator` (or your choice)
- **Environment**: `Python 3`
- **Region**: Choose closest to your users
- **Branch**: `main` (or your default branch)

**Build & Deploy:**
- **Build Command**: 
  ```bash
  pip install -r requirements.txt && python manage.py migrate
  ```
- **Start Command**: 
  ```bash
  gunicorn ai_blog_app.wsgi:application
  ```

**Instance Type:**
- Select **"Free"** for testing
- Upgrade to paid tier for production use

#### 5. Add Environment Variables

Click **"Advanced"** → **"Add Environment Variable"** and add:

```
PYTHON_VERSION=3.10.12
SECRET_KEY=your-random-secret-key-here
DEBUG=False
ALLOWED_HOSTS=your-app-name.onrender.com
DISABLE_COLLECTSTATIC=1
WHISPER_MODEL_SIZE=tiny
MAX_VIDEO_DURATION=600
ASR_TIMEOUT=180
```

**Generate a secure SECRET_KEY:**
```python
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

#### 6. Deploy

1. Click **"Create Web Service"**
2. Render will automatically:
   - Clone your repository
   - Install dependencies
   - Run migrations
   - Start your application
3. Wait for deployment to complete (5-10 minutes first time)

#### 7. Access Your Application

Once deployed, your app will be available at:
```
https://your-app-name.onrender.com
```

### Render Free Tier Limitations

⚠️ **Important Limitations:**
- **RAM**: 512MB (use `tiny` model only)
- **Sleep**: App sleeps after 15 minutes of inactivity
- **Cold Start**: 30-60 seconds to wake up
- **Build Time**: 10 minutes max
- **Bandwidth**: 100GB/month

**Recommended Settings for Free Tier:**
```python
WHISPER_MODEL_SIZE = 'tiny'  # Only tiny fits in 512MB
MAX_VIDEO_DURATION = 300     # 5 minutes max
ASR_TIMEOUT = 120            # 2 minutes timeout
```

### Upgrading to Paid Tier

For production use, upgrade to:
- **Starter**: $7/month, 512MB RAM
- **Standard**: $25/month, 2GB RAM (can use 'base' model)
- **Pro**: $85/month, 4GB RAM (can use 'small' model)

---

## Heroku Deployment

### Prerequisites
- Heroku account
- Heroku CLI installed

### Steps

#### 1. Install Heroku CLI
```bash
# macOS
brew tap heroku/brew && brew install heroku

# Ubuntu
curl https://cli-assets.heroku.com/install.sh | sh
```

#### 2. Login to Heroku
```bash
heroku login
```

#### 3. Create Heroku App
```bash
heroku create your-app-name
```

#### 4. Add FFmpeg Buildpack
```bash
heroku buildpacks:add --index 1 https://github.com/jonathanong/heroku-buildpack-ffmpeg-latest.git
heroku buildpacks:add --index 2 heroku/python
```

#### 5. Set Environment Variables
```bash
heroku config:set SECRET_KEY="your-secret-key"
heroku config:set DEBUG=False
heroku config:set WHISPER_MODEL_SIZE=tiny
heroku config:set MAX_VIDEO_DURATION=600
heroku config:set ASR_TIMEOUT=180
```

#### 6. Deploy
```bash
git push heroku main
```

#### 7. Run Migrations
```bash
heroku run python manage.py migrate
```

#### 8. Create Superuser (Optional)
```bash
heroku run python manage.py createsuperuser
```

### Heroku Pricing
- **Free Tier**: Deprecated (no longer available)
- **Eco**: $5/month, 512MB RAM
- **Basic**: $7/month, 512MB RAM
- **Standard**: $25/month, 2GB RAM

---

## Railway Deployment

Railway is similar to Render with good free tier.

### Steps

#### 1. Install Railway CLI
```bash
npm install -g @railway/cli
```

#### 2. Login
```bash
railway login
```

#### 3. Initialize Project
```bash
railway init
```

#### 4. Add Environment Variables
```bash
railway variables set SECRET_KEY="your-secret-key"
railway variables set DEBUG=False
railway variables set WHISPER_MODEL_SIZE=tiny
```

#### 5. Deploy
```bash
railway up
```

### Railway Pricing
- **Free Trial**: $5 credit
- **Developer**: $5/month
- **Team**: $20/month

---

## DigitalOcean App Platform

### Steps

#### 1. Create App
1. Go to DigitalOcean App Platform
2. Click "Create App"
3. Connect GitHub repository

#### 2. Configure App Spec

Create `app.yaml`:
```yaml
name: ai-blog-generator
services:
- name: web
  github:
    repo: your-username/your-repo
    branch: main
  build_command: pip install -r requirements.txt && python manage.py migrate
  run_command: gunicorn ai_blog_app.wsgi:application
  envs:
  - key: SECRET_KEY
    value: your-secret-key
  - key: DEBUG
    value: "False"
  - key: WHISPER_MODEL_SIZE
    value: tiny
  instance_count: 1
  instance_size_slug: basic-xxs
```

#### 3. Deploy
Click "Deploy" in the DigitalOcean dashboard.

### DigitalOcean Pricing
- **Basic**: $5/month, 512MB RAM
- **Professional**: $12/month, 1GB RAM

---

## Troubleshooting

### Common Issues

#### 1. "openai-whisper failed to build"
**Solution**: Make sure you're using `faster-whisper`, not `openai-whisper`

Check `requirements.txt`:
```
✅ faster-whisper==0.10.0
❌ openai-whisper==20231117
```

#### 2. "torch/torchaudio installation failed"
**Solution**: Remove PyTorch dependencies

`requirements.txt` should NOT have:
```
❌ torch>=2.2.0
❌ torchaudio>=2.2.0
```

#### 3. "Out of memory during transcription"
**Solutions**:
- Use smaller model: `WHISPER_MODEL_SIZE=tiny`
- Reduce video duration: `MAX_VIDEO_DURATION=300`
- Upgrade to larger instance

#### 4. "Application error" or "H10 error" (Heroku)
**Solutions**:
- Check logs: `heroku logs --tail`
- Verify Procfile exists and is correct
- Ensure gunicorn is in requirements.txt
- Check ALLOWED_HOSTS includes your domain

#### 5. "ffmpeg not found"
**Solutions**:
- **Render**: ffmpeg is included by default
- **Heroku**: Add ffmpeg buildpack (see above)
- **Railway**: Add nixpacks config
- **DigitalOcean**: Add to app spec

#### 6. "Static files not loading"
**Solutions**:
- Set `DISABLE_COLLECTSTATIC=1` for development
- For production, configure WhiteNoise:
  ```bash
  pip install whitenoise
  ```
  Add to `settings.py`:
  ```python
  MIDDLEWARE = [
      'django.middleware.security.SecurityMiddleware',
      'whitenoise.middleware.WhiteNoiseMiddleware',  # Add this
      # ... other middleware
  ]
  ```

#### 7. "Database is locked" (SQLite)
**Solution**: For production, use PostgreSQL:
```bash
# Render provides free PostgreSQL
# Add to environment variables:
DATABASE_URL=postgresql://user:pass@host:5432/dbname
```

Update `settings.py`:
```python
import dj_database_url

DATABASES = {
    'default': dj_database_url.config(
        default='sqlite:///db.sqlite3',
        conn_max_age=600
    )
}
```

### Checking Deployment Status

**Render:**
```bash
# View logs in dashboard or CLI
render logs -s your-service-name
```

**Heroku:**
```bash
heroku logs --tail
heroku ps
```

**Railway:**
```bash
railway logs
railway status
```

### Performance Optimization for Production

1. **Use PostgreSQL instead of SQLite**
2. **Enable caching** (Redis/Memcached)
3. **Use CDN for static files**
4. **Implement rate limiting**
5. **Add monitoring** (Sentry, New Relic)
6. **Use async workers** (Celery) for long tasks

---

## Post-Deployment Checklist

- [ ] Application is accessible via HTTPS
- [ ] Environment variables are set correctly
- [ ] Database migrations have run
- [ ] Static files are loading
- [ ] Can create user accounts
- [ ] Can generate blog from YouTube URL
- [ ] Transcription works (test with short video)
- [ ] Error pages display correctly
- [ ] Logs are accessible
- [ ] Monitoring is set up (optional)

---

## Support

If you encounter issues:
1. Check the logs first
2. Review this troubleshooting guide
3. Check the main README.md
4. Create an issue on GitHub with:
   - Platform (Render, Heroku, etc.)
   - Error messages
   - Relevant logs
   - Steps to reproduce

---

**Last Updated**: November 2024
