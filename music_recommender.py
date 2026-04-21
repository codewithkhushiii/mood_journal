import random

MOOD_MUSIC_MAP = {
    "happy": [
        {"title": "Happy", "artist": "Pharrell Williams"},
        {"title": "On Top of the World", "artist": "Imagine Dragons"},
    ],
    "sad": [
        {"title": "Fix You", "artist": "Coldplay"},
        {"title": "Someone Like You", "artist": "Adele"},
    ],
    "stressed": [
        {"title": "Weightless", "artist": "Marconi Union"},
        {"title": "Sunset Lover", "artist": "Petit Biscuit"},
    ],
    "angry": [
        {"title": "Believer", "artist": "Imagine Dragons"},
        {"title": "Stronger", "artist": "Kanye West"},
    ],
    "calm": [
        {"title": "Bloom", "artist": "The Paper Kites"},
        {"title": "River Flows in You", "artist": "Yiruma"},
    ]
}


def recommend_music(mood: str):
    mood = mood.lower()

    if mood not in MOOD_MUSIC_MAP:
        return {"message": "No recommendation found for this mood"}

    song = random.choice(MOOD_MUSIC_MAP[mood])

    return {
        "mood": mood,
        "song": song,
        "message": f"This song suits your {mood} mood 🎧"
    }