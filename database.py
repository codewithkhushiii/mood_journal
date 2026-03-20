"""
MongoDB Database Layer — Async with Motor
Handles all CRUD + advanced aggregation queries for mood analysis.
"""

import os
from datetime import datetime, timedelta, date
from typing import Optional
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
MONGODB_DB = os.getenv("MONGODB_DB", "moodboard")

# ─── Connection ───────────────────────────────────────────────
client: Optional[AsyncIOMotorClient] = None
db = None


async def connect_db():
    global client, db
    client = AsyncIOMotorClient(MONGODB_URI)
    db = client[MONGODB_DB]

    # Create indexes for fast queries
    await db.moods.create_index("date")
    await db.moods.create_index("mood")
    await db.moods.create_index("user_id")
    await db.moods.create_index([("user_id", 1), ("created_at", -1)])
    print(f"✅ Connected to MongoDB: {MONGODB_DB}")


async def close_db():
    global client
    if client:
        client.close()
        print("🔌 MongoDB connection closed")


def get_db():
    return db


# ─── MOOD EMOJI MAP ──────────────────────────────────────────
MOOD_EMOJIS = {
    "happy": "😊", "sad": "😢", "angry": "😤", "anxious": "😰",
    "excited": "🤩", "calm": "😌", "tired": "😴", "loved": "🥰",
    "confused": "😵‍💫", "productive": "💪", "creative": "🎨",
    "grateful": "🙏", "stressed": "😫", "hopeful": "🌟",
    "lonely": "🥺", "proud": "🦁", "nostalgic": "🌅",
    "motivated": "🚀", "overwhelmed": "🌊", "peaceful": "🕊️",
}

MOOD_CATEGORIES = {
    "positive": ["happy", "excited", "calm", "loved", "productive",
                  "creative", "grateful", "hopeful", "proud",
                  "motivated", "peaceful"],
    "negative": ["sad", "angry", "anxious", "tired", "confused",
                  "stressed", "lonely", "overwhelmed"],
    "neutral": ["nostalgic"],
}


# ─── CRUD Operations ─────────────────────────────────────────
async def add_mood_entry(
    user_id: str,
    mood: str,
    note: str = "",
    intensity: int = 5,
    tags: list = None,
    activities: list = None,
):
    mood_lower = mood.lower()
    now = datetime.utcnow()

    # Determine category
    category = "neutral"
    for cat, moods_list in MOOD_CATEGORIES.items():
        if mood_lower in moods_list:
            category = cat
            break

    entry = {
        "user_id": user_id,
        "mood": mood_lower,
        "emoji": MOOD_EMOJIS.get(mood_lower, "🫠"),
        "category": category,
        "note": note,
        "intensity": max(1, min(10, intensity)),
        "tags": tags or [],
        "activities": activities or [],
        "date": now.strftime("%Y-%m-%d"),
        "time": now.strftime("%H:%M"),
        "hour": now.hour,
        "day_of_week": now.strftime("%A"),
        "week_number": now.isocalendar()[1],
        "month": now.strftime("%B"),
        "created_at": now,
    }

    result = await db.moods.insert_one(entry)
    entry["_id"] = str(result.inserted_id)
    return entry


async def get_recent_moods(user_id: str, limit: int = 50):
    cursor = db.moods.find(
        {"user_id": user_id},
        {"_id": 0}
    ).sort("created_at", -1).limit(limit)
    return await cursor.to_list(length=limit)


async def get_all_moods(user_id: str):
    cursor = db.moods.find(
        {"user_id": user_id},
        {"_id": 0}
    ).sort("created_at", -1)
    return await cursor.to_list(length=10000)


async def get_mood_count(user_id: str) -> int:
    return await db.moods.count_documents({"user_id": user_id})


async def delete_all_moods(user_id: str):
    result = await db.moods.delete_many({"user_id": user_id})
    return result.deleted_count


# ─── Advanced Analytics Aggregations ─────────────────────────
async def get_mood_distribution(user_id: str):
    pipeline = [
        {"$match": {"user_id": user_id}},
        {"$group": {
            "_id": "$mood",
            "count": {"$sum": 1},
            "avg_intensity": {"$avg": "$intensity"},
            "emoji": {"$first": "$emoji"},
            "category": {"$first": "$category"},
        }},
        {"$sort": {"count": -1}},
    ]
    cursor = db.moods.aggregate(pipeline)
    return await cursor.to_list(length=100)


async def get_hourly_patterns(user_id: str):
    pipeline = [
        {"$match": {"user_id": user_id}},
        {"$group": {
            "_id": "$hour",
            "moods": {"$push": "$mood"},
            "avg_intensity": {"$avg": "$intensity"},
            "count": {"$sum": 1},
            "dominant_category": {"$first": "$category"},
        }},
        {"$sort": {"_id": 1}},
    ]
    cursor = db.moods.aggregate(pipeline)
    return await cursor.to_list(length=24)


async def get_weekly_patterns(user_id: str):
    pipeline = [
        {"$match": {"user_id": user_id}},
        {"$group": {
            "_id": "$day_of_week",
            "moods": {"$push": "$mood"},
            "avg_intensity": {"$avg": "$intensity"},
            "count": {"$sum": 1},
            "positive_count": {
                "$sum": {"$cond": [{"$eq": ["$category", "positive"]}, 1, 0]}
            },
            "negative_count": {
                "$sum": {"$cond": [{"$eq": ["$category", "negative"]}, 1, 0]}
            },
        }},
    ]
    cursor = db.moods.aggregate(pipeline)
    results = await cursor.to_list(length=7)

    day_order = ["Monday", "Tuesday", "Wednesday",
                 "Thursday", "Friday", "Saturday", "Sunday"]
    sorted_results = sorted(
        results,
        key=lambda x: day_order.index(x["_id"]) if x["_id"] in day_order else 7
    )
    return sorted_results


async def get_monthly_trend(user_id: str, months: int = 3):
    cutoff = datetime.utcnow() - timedelta(days=months * 30)
    pipeline = [
        {"$match": {"user_id": user_id, "created_at": {"$gte": cutoff}}},
        {"$group": {
            "_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"}},
            "avg_intensity": {"$avg": "$intensity"},
            "moods": {"$push": "$mood"},
            "categories": {"$push": "$category"},
            "count": {"$sum": 1},
        }},
        {"$sort": {"_id": 1}},
    ]
    cursor = db.moods.aggregate(pipeline)
    return await cursor.to_list(length=200)


async def get_streak(user_id: str) -> int:
    pipeline = [
        {"$match": {"user_id": user_id}},
        {"$group": {"_id": "$date"}},
        {"$sort": {"_id": -1}},
    ]
    cursor = db.moods.aggregate(pipeline)
    dates = [doc["_id"] for doc in await cursor.to_list(length=1000)]

    if not dates:
        return 0

    streak = 1
    for i in range(len(dates) - 1):
        d1 = date.fromisoformat(dates[i])
        d2 = date.fromisoformat(dates[i + 1])
        if (d1 - d2).days == 1:
            streak += 1
        else:
            break
    return streak


async def get_activity_correlations(user_id: str):
    pipeline = [
        {"$match": {"user_id": user_id, "activities": {"$ne": []}}},
        {"$unwind": "$activities"},
        {"$group": {
            "_id": "$activities",
            "avg_intensity": {"$avg": "$intensity"},
            "moods": {"$push": "$mood"},
            "count": {"$sum": 1},
            "positive_ratio": {
                "$avg": {"$cond": [{"$eq": ["$category", "positive"]}, 1, 0]}
            },
        }},
        {"$sort": {"count": -1}},
    ]
    cursor = db.moods.aggregate(pipeline)
    return await cursor.to_list(length=50)


async def get_comprehensive_analysis(user_id: str) -> dict:
    """
    Pulls EVERYTHING the AI needs to give deep insights.
    This is what gets fed to the chatbot.
    """
    total = await get_mood_count(user_id)
    if total == 0:
        return {"has_data": False, "message": "No mood data recorded yet."}

    distribution = await get_mood_distribution(user_id)
    hourly = await get_hourly_patterns(user_id)
    weekly = await get_weekly_patterns(user_id)
    trend = await get_monthly_trend(user_id, months=3)
    streak = await get_streak(user_id)
    activities = await get_activity_correlations(user_id)
    recent = await get_recent_moods(user_id, limit=10)

    # Calculate overall sentiment
    pos_count = sum(d["count"] for d in distribution if d["category"] == "positive")
    neg_count = sum(d["count"] for d in distribution if d["category"] == "negative")
    sentiment_ratio = round(pos_count / max(total, 1) * 100, 1)

    # Find peak mood hours
    peak_hours = sorted(hourly, key=lambda x: x["count"], reverse=True)[:3]

    # Worst and best days
    best_day = max(weekly, key=lambda x: x.get("positive_count", 0), default=None)
    worst_day = max(weekly, key=lambda x: x.get("negative_count", 0), default=None)

    # Average intensity overall
    all_moods = await get_recent_moods(user_id, limit=10000)
    avg_int = round(
        sum(m.get("intensity", 5) for m in all_moods) / max(len(all_moods), 1), 1
    )

    # Recent trajectory (last 7 vs previous 7)
    if len(all_moods) >= 14:
        recent_7_int = sum(
            m.get("intensity", 5) for m in all_moods[:7]
        ) / 7
        prev_7_int = sum(
            m.get("intensity", 5) for m in all_moods[7:14]
        ) / 7
        trajectory = "improving" if recent_7_int > prev_7_int else "declining" \
            if recent_7_int < prev_7_int else "stable"
    else:
        trajectory = "not enough data"

    return {
        "has_data": True,
        "total_entries": total,
        "streak_days": streak,
        "sentiment_ratio": sentiment_ratio,
        "avg_intensity": avg_int,
        "trajectory": trajectory,
        "mood_distribution": [
            {
                "mood": d["_id"],
                "emoji": d["emoji"],
                "count": d["count"],
                "avg_intensity": round(d["avg_intensity"], 1),
                "category": d["category"],
            }
            for d in distribution
        ],
        "hourly_patterns": [
            {
                "hour": h["_id"],
                "count": h["count"],
                "avg_intensity": round(h["avg_intensity"], 1),
            }
            for h in hourly
        ],
        "weekly_patterns": [
            {
                "day": w["_id"],
                "count": w["count"],
                "positive": w.get("positive_count", 0),
                "negative": w.get("negative_count", 0),
                "avg_intensity": round(w["avg_intensity"], 1),
            }
            for w in weekly
        ],
        "peak_mood_hours": [h["_id"] for h in peak_hours],
        "best_day": best_day["_id"] if best_day else None,
        "worst_day": worst_day["_id"] if worst_day else None,
        "recent_entries": [
            {
                "mood": m["mood"],
                "emoji": m.get("emoji", "🫠"),
                "intensity": m.get("intensity", 5),
                "note": m.get("note", ""),
                "date": m["date"],
                "time": m.get("time", ""),
                "day": m.get("day_of_week", ""),
                "activities": m.get("activities", []),
                "tags": m.get("tags", []),
            }
            for m in recent
        ],
        "activity_correlations": [
            {
                "activity": a["_id"],
                "times": a["count"],
                "positive_ratio": round(a["positive_ratio"] * 100, 1),
                "avg_intensity": round(a["avg_intensity"], 1),
            }
            for a in activities
        ],
        "daily_trend": [
            {
                "date": t["_id"],
                "avg_intensity": round(t["avg_intensity"], 1),
                "entries": t["count"],
            }
            for t in trend[-30:]  # last 30 days
        ],
    }