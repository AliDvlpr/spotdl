import yt_dlp
import re
import os
import tempfile
from datetime import datetime

def clean_filename(text: str):
    return re.sub(r'[\\/*?:"<>|]', "", text)

def download_song(search_query: str, save_path: str):
    ydl_opts = {
        "format": "bestaudio/best",
        "noplaylist": True,
        "quiet": True,
        "outtmpl": save_path + ".%(ext)s",
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "320"
        }]
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.extract_info(f"ytsearch1:{search_query}", download=True)

def get_temp_dir(prefix="spotify_dl"):
    path = os.path.join(tempfile.gettempdir(), f"{prefix}_{datetime.now().strftime('%Y%m%d%H%M%S')}")
    os.makedirs(path, exist_ok=True)
    return path
