# Video Creator App - Simple Guide

## First Time Setup (Do this once)

### Step 1: Install Python
- Open **Microsoft Store**
- Search **"Python 3.11"** or **"Python 3.12"**
- Click **Install**

---

### Step 2: Run Setup
- Double-click **`First Time Setup.bat`**
- Wait for it to finish (follow any on-screen instructions)

---

### Step 3: Set Up YouTube Login (One-time, ~5 minutes)

This connects the app to YOUR YouTube channel so videos upload to YOUR channel.

#### 3A. Create a Google Cloud Project

1. Go to: https://console.cloud.google.com/apis/credentials
2. At the top, click the project dropdown and click **"NEW PROJECT"**
3. Name it anything (e.g., "Video Creator") and click **"CREATE"**
4. Wait 30 seconds for it to create, then select your new project

#### 3B. Enable YouTube Data API

1. On the left menu, click **"APIs & Services"** → **"Library"**
2. Search for **"YouTube Data API v3"**
3. Click on it and press **"ENABLE"**

#### 3C. Create OAuth Credentials

1. Go to: **"APIs & Services"** → **"Credentials"** (left menu)
2. Click **"+ CREATE CREDENTIALS"** at the top
3. Select **"OAuth 2.0 Client ID"**
4. If asked to configure consent screen:
   - Choose **"External"** and click **"Create"**
   - Fill in: App name (anything), User type = External
   - Scroll down, click **"Save and Continue"** through all steps
   - Go back to Credentials when done
5. Select **"Web application"** as the application type
6. Fill in:
   - **Name**: `Video Creator App` (or anything)
   - **Authorized redirect URIs**: Click **"ADD URI"** and paste: `http://localhost:8501`
7. Click **"Create"**
8. **Copy the Client ID** (you'll need it!)
9. Click **"Download JSON"** to save your credentials (optional backup)

#### 3D. Add Credentials to the App

1. In the app folder, create a folder named `.streamlit` (the dot is important)
2. Inside `.streamlit`, create a file named `secrets.toml`
3. Paste this inside (replace with YOUR keys from step 3C):

```toml
GOOGLE_CLIENT_ID = "paste-your-client-id-here.apps.googleusercontent.com"
GOOGLE_CLIENT_SECRET = "paste-your-client-secret-here"
```

4. Save the file

**You're done!** Now when you click "Sign in to YouTube" in the app, it will open a Google sign-in page for YOUR account.

---

## Every Day - Making a Video

### Step 1: Start the App
- Double-click **`Start App.bat`**
- Wait for it to open in your browser

### Step 2: Click the **"Simple"** tab (it's already selected)

### Step 3: Fill in 4 things:

| # | What | How |
|---|------|-----|
| 1 | **YouTube Account** | Click "Sign in" (first time only) |
| 2 | **Music Folder** | Paste your folder path like `C:\Users\YourName\Music` |
| 3 | **Text on Video** | Type what you want (e.g., "FOCUS", "RELAX") |
| 4 | **Video Length** | Choose 8 or 9 hours |

### Step 4: Click **"GENERATE VIDEO"**

That's it! It will take 30-60 minutes. You can close the browser and come back later.

---

## FAQ

**Q: Where do my MP3 files go?**
A: Just put them in a folder on your computer. Point the app to that folder.

**Q: What if I close the browser?**
A: The video keeps generating! Open the app again to check progress.

**Q: How do I see my video on YouTube?**
A: It uploads automatically when done. Check your YouTube Studio.

**Q: Can I change the video style?**
A: Sure! Click the "Visuals" tab for more options.

---

## Need Help?

If something goes wrong:
1. Make sure you ran **First Time Setup.bat**
2. Check that FFmpeg is installed (the setup should do this)
3. Make sure you created the `.streamlit\secrets.toml` file for YouTube
