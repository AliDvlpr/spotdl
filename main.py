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

# --- Setup Logging ---
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

# --- Spotify Setup ---
sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(
    client_id=SPOTIFY_CLIENT_ID,
    client_secret=SPOTIFY_CLIENT_SECRET
))

def extract_playlist_id(url: str):
    match = re.search(r'playlist/([a-zA-Z0-9]+)', url)
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

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_button = InlineKeyboardButton("Help", callback_data="help")
    keyboard = InlineKeyboardMarkup([[help_button]])
    await update.message.reply_text(
        "👋 Hi! Send me a Spotify playlist link and I'll send you all songs as 320kbps MP3 files.",
        reply_markup=keyboard
    )

async def help_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "📚 **Help**\n\n"
        "• Send a Spotify playlist URL, and I will download each song and send it as a high quality MP3.\n"
        "• Please wait patiently while I download.\n"
        "• If you want to start again, just send another playlist URL.\n"
        "• Use /start to see this message again.",
        parse_mode="Markdown"
    )

async def handle_playlist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    playlist_id = extract_playlist_id(url)

    if not playlist_id:
        await update.message.reply_text("❌ Invalid Spotify playlist link. Please send a valid one.")
        return

    # Get playlist info
    try:
        playlist = sp.playlist(playlist_id)
        playlist_name = playlist["name"]
        tracks = playlist["tracks"]["items"]
        track_count = len(tracks)
    except Exception as e:
        logger.error(f"Spotify API error: {e}")
        await update.message.reply_text("❌ Failed to fetch playlist info. Try again later.")
        return

    await update.message.reply_text(f"🎵 Playlist *{playlist_name}* found with {track_count} tracks.\nStarting download...", parse_mode="Markdown")
    logger.info(f"Starting download: {playlist_name} ({track_count} tracks)")

    # Create temp dir
    download_dir = os.path.join(tempfile.gettempdir(), f"spotify_dl_{datetime.now().strftime('%Y%m%d%H%M%S')}")
    os.makedirs(download_dir, exist_ok=True)

    # Download & send songs one by one without intermediate messages to user
    failed_tracks = []
    for index, item in enumerate(tracks, start=1):
        track = item["track"]
        song_title = track["name"]
        artist_name = track["artists"][0]["name"]
        clean_filename = re.sub(r'[\\/*?:"<>|]', "", f"{song_title} - {artist_name}")
        save_path = os.path.join(download_dir, clean_filename)

        logger.info(f"Downloading ({index}/{track_count}): {clean_filename}")
        try:
            download_song(f"{song_title} {artist_name}", save_path)
            mp3_path = save_path + ".mp3"

            if os.path.exists(mp3_path):
                with open(mp3_path, "rb") as audio_file:
                    await update.message.reply_audio(audio=audio_file, title=song_title, performer=artist_name)
                os.remove(mp3_path)
            else:
                logger.warning(f"MP3 file missing after download: {mp3_path}")
                failed_tracks.append(clean_filename)
        except Exception as e:
            logger.error(f"Failed to download/send {clean_filename}: {e}")
            failed_tracks.append(clean_filename)

    # Clean temp dir
    shutil.rmtree(download_dir, ignore_errors=True)
    logger.info("Download process completed.")

    if failed_tracks:
        await update.message.reply_text(f"⚠️ Finished with errors on these tracks:\n" + "\n".join(failed_tracks))
    else:
        await update.message.reply_text("✅ All songs sent successfully!")

# --- Bot Setup ---
app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(help_callback, pattern="help"))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_playlist))

if __name__ == "__main__":
    app.run_polling()
