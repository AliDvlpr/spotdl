import os
import shutil
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from .spotify_service import extract_playlist_id, extract_track_id, get_playlist, get_track
from .downloader import download_song, clean_filename, get_temp_dir

logger = logging.getLogger(__name__)

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

async def process_playlist(update, playlist_id: str):
    playlist = get_playlist(playlist_id)
    if not playlist:
        await update.message.reply_text("❌ Failed to fetch playlist info.")
        return

    playlist_name = playlist["name"]
    tracks = playlist["tracks"]["items"]
    await update.message.reply_text(f"🎵 Playlist *{playlist_name}* found with {len(tracks)} tracks.\nStarting download...", parse_mode="Markdown")

    download_dir = get_temp_dir()
    failed_tracks = []

    for idx, item in enumerate(tracks, start=1):
        track = item["track"]
        title, artist = track["name"], track["artists"][0]["name"]
        filename = clean_filename(f"{title} - {artist}")
        path = os.path.join(download_dir, filename)
        try:
            download_song(f"{title} {artist}", path)
            mp3_path = path + ".mp3"
            if os.path.exists(mp3_path):
                with open(mp3_path, "rb") as f:
                    await update.message.reply_audio(f, title=title, performer=artist)
                os.remove(mp3_path)
            else:
                failed_tracks.append(filename)
        except Exception as e:
            logger.error(f"Failed {filename}: {e}")
            failed_tracks.append(filename)

    shutil.rmtree(download_dir, ignore_errors=True)
    if failed_tracks:
        await update.message.reply_text(f"⚠️ Errors with:\n" + "\n".join(failed_tracks))
    else:
        await update.message.reply_text("✅ All songs sent successfully!")

async def process_single_track(update, track_id: str):
    track = get_track(track_id)
    if not track:
        await update.message.reply_text("❌ Failed to fetch track info.")
        return

    title, artist = track["name"], track["artists"][0]["name"]
    await update.message.reply_text(f"🎶 Downloading *{title}* by {artist}...", parse_mode="Markdown")

    path = os.path.join(get_temp_dir(), clean_filename(f"{title} - {artist}"))
    try:
        download_song(f"{title} {artist}", path)
        mp3_path = path + ".mp3"
        if os.path.exists(mp3_path):
            with open(mp3_path, "rb") as f:
                await update.message.reply_audio(f, title=title, performer=artist)
            os.remove(mp3_path)
        else:
            await update.message.reply_text("❌ Failed to find MP3 after download.")
    except Exception as e:
        logger.error(f"Error downloading track: {e}")
        await update.message.reply_text("❌ Failed to download this track.")
