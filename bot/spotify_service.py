import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import re
import logging

from .config import SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET

logger = logging.getLogger(__name__)

sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(
    client_id=SPOTIFY_CLIENT_ID,
    client_secret=SPOTIFY_CLIENT_SECRET
))

def extract_playlist_id(url: str):
    match = re.search(r'playlist/([a-zA-Z0-9]+)', url)
    return match.group(1) if match else None

def extract_track_id(url: str):
    match = re.search(r'track/([a-zA-Z0-9]+)', url)
    return match.group(1) if match else None

def get_playlist(playlist_id: str):
    try:
        return sp.playlist(playlist_id)
    except Exception as e:
        logger.error(f"Spotify playlist fetch error: {e}")
        return None

def get_track(track_id: str):
    try:
        return sp.track(track_id)
    except Exception as e:
        logger.error(f"Spotify track fetch error: {e}")
        return None
