import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import List

import streamlit as st

try:
    from yt_dlp import YoutubeDL
except Exception:
    st.error("Missing dependency: install requirements (`pip install -r requirements.txt`).")
    raise


st.set_page_config(page_title="SongDown — YouTube to MP3", layout="centered")

DOWNLOAD_DIR = Path.home() / "Downloads"
DOWNLOAD_DIR.mkdir(exist_ok=True)

# Color palette from attachments: 311B66, 50409A, 964BC2, FF7BBF
PALETTE = {
    "c1": "#311B66",
    "c2": "#50409A",
    "c3": "#964BC2",
    "c4": "#FF7BBF",
}

# Inject CSS to style the app and present the input area in a centered 'card'
st.markdown(
    f"""
    <link href="https://fonts.googleapis.com/css2?family=Merriweather:wght@300;400;700&display=swap" rel="stylesheet">
    <style>
      :root{{--c1:{PALETTE['c1']}; --c2:{PALETTE['c2']}; --c3:{PALETTE['c3']}; --c4:{PALETTE['c4']};}}
      html, body {{background: linear-gradient(180deg, var(--c1) 0%, var(--c2) 100%);}}
      * {{ font-family: 'Merriweather', serif; }}
      .stApp .block-container {{
        max-width: 880px;
        margin: 48px auto;
        padding: 32px;
        background: linear-gradient(180deg, rgba(255,255,255,0.03), rgba(255,255,255,0.02));
        border-radius: 16px;
        box-shadow: 0 12px 40px rgba(0,0,0,0.45);
        color: #ffffff;
        border: 1px solid rgba(255,255,255,0.04);
      }}
      .hero-title {{ font-size:34px; font-weight:700; margin-bottom:6px; color:var(--c4); }}
      .hero-sub {{ color:var(--c3); margin-bottom:18px; }}
      .stButton>button {{
        background: linear-gradient(90deg, var(--c3), var(--c4)) !important;
        color: #0b0b0b !important;
        border: none !important;
        padding: 10px 20px !important;
        border-radius: 10px !important;
        font-weight:700 !important;
        box-shadow: 0 6px 18px rgba(0,0,0,0.25);
      }}
      .stTextInput>div>div>input, .stTextInput>div>input {{ background: rgba(255,255,255,0.04) !important; color: #fff !important; border-radius:8px; padding:10px; }}
      .stSelectbox>div>div>div{{ background: rgba(255,255,255,0.02) !important; color:#fff !important; border-radius:8px; padding:8px; }}
      .stDownloadButton>button {{ background: transparent !important; border: 1px solid rgba(255,255,255,0.12) !important; color: #fff !important; border-radius:8px; padding:6px 10px; }}
      .card-sub {{ color: var(--c3); }}
      .file-row {{ display:flex; align-items:center; gap:12px; padding:8px 6px; border-bottom:1px solid rgba(255,255,255,0.03); }}
      .file-name {{ flex:1; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }}
      .file-meta {{ color: rgba(255,255,255,0.7); font-size:13px; min-width:150px; text-align:right; }}
    </style>
    """,
    unsafe_allow_html=True,
)


def safe_filename(name: str, max_length: int = 150) -> str:
    name = re.sub(r"[\\/*?:\"<>|]", "", name)
    name = re.sub(r"\s+", " ", name).strip()
    if len(name) > max_length:
        name = name[:max_length]
    return name


def ffprobe_recognizes_mp3(path: Path) -> bool:
    # Returns True if ffprobe reports mp3 format
    if shutil.which("ffprobe") is None:
        return False
    try:
        completed = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=format_name",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                str(path),
            ],
            capture_output=True,
            text=True,
            timeout=15,
        )
        out = (completed.stdout or "").lower()
        return "mp3" in out
    except Exception:
        return False


def download_and_validate(url: str, final_out_dir: Path, quality: str = "192") -> List[Path]:
    final_out_dir.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        outtmpl = str(tmp / "%(title)s.%(ext)s")

        ydl_opts = {
            "format": "bestaudio/best",
            "outtmpl": outtmpl,
            "noplaylist": False,
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": quality,
                }
            ],
            # keep logs visible for debugging
            "quiet": False,
            "no_warnings": False,
        }

        with YoutubeDL(ydl_opts) as ydl:
            ydl.extract_info(url, download=True)

        # Find any .mp3 files in the temp folder
        candidates = sorted(tmp.glob("*.mp3"))
        accepted: List[Path] = []

        for cand in candidates:
            # Sanity check: ensure ffprobe recognizes it as mp3 (if available)
            ok = ffprobe_recognizes_mp3(cand)
            if not ok:
                # try a quick ffmpeg decode to detect broken files
                try:
                    res = subprocess.run(
                        ["ffmpeg", "-v", "error", "-i", str(cand), "-f", "null", "-"],
                        capture_output=True,
                        text=True,
                        timeout=20,
                    )
                    ok = res.returncode == 0
                except Exception:
                    ok = False

            if not ok:
                # don't move unrecognized/invalid files
                st.warning(f"Discarding unrecognized or invalid file: {cand.name}")
                try:
                    cand.unlink()
                except Exception:
                    pass
                continue

            # Sanitize filename and move atomically into final folder
            safe_name = safe_filename(cand.stem) + ".mp3"
            dest = final_out_dir / safe_name
            try:
                # If dest exists, append a counter
                if dest.exists():
                    base = final_out_dir / (safe_filename(cand.stem) + "")
                    i = 1
                    while dest.exists():
                        dest = final_out_dir / f"{safe_filename(cand.stem)} ({i}).mp3"
                        i += 1

                os.replace(cand, dest)
                # Restrict permissions: readable/writable only by owner
                try:
                    os.chmod(dest, 0o600)
                except Exception:
                    pass
                accepted.append(dest)
            except Exception as e:
                st.error(f"Failed to move validated file into place: {e}")

        return accepted


def main():

    # Hero / title inside the card
    st.markdown(
        """
        <div style='margin-bottom:8px'>
          <div class='hero-title'>SongDown — YouTube → MP3</div>
          <div class='hero-sub'>Secure prototype — files validated and saved where you choose</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Layout inside the styled "card" (the block-container is styled above)
    url = st.text_input("YouTube video or playlist URL")

    # Require the user to choose where to save before download.
    save_option = st.selectbox(
        "Where should the downloaded MP3 be saved?",
        ["System Downloads", "Desktop", "Custom path"],
        index=0,
    )

    if save_option == "System Downloads":
        out_dir = str(DOWNLOAD_DIR)
    elif save_option == "Desktop":
        out_dir = str(Path.home() / "Desktop")
    else:
        out_dir = st.text_input("Custom output folder (enter full path)", "")

    col1, col2 = st.columns([1, 3])
    with col1:
        quality = st.selectbox("MP3 bitrate (kbps)", [128, 192, 256, 320], index=1)
    with col2:
        st.markdown(f"**Selected folder:** <span class=\"card-sub\">{out_dir or 'None'}</span>", unsafe_allow_html=True)

    if st.button("Download"):
        if not url:
            st.error("Please provide a YouTube URL.")
            return

        # ensure out_dir is set (user must confirm where to save)
        if not out_dir:
            st.error("Please select or enter an output folder before downloading.")
            return

        out_path = Path(out_dir)
        if not out_path.exists():
            try:
                out_path.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                st.error(f"Could not create output directory: {e}")
                return

        if shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None:
            st.warning("ffmpeg/ffprobe not found on PATH. Audio validation may be limited. Install ffmpeg to improve security checks.")

        with st.spinner("Downloading, converting and validating — this may take a while..."):
            try:
                files = download_and_validate(url, out_path, quality=str(quality))
            except Exception as e:
                st.error(f"Download/validation failed: {e}")
                return

        if not files:
            st.info("No validated MP3 files available after download. Check the server logs or try a different URL.")
            return

        st.success(f"Completed: {len(files)} validated file(s) available in {out_path}")

        # Present files in nicer rows with meta and download button
        for f in files:
            try:
                stat = f.stat()
                size_mb = stat.st_size / (1024 * 1024)
                mtime = stat.st_mtime
                from datetime import datetime

                mtime_s = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M")

                cols = st.columns([6, 2, 2])
                with cols[0]:
                    st.markdown(f"<div class='file-row'><div class='file-name'>{f.name}</div></div>", unsafe_allow_html=True)
                with cols[1]:
                    st.markdown(f"<div class='file-meta'>{size_mb:.2f} MB</div>", unsafe_allow_html=True)
                with cols[2]:
                    with open(f, "rb") as fh:
                        data = fh.read()
                    st.download_button(label="Download", data=data, file_name=f.name, mime="audio/mpeg")
            except Exception as e:
                st.error(f"Could not prepare download for {f.name}: {e}")


if __name__ == "__main__":
    main()
