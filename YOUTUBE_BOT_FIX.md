# Fixing YouTube Bot Detection on Render

## The Problem

When deployed on Render, you may see these errors:
```
ERROR: [youtube] Sign in to confirm you're not a bot
HTTP Error 429: Too Many Requests
Please provide a valid YouTube URL. The video may be private or unavailable.
```

**Root Cause:** YouTube blocks requests from Render's shared server IPs, treating them as bots.

## ✅ Solution Implemented

I've updated the code with multiple fixes to bypass YouTube's bot detection:

### 1. Enhanced yt-dlp Configuration

The audio extractor now uses:
- **Android player client** - Less likely to be blocked
- **Cookie support** - Uses YouTube login cookies if available
- **FFmpeg location** - Explicitly set for Render
- **Skip problematic formats** - Avoids HLS/DASH that trigger blocks

### 2. Automatic Cookie Detection

The app automatically checks for `cookies/cookies.txt` and uses it if present.

## 🚀 Quick Fix (Recommended)

### Option A: Add YouTube Cookies (Most Reliable)

**Step 1:** Install browser extension
- Chrome: [Get cookies.txt LOCALLY](https://chrome.google.com/webstore/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc)
- Firefox: [cookies.txt](https://addons.mozilla.org/en-US/firefox/addon/cookies-txt/)

**Step 2:** Export cookies
1. Open YouTube in browser (logged in)
2. Click extension icon
3. Export cookies
4. Save as `cookies.txt`

**Step 3:** Add to project
```bash
# Place file in cookies directory
cp ~/Downloads/cookies.txt cookies/cookies.txt

# Commit and push
git add cookies/cookies.txt .gitignore
git commit -m "Add YouTube cookies for bot detection bypass"
git push
```

**Step 4:** Render will auto-deploy with cookies

### Option B: Use Without Cookies (May Work)

The code improvements may be enough without cookies:
- Android player client helps bypass detection
- Works for many public videos
- May still hit rate limits occasionally

Just push the current changes:
```bash
git add -A
git commit -m "Add YouTube bot detection bypass"
git push
```

## 🔒 Security Best Practices

### For Public Repositories

**DO NOT commit cookies.txt to public repos!**

Instead, use Render environment variables:

1. **Encode cookies:**
   ```bash
   base64 cookies/cookies.txt > cookies_base64.txt
   ```

2. **Add to Render:**
   - Dashboard → Environment
   - Add variable: `YOUTUBE_COOKIES_BASE64`
   - Paste the base64 content

3. **Update code to decode:**
   ```python
   import os
   import base64
   
   cookies_b64 = os.getenv('YOUTUBE_COOKIES_BASE64')
   if cookies_b64:
       cookies_content = base64.b64decode(cookies_b64)
       with open('cookies/cookies.txt', 'wb') as f:
           f.write(cookies_content)
   ```

### For Private Repositories

You can safely commit `cookies.txt` if your repo is private, but:
- Use a dedicated YouTube account (not personal)
- Rotate cookies every 30 days
- Revoke access if cookies are leaked

## 📊 What to Expect

### With Cookies:
- ✅ Works with all public videos
- ✅ Works with private videos (if account has access)
- ✅ Works with age-restricted videos
- ✅ No rate limiting
- ✅ Faster processing

### Without Cookies:
- ✅ Works with most public videos
- ⚠️ May hit rate limits occasionally
- ❌ Won't work with private videos
- ❌ Won't work with age-restricted videos
- ⚠️ Slower due to retries

## 🧪 Testing

After deploying, test with these URLs:

**Public video (should work):**
```
https://www.youtube.com/watch?v=dQw4w9WgXcQ
```

**Short video (best for testing):**
```
https://www.youtube.com/watch?v=2IK3DFHRRFw
```

## 🐛 Troubleshooting

### Still getting 429 errors?

1. **Check cookies are being used:**
   - Look for `cookies/cookies.txt` in your deployment
   - Check Render logs for "Using cookies" message

2. **Regenerate cookies:**
   - Cookies expire after ~30 days
   - Export fresh cookies from browser
   - Redeploy

3. **Try different videos:**
   - Some videos may still be blocked
   - Try videos with existing subtitles (faster anyway)

### Cookies not working?

1. **Check file location:**
   ```
   cookies/cookies.txt  ✅ Correct
   cookies.txt          ❌ Wrong
   cookie.txt           ❌ Wrong
   ```

2. **Check file format:**
   - Must be Netscape format
   - Should start with `# Netscape HTTP Cookie File`
   - Use the browser extension (don't create manually)

3. **Check file permissions:**
   ```bash
   chmod 644 cookies/cookies.txt
   ```

### Alternative: Use Invidious API

If cookies don't work, you can use Invidious (YouTube alternative frontend):

```python
# Example (requires code changes)
import requests

def get_video_via_invidious(video_id):
    url = f"https://yt.artemislena.eu/api/v1/videos/{video_id}"
    response = requests.get(url)
    data = response.json()
    audio_url = data['adaptiveFormats'][0]['url']
    # Download from audio_url
```

## 📝 Summary of Changes

### Files Modified:
- ✅ `blog_generator/transcription/audio_extractor.py` - Added cookie support and Android client
- ✅ `.gitignore` - Exclude cookies.txt from git
- ✅ `apt.txt` - Install ffmpeg on Render

### Files Created:
- ✅ `cookies/README.md` - Cookie setup instructions
- ✅ `cookies/.gitkeep` - Keep directory in git
- ✅ `YOUTUBE_BOT_FIX.md` - This file

## 🎯 Next Steps

1. **Push current changes** (bot detection improvements)
   ```bash
   git add -A
   git commit -m "Add YouTube bot detection bypass with cookie support"
   git push
   ```

2. **Test without cookies first** - May work for your use case

3. **Add cookies if needed** - Follow Option A above

4. **Monitor Render logs** - Check for any remaining errors

---

**Status:** ✅ Code updated with bot detection bypass
**Cookies:** Optional but recommended for production
**Expected:** Should work for most videos without cookies, all videos with cookies
