# Video Creator Agent (ffmpeg + Drive + YouTube)

Automates an 8-9 hour looped visual + audio video:
- Downloads MP3s from a Google Drive folder.
- Repeats the playlist until it reaches the target length.
- Generates a static image with Whisk.
- Generates a 5-second loopable video with Grok.
- Loops that video until the audio finishes.
- Uploads to YouTube once per day.

## Prerequisites

- Python 3.10+
- ffmpeg and ffprobe in PATH
- Google Drive API access (service account or OAuth)
- YouTube Data API v3 OAuth credentials
- Whisk and Grok access (CLI or API via the command templates)

## Quick start (Windows UI - easiest)

1. Clone the repo:
   ```powershell
   git clone https://github.com/JonDipilato/uploader-agent.git
   cd uploader-agent
   ```
2. Run setup:
   ```powershell
   .\setup.ps1
   ```
3. Launch the UI:
   ```powershell
   .\start-ui.ps1
   ```
4. In the browser form:
   - Choose audio source (Local folder or Google Drive).
   - If Local folder: paste the MP3 folder path (example: `C:\Users\jon-d\Downloads\Music`).
   - If Drive: paste your Google Drive folder ID.
   - Choose Drive auth (service account is easiest) and upload the JSON file.
   - Upload YouTube OAuth client JSON.
   - Fill prompts, schedule time, optional text overlay, and loop generator (ffmpeg is simplest).
   - Click "Save config".
5. Set API keys (same PowerShell window):
   ```powershell
   $env:WHISK_API_KEY="YOUR_KEY"
   $env:GROK_API_KEY="YOUR_KEY"
   ```
6. Run once:
   ```powershell
   .\run-once.ps1
   ```
7. Test run (no upload, no repeat):
   ```powershell
   .\run-test.ps1 -Minutes 10
   ```
8. Schedule daily (runs in background):
   ```powershell
   .\schedule-task.ps1
   ```

## Password-protected UI (optional)

If you set a password, the Streamlit UI will prompt for it on load.

Local (PowerShell):
```powershell
$env:APP_PASSWORD="YOUR_PASSWORD"
```

Local (Streamlit secrets file):
```toml
app_password = "YOUR_PASSWORD"
```
Save that in `.streamlit/secrets.toml` (do not commit it).

## Streamlit Community Cloud (share with a friend)

This is the easiest way to share the UI without giving repo access.

1. Push the repo to GitHub.
2. Go to https://share.streamlit.io and click "New app".
3. Select your repo + branch and set the main file to `streamlit_app.py`.
4. In "Advanced settings" > "Secrets", add:
   ```toml
   app_password = "DilaraTemp#$"
   WHISK_API_KEY = "YOUR_KEY"
   GROK_API_KEY = "YOUR_KEY"
   OPENAI_API_KEY = "YOUR_KEY" # optional
   ```
5. Deploy and share the app URL + password.

Notes:
- Streamlit Community Cloud apps are public by URL on the free plan; the password gate protects access.
- Long 8-9 hour renders are best run locally or on your own machine.

## Credentials checklist

- Drive service account JSON (only if using Google Drive; share the folder with the service account email).
- Or Drive OAuth client JSON (if not using service account).
- YouTube OAuth client JSON (first run opens a browser to authorize).
- Whisk and Grok API keys (set in your environment).

## Persist API keys (Windows)

If you want the keys to persist across restarts:
```powershell
setx WHISK_API_KEY "YOUR_KEY"
setx GROK_API_KEY "YOUR_KEY"
```
Open a new PowerShell window after running `setx`.

## Finding your Drive folder ID

Open the folder in Google Drive and copy the ID from the URL:
`https://drive.google.com/drive/folders/<THIS_PART_IS_THE_ID>`

## Setup

1. Install dependencies:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
2. Copy the sample config:
   ```bash
   cp config.example.yaml config.yaml
   ```
3. Fill in Drive, Whisk, Grok, and YouTube settings in `config.yaml`.

## Google Drive

- Service account is the simplest. Share the Drive folder with the service account email.
- If you use OAuth, set `drive.use_service_account: false` and provide `oauth_client_json` and `token_json`.

## Whisk and Grok

Use the command template mode to call your local CLI or wrapper script:

```yaml
visuals:
  whisk_mode: "command"
  whisk_command:
    - whisk
    - "image"
    - "--prompt"
    - "{prompt}"
    - "--out"
    - "{output_path}"
```

```yaml
visuals:
  grok_mode: "command"
  grok_command:
    - grok
    - "video"
    - "--image"
    - "{image_path}"
    - "--prompt"
    - "{prompt}"
    - "--duration"
    - "{duration}"
    - "--fps"
    - "{fps}"
    - "--out"
    - "{output_path}"
```

If you already have assets, set `visuals.image_path` and/or `visuals.loop_video_path` to skip generation.
If you want to avoid Grok entirely, set `visuals.loop_provider: ffmpeg` (default) to create a loop from the image.
You can include `{overlay_text}` or `{date}` in `visuals.image_prompt` to align the prompt with the daily thumbnail text.

## OpenAI image generation (optional)

If you want a new original image each run without Whisk, set:
```yaml
visuals:
  image_provider: "openai"
  image_prompt: "cozy coffee shop interior, warm light, cinematic, empty space for text, high detail"
  openai_api_key_env: "OPENAI_API_KEY"
```
Then export your key in the environment before running:
```powershell
$env:OPENAI_API_KEY="sk-..."
```

## YouTube upload

- Create OAuth credentials in Google Cloud Console.
- Put the client JSON at the path in `upload.credentials_json`.
- The first run opens a browser to authorize and stores a refresh token in `upload.token_json`.
- If you enable thumbnail uploads, you may be prompted to re-authorize.

## Text overlay + thumbnails

Set `text_overlay.text` to burn text onto the video and generate a matching thumbnail. If you want the thumbnail uploaded automatically, set `text_overlay.upload_thumbnail: true`. You can also set `text_overlay.auto_texts` + `text_overlay.auto_mode` (daily/random) to rotate text automatically when `text_overlay.text` is blank. In the UI, use the "Text Overlay + Thumbnail" section.
In the UI, click "Preview thumbnail overlay" to see placement without rendering a full video.

## Tracklist timestamps

The agent can generate a `tracklist.txt` with timestamps, embed chapters in the MP4, and optionally append the list to the upload description. Control this via the `tracklist` section in config or the UI.

## Local audio (no Drive)

Set `audio.source: local` and `audio.local_folder` to your MP3 folder path. The UI exposes this as "Audio source".
YouTube APIs do not allow downloading music, so use local files or Drive instead.

## Test mode

Test mode disables uploads and playlist repetition. Run a quick test with:
```powershell
.\run-test.ps1 -Minutes 10
```
Set minutes to `0` to render the full length of the playlist once (no repeat).

## Run

Single run:
```bash
python -m src.agent --config config.yaml --once
```

Daily scheduling (uses `schedule`):
```bash
python -m src.agent --config config.yaml
```

## Windows quickstart

```powershell
.\setup.ps1
```

Launch the UI:
```powershell
.\start-ui.ps1
```
This opens a local browser at http://localhost:8501 where she can fill in the form and save `config.yaml`.

Preview-only UI (no saving):
```powershell
.\start-ui.ps1 -Demo
```

Then run once:
```powershell
.\run-once.ps1
```

Test run (no upload, no repeat):
```powershell
.\run-test.ps1 -Minutes 10
```

Or keep it running with the built-in scheduler:
```powershell
.\run-schedule.ps1
```

Or register a Windows Task Scheduler job (runs once per day in the background):
```powershell
.\schedule-task.ps1
```

To remove the scheduled task:
```powershell
.\schedule-task.ps1 -Remove
```

## Notes

- Target length is controlled by `audio.target_hours_min` and `audio.target_hours_max`.
- Visuals are looped continuously to match the audio length.
- Optional text overlay can be burned into the video and thumbnail using `text_overlay` settings.
- If you use text overlay, design the image prompt with empty space behind the text and provide a TTF/OTF font file.
- If you select the ffmpeg loop generator, no Grok account is required.
- If you enable `visuals.auto_background`, the agent will generate a plain background image with ffmpeg.
- For more motion, increase `visuals.loop_pan_amount` and `visuals.loop_zoom_amount`.
- Optional extra loop effects: set `visuals.loop_effects` (steam, sway, flicker, color_drift, vignette) and tweak `loop_sway_degrees`, `loop_flicker_amount`, `loop_hue_degrees`, `loop_vignette_angle`.
- For a coffee-steam look, enable `steam` and adjust `loop_steam_opacity`, `loop_steam_blur`, `loop_steam_noise`, `loop_steam_drift_x`, `loop_steam_drift_y`.
- For smoother motion, set `visuals.loop_motion_style: cinematic` and avoid `sway` unless you want a handheld feel.
- For production reliability, consider running the agent under systemd or a container with a watchdog.
