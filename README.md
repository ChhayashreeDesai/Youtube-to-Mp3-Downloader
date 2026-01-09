# YouTube to MP3 downloader

This small Python CLI downloads YouTube videos (or playlists) and saves audio as MP3 using `yt-dlp` and `ffmpeg`.

Requirements
- Python 3.8+
- `yt-dlp` (install via pip)
- `ffmpeg` available on your PATH

Install

On Windows (PowerShell):

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Install `ffmpeg`:
- Option A: Install with Chocolatey (if you have it): `choco install ffmpeg -y`
- Option B: Download static build from https://ffmpeg.org and add to PATH

Usage

Command-line:

```powershell
python yt_to_mp3.py "https://www.youtube.com/watch?v=VIDEO_ID"
# specify output directory and quality
python yt_to_mp3.py "https://www.youtube.com/watch?v=VIDEO_ID" -o "C:\Music" -q 256
```

Streamlit prototype:

```powershell
streamlit run streamlit_app.py
```

Notes
 - The script uses `yt-dlp` postprocessor which requires `ffmpeg` to convert audio to MP3.
 - For playlists, the script will download all videos by default. Use `--no-playlist` to restrict to a single video.
 - By default both the CLI and Streamlit prototype save MP3 files to your system Downloads folder (e.g. `C:\Users\<you>\Downloads`). You can override this with the `-o/--output` flag or by changing the output folder in the Streamlit UI.

Security and validation
- The Streamlit prototype downloads into a temporary folder first, validates the produced MP3 files using `ffprobe`/`ffmpeg`, and only moves validated files into your Downloads folder. This helps reduce the chance of arbitrary files or broken outputs being saved to your system.
- For best protection install `ffmpeg` (which includes `ffprobe`) and ensure it's on PATH. The app will warn if not found and validation will be limited.



