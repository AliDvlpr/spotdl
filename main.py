import os
import re
import shutil
import yt_dlp
import tempfile
import logging
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    filters, ContextTypes, CallbackQueryHandler
)
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from datetime import datetime

# --- Logging ---
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- Load .env ---
load_dotenv()
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")

# --- Spotify API ---
sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(
    client_id=SPOTIFY_CLIENT_ID,
    client_secret=SPOTIFY_CLIENT_SECRET
))

# --- Helpers ---
def extract_playlist_id(url: str):
    match = re.search(r'playlist/([a-zA-Z0-9]+)', url)
    return match.group(1) if match else None

def extract_track_id(url: str):
    match = re.search(r'track/([a-zA-Z0-9]+)', url)
    return match.group(1) if match else None

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

# --- Commands ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_button = InlineKeyboardButton("Help", callback_data="help")
    keyboard = InlineKeyboardMarkup([[help_button]])
    await update.message.reply_text(
        "👋 Hi! Send me a Spotify playlist **or** single track link and I'll send you high quality MP3 files.",
        reply_markup=keyboard
    )

async def help_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "📚 **Help**\n\n"
        "• Send a Spotify playlist URL: I'll send all songs.\n"
        "• Send a Spotify track URL: I'll send that one song.\n"
        "• MP3 files are 320kbps.\n",
        parse_mode="Markdown"
    )

async def handle_spotify(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()

    playlist_id = extract_playlist_id(url)
    track_id = extract_track_id(url)

    if playlist_id:
        await process_playlist(update, playlist_id)
    elif track_id:
        await process_single_track(update, track_id)
    else:
        await update.message.reply_text("❌ Invalid Spotify link. Send a playlist or track link.")

async def process_playlist(update: Update, playlist_id: str):
    try:
        playlist = sp.playlist(playlist_id)
        playlist_name = playlist["name"]
        tracks = playlist["tracks"]["items"]
    except Exception as e:
        logger.error(f"Spotify API error: {e}")
        await update.message.reply_text("❌ Failed to fetch playlist info.")
        return

    await update.message.reply_text(f"🎵 Playlist *{playlist_name}* found with {len(tracks)} tracks.\nStarting download...", parse_mode="Markdown")

    download_dir = os.path.join(tempfile.gettempdir(), f"spotify_dl_{datetime.now().strftime('%Y%m%d%H%M%S')}")
    os.makedirs(download_dir, exist_ok=True)

    failed_tracks = []
    for index, item in enumerate(tracks, start=1):
        track = item["track"]
        song_title = track["name"]
        artist_name = track["artists"][0]["name"]
        clean_filename = re.sub(r'[\\/*?:"<>|]', "", f"{song_title} - {artist_name}")
        save_path = os.path.join(download_dir, clean_filename)

        logger.info(f"Downloading ({index}/{len(tracks)}): {clean_filename}")
        try:
            download_song(f"{song_title} {artist_name}", save_path)
            mp3_path = save_path + ".mp3"

            if os.path.exists(mp3_path):
                with open(mp3_path, "rb") as audio_file:
                    await update.message.reply_audio(audio=audio_file, title=song_title, performer=artist_name)
                os.remove(mp3_path)
            else:
                failed_tracks.append(clean_filename)
        except Exception as e:
            logger.error(f"Failed to download/send {clean_filename}: {e}")
            failed_tracks.append(clean_filename)

    shutil.rmtree(download_dir, ignore_errors=True)

    if failed_tracks:
        await update.message.reply_text(f"⚠️ Errors with:\n" + "\n".join(failed_tracks))
    else:
        await update.message.reply_text("✅ All songs sent successfully!")

async def process_single_track(update: Update, track_id: str):
    try:
        track = sp.track(track_id)
        song_title = track["name"]
        artist_name = track["artists"][0]["name"]
    except Exception as e:
        logger.error(f"Spotify API error: {e}")
        await update.message.reply_text("❌ Failed to fetch track info.")
        return

    await update.message.reply_text(f"🎶 Downloading *{song_title}* by {artist_name}...", parse_mode="Markdown")

    download_dir = tempfile.gettempdir()
    clean_filename = re.sub(r'[\\/*?:"<>|]', "", f"{song_title} - {artist_name}")
    save_path = os.path.join(download_dir, clean_filename)

    try:
        download_song(f"{song_title} {artist_name}", save_path)
        mp3_path = save_path + ".mp3"

        if os.path.exists(mp3_path):
            with open(mp3_path, "rb") as audio_file:
                await update.message.reply_audio(audio=audio_file, title=song_title, performer=artist_name)
            os.remove(mp3_path)
        else:
            await update.message.reply_text("❌ Failed to find MP3 after download.")
    except Exception as e:
        logger.error(f"Error downloading track: {e}")
        await update.message.reply_text("❌ Failed to download this track.")

# --- Bot Setup ---
app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(help_callback, pattern="help"))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_spotify))

if __name__ == "__main__":
    app.run_polling()
