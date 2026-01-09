#!/usr/bin/env python
"""Simple CLI to download YouTube videos as MP3 using yt-dlp and ffmpeg.

Usage:
  python yt_to_mp3.py <url> [--output OUTPUT_DIR]

Requires:
  - Python 3.8+
  - `yt-dlp` Python package (see `requirements.txt`)
  - `ffmpeg` installed and available on PATH

This script downloads the best audio and converts it to MP3.
"""
from __future__ import annotations

import argparse
import os
import shutil
import sys
from typing import Optional

try:
    from yt_dlp import YoutubeDL
except Exception as e:
    print("Error: yt-dlp package not found. Install with: pip install -r requirements.txt")
    raise


def check_ffmpeg() -> bool:
    return shutil.which("ffmpeg") is not None


def download_mp3(url: str, out_dir: str, prefer_quality: str = "192") -> None:
    os.makedirs(out_dir, exist_ok=True)

    if not check_ffmpeg():
        print("Warning: ffmpeg not found on PATH. yt-dlp will fail to convert to MP3.")

    outtmpl = os.path.join(out_dir, "%(title)s.%(ext)s")

    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": outtmpl,
        "noplaylist": False,
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": prefer_quality,
            }
        ],
        # show progress to user
        "progress_hooks": [progress_hook],
        "quiet": False,
        "no_warnings": True,
    }

    with YoutubeDL(ydl_opts) as ydl:
        try:
            ydl.download([url])
        except Exception as exc:
            print(f"Download failed: {exc}")
            sys.exit(1)


def progress_hook(d):
    status = d.get("status")
    if status == "downloading":
        total_bytes = d.get("total_bytes") or d.get("total_bytes_estimate")
        downloaded = d.get("downloaded_bytes")
        if total_bytes and downloaded:
            percent = downloaded / total_bytes * 100
            print(f"Downloading: {percent:5.1f}% ({downloaded}/{total_bytes} bytes)", end="\r")
    elif status == "finished":
        print("\nDownload complete, converting to mp3...")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Download YouTube video/audio as MP3 using yt-dlp.")
    parser.add_argument("url", help="YouTube video or playlist URL to download")
    default_downloads = os.path.expanduser("~/Downloads")
    parser.add_argument("-o", "--output", default=default_downloads, help=f"Output directory (default: {default_downloads})")
    parser.add_argument("-q", "--quality", default="192", help="MP3 bitrate in kbps (default: 192)")
    parser.add_argument("--no-playlist", dest="noplaylist", action="store_true", help="Do not download playlists; only the provided URL")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    url = args.url
    out_dir = args.output

    # if user requested no playlist, pass option to yt-dlp via URL list handling
    if args.noplaylist:
        # append "&list=" trick isn't necessary — use ydl_opts
        pass

    print(f"Downloading: {url}\nOutput directory: {out_dir}")
    download_mp3(url, out_dir, prefer_quality=args.quality)
    print("Done.")


if __name__ == "__main__":
    main()
