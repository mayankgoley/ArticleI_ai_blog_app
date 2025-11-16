# YouTube Cookies for Bot Detection Bypass

## Why Cookies Are Needed

YouTube may block server requests from cloud platforms like Render, showing errors like:
- `HTTP Error 429: Too Many Requests`
- `Sign in to confirm you're not a bot`

Using cookies from a logged-in YouTube session helps bypass these restrictions.

## How to Add Cookies (Optional but Recommended for Production)

### Step 1: Install Browser Extension

Install one of these extensions to export cookies:

**Chrome/Edge:**
- [Get cookies.txt LOCALLY](https://chrome.google.com/webstore/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc)

**Firefox:**
- [cookies.txt](https://addons.mozilla.org/en-US/firefox/addon/cookies-txt/)

### Step 2: Export Cookies

1. Open YouTube in your browser
2. Make sure you're logged in to your YouTube/Google account
3. Click the extension icon
4. Click "Export" or "Get cookies.txt"
5. Save the file as `cookies.txt`

### Step 3: Add to Project

Place the `cookies.txt` file in this directory:
```
cookies/cookies.txt
```

**Important:** The file must be named exactly `cookies.txt`

### Step 4: Deploy

For local development:
- Just place the file and restart the server

For Render deployment:
- Add the cookies.txt file to your repository
- Commit and push:
  ```bash
  git add cookies/cookies.txt
  git commit -m "Add YouTube cookies for bot detection bypass"
  git push
  ```

## Security Notes

⚠️ **Important Security Considerations:**

1. **Never commit cookies to public repositories**
   - Cookies contain authentication tokens
   - Anyone with your cookies can access your YouTube account
   - Use `.gitignore` to exclude `cookies.txt` from version control

2. **For production deployment:**
   - Use environment variables or secrets management
   - Rotate cookies periodically (every 30 days)
   - Use a dedicated YouTube account (not your personal account)

3. **Alternative: Use Render Environment Variables**
   - Store cookies as base64-encoded environment variable
   - Decode at runtime
   - More secure than committing to repository

## How It Works

When `cookies.txt` exists in this directory:
- yt-dlp automatically uses it for YouTube requests
- YouTube sees requests as coming from a logged-in user
- Rate limiting and bot detection are bypassed
- Works with private and age-restricted videos

When `cookies.txt` doesn't exist:
- App still works but may hit rate limits
- Public videos with subtitles work fine
- ASR transcription may fail on some videos

## Troubleshooting

### "Still getting 429 errors"
- Cookies may be expired (regenerate them)
- Try logging out and back in to YouTube
- Export fresh cookies

### "Cookies not working"
- Check file name is exactly `cookies.txt`
- Check file is in `cookies/` directory
- Check file format (should be Netscape format)
- Restart your application

### "Don't want to use cookies"
- App works without cookies for most public videos
- Consider using shorter videos
- Use videos with existing subtitles (faster, no ASR needed)

## Alternative Solutions

If you don't want to use cookies:

1. **Use videos with subtitles** - Much faster, no YouTube API calls needed
2. **Limit video length** - Shorter videos are less likely to trigger rate limits
3. **Use Invidious API** - Alternative YouTube frontend (requires code changes)
4. **Upgrade Render tier** - Dedicated IP may have better rate limits

## File Structure

```
cookies/
├── README.md          # This file
├── cookies.txt        # Your YouTube cookies (add this)
└── .gitkeep          # Keeps directory in git
```

## Example .gitignore Entry

Add this to your `.gitignore` to prevent accidentally committing cookies:

```gitignore
# YouTube cookies (contains sensitive auth tokens)
cookies/cookies.txt
```

---

**Note:** Cookies are optional. The app will work without them for most public videos, but may encounter rate limiting on Render's shared infrastructure.
