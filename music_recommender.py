"""
music_recommender.py
iTunes-powered mood-based music recommendations.
Uses Apple's free iTunes Search API — no API key or account required.
"""

import random
import logging
import requests

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ─── Mood → iTunes Search Config ─────────────────────────────────────────────
# Each mood maps to a list of search terms rotated randomly for variety.

MOOD_CONFIG = {
    "happy": {
        "queries": ["happy upbeat pop", "feel good summer", "party dance pop", "cheerful hits"],
        "emoji": "😊",
    },
    "sad": {
        "queries": ["sad emotional ballad", "heartbreak songs", "melancholy acoustic", "tearjerker slow"],
        "emoji": "😢",
    },
    "stressed": {
        "queries": ["relaxing calm instrumental", "stress relief ambient", "peaceful meditation music", "soothing nature sounds"],
        "emoji": "😤",
    },
    "angry": {
        "queries": ["intense rock anthem", "powerful metal", "rage punk", "hard rock energy"],
        "emoji": "😠",
    },
    "calm": {
        "queries": ["peaceful classical piano", "calm jazz instrumental", "ambient relaxation", "soft acoustic guitar"],
        "emoji": "😌",
    },
    "excited": {
        "queries": ["hype edm dance", "festival banger", "energetic pop hit", "euphoric club music"],
        "emoji": "🤩",
    },
    "anxious": {
        "queries": ["soothing lo-fi chill", "anxiety relief piano", "gentle acoustic calm", "soft ambient sleep"],
        "emoji": "😰",
    },
    "romantic": {
        "queries": ["romantic love song", "slow dance R&B", "sweet soul ballad", "love acoustic"],
        "emoji": "🥰",
    },
    "focused": {
        "queries": ["focus study instrumental", "concentration classical", "deep work lo-fi", "productivity ambient"],
        "emoji": "🧠",
    },
    "energetic": {
        "queries": ["workout pump up", "motivation gym music", "running upbeat", "high energy hip hop"],
        "emoji": "⚡",
    },
}

# Alias mappings for common mood variants
MOOD_ALIASES = {
    "joy": "happy", "joyful": "happy", "cheerful": "happy",
    "depressed": "sad", "melancholy": "sad", "upset": "sad",
    "nervous": "anxious",
    "furious": "angry", "mad": "angry",
    "relaxed": "calm", "peaceful": "calm", "serene": "calm", "chill": "calm",
    "tense": "stressed", "overwhelmed": "stressed",
    "hyped": "excited", "thrilled": "excited",
    "love": "romantic", "amorous": "romantic",
    "motivated": "energetic", "pumped": "energetic",
    "productive": "focused", "concentrating": "focused",
}


def _resolve_mood(mood: str) -> str:
    """Normalize and resolve mood aliases to a canonical key."""
    mood = mood.lower().strip()
    return MOOD_ALIASES.get(mood, mood)


def _format_itunes_track(track: dict) -> dict:
    """Extract clean track info from an iTunes track object."""
    return {
        "title": track.get("trackName", "Unknown"),
        "artist": track.get("artistName", "Unknown"),
        "album": track.get("collectionName", ""),
        "album_art": track.get("artworkUrl100", "").replace("100x100", "300x300"),
        "itunes_url": track.get("trackViewUrl"),     # iTunes Store link
        "preview_url": track.get("previewUrl"),      # 30-sec AAC preview
        "duration_ms": track.get("trackTimeMillis"),
        "track_number": track.get("trackNumber", 0),
    }


def _fetch_itunes_tracks(query: str, limit: int = 10) -> list[dict]:
    """Query the iTunes Search API and return formatted tracks."""
    url = "https://itunes.apple.com/search"
    params = {
        "term": query,
        "media": "music",
        "entity": "song",
        "limit": 25,
        "country": "IN",
    }
    try:
        resp = requests.get(url, params=params, timeout=8)
        resp.raise_for_status()
        results = resp.json().get("results", [])
        # Filter to actual tracks only
        tracks = [r for r in results if r.get("kind") == "song"]
        random.shuffle(tracks)
        return [_format_itunes_track(t) for t in tracks[:limit]]
    except Exception as e:
        logger.error(f"iTunes API error: {e}")
        return []


def _static_fallback(mood: str) -> dict:
    """Return a static recommendation when iTunes API is unreachable."""
    STATIC_MAP = {
        "happy":    {"title": "Happy",                  "artist": "Pharrell Williams"},
        "sad":      {"title": "Fix You",                "artist": "Coldplay"},
        "stressed": {"title": "Weightless",             "artist": "Marconi Union"},
        "angry":    {"title": "Believer",               "artist": "Imagine Dragons"},
        "calm":     {"title": "River Flows in You",     "artist": "Yiruma"},
        "excited":  {"title": "Can't Stop the Feeling!","artist": "Justin Timberlake"},
        "anxious":  {"title": "Breathe (2 AM)",         "artist": "Anna Nalick"},
        "romantic": {"title": "Perfect",                "artist": "Ed Sheeran"},
        "focused":  {"title": "Experience",             "artist": "Ludovico Einaudi"},
        "energetic":{"title": "Eye of the Tiger",       "artist": "Survivor"},
    }
    config = MOOD_CONFIG.get(mood, MOOD_CONFIG["calm"])
    song = STATIC_MAP.get(mood, {"title": "River Flows in You", "artist": "Yiruma"})

    return {
        "mood": mood,
        "emoji": config["emoji"],
        "source": "static",
        "song": {**song, "album_art": None, "itunes_url": None, "preview_url": None},
        "recommendations": [],
        "message": f"🎧 {song['title']} by {song['artist']} suits your {mood} mood!",
    }


# ─── Public API ───────────────────────────────────────────────────────────────

def recommend_music(mood: str, limit: int = 5) -> dict:
    """
    Main entry point.
    Returns mood-matched music from the iTunes Search API (free, no key needed).

    Args:
        mood  : User's current mood string
        limit : Number of recommendations to return (default 5)

    Returns dict with:
        - mood  : resolved canonical mood string
        - emoji : mood emoji
        - source: "itunes" | "static"
        - song  : the top recommended track (title, artist, album, album_art,
                  itunes_url, preview_url, duration_ms, track_number)
        - recommendations: list of all fetched tracks
        - message: human-friendly summary string
    """
    mood = _resolve_mood(mood)
    config = MOOD_CONFIG.get(mood)

    # Unknown mood → default to calm
    if not config:
        mood = "calm"
        config = MOOD_CONFIG["calm"]

    # Pick a random query for variety
    query = random.choice(config["queries"])
    logger.info(f"iTunes search for mood='{mood}' using query: '{query}'")

    tracks = _fetch_itunes_tracks(query, limit=limit)

    if not tracks:
        logger.warning("iTunes returned no results — using static fallback.")
        return _static_fallback(mood)

    top = tracks[0]

    return {
        "mood": mood,
        "emoji": config["emoji"],
        "source": "itunes",
        "song": top,
        "recommendations": tracks,
        "message": f"🎧 iTunes picked '{top['title']}' by {top['artist']} for your {mood} mood!",
    }