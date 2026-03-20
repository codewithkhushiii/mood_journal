"""
MOODBOARD v3.0 — FastAPI Backend
MongoDB + AI-Powered Mood Analysis
"""

import os
from datetime import datetime
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException, Request, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from database import (
    connect_db, close_db, add_mood_entry, get_recent_moods,
    get_mood_count, delete_all_moods, get_mood_distribution,
    get_streak, get_comprehensive_analysis, get_hourly_patterns,
    get_weekly_patterns, get_monthly_trend, get_activity_correlations,
    MOOD_EMOJIS, MOOD_CATEGORIES,
)
from agent_tools import chat_with_agent


# ─── Lifespan ─────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_db()
    print("🚀 MOODBOARD v3.0 is live!")
    yield
    await close_db()


# ─── App Setup ────────────────────────────────────────────────
app = FastAPI(
    title="MOODBOARD v3.0",
    description="Track vibes. Analyze patterns. Chat with AI.",
    version="3.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

os.makedirs("static", exist_ok=True)
os.makedirs("templates", exist_ok=True)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

DEFAULT_USER = "default_user"


# ─── Pydantic Models ─────────────────────────────────────────
class MoodEntry(BaseModel):
    mood: str
    note: str = ""
    intensity: int = 5
    tags: list[str] = []
    activities: list[str] = []
    user_id: str = DEFAULT_USER


class ChatRequest(BaseModel):
    message: str
    thread_id: str = "default"
    user_id: str = DEFAULT_USER
    include_analysis: bool = True


class ChatResponse(BaseModel):
    reply: str
    thread_id: str


# ─── Page Routes ──────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    entries = await get_recent_moods(DEFAULT_USER, limit=20)
    total = await get_mood_count(DEFAULT_USER)
    return templates.TemplateResponse("index.html", {
        "request": request,
        "entries": entries,
        "total_entries": total,
        "mood_emojis": MOOD_EMOJIS,
    })


# ─── Mood API ────────────────────────────────────────────────
@app.post("/api/mood")
async def api_add_mood(entry: MoodEntry):
    result = await add_mood_entry(
        user_id=entry.user_id,
        mood=entry.mood,
        note=entry.note,
        intensity=entry.intensity,
        tags=entry.tags,
        activities=entry.activities,
    )
    return {"status": "saved", "entry": result}


@app.get("/api/moods")
async def api_get_moods(user_id: str = DEFAULT_USER, limit: int = 50):
    entries = await get_recent_moods(user_id, limit)
    total = await get_mood_count(user_id)
    return {"entries": entries, "total": total}


@app.delete("/api/moods")
async def api_delete_moods(user_id: str = DEFAULT_USER):
    count = await delete_all_moods(user_id)
    return {"status": "cleared", "deleted": count}


# ─── Analytics API ────────────────────────────────────────────
@app.get("/api/stats")
async def api_stats(user_id: str = DEFAULT_USER):
    total = await get_mood_count(user_id)
    if total == 0:
        return {"has_data": False, "message": "No mood data yet."}

    distribution = await get_mood_distribution(user_id)
    streak = await get_streak(user_id)
    recent = await get_recent_moods(user_id, limit=10000)

    # Compute stats
    avg_intensity = round(
        sum(m.get("intensity", 5) for m in recent) / max(len(recent), 1), 1
    )

    top_mood = distribution[0] if distribution else None

    # Positive ratio
    pos = sum(d["count"] for d in distribution if d["category"] == "positive")
    sentiment = round(pos / max(total, 1) * 100, 1)

    # Recent trend
    recent_7 = recent[:7]
    pos_recent = sum(
        1 for m in recent_7 if m.get("category") == "positive"
    )
    if pos_recent >= 5:
        trend = "📈 Vibes are immaculate lately!"
        trend_type = "positive"
    elif pos_recent >= 3:
        trend = "📊 Mixed bag — riding the waves."
        trend_type = "mixed"
    else:
        trend = "📉 Rough patch — but awareness is the first step."
        trend_type = "rough"

    return {
        "has_data": True,
        "total_entries": total,
        "streak_days": streak,
        "avg_intensity": avg_intensity,
        "sentiment_ratio": sentiment,
        "top_mood": {
            "mood": top_mood["_id"],
            "emoji": top_mood["emoji"],
            "count": top_mood["count"],
        } if top_mood else None,
        "distribution": [
            {
                "mood": d["_id"],
                "emoji": d["emoji"],
                "count": d["count"],
                "avg_intensity": round(d["avg_intensity"], 1),
                "category": d["category"],
            }
            for d in distribution
        ],
        "trend": trend,
        "trend_type": trend_type,
    }


@app.get("/api/analytics/hourly")
async def api_hourly(user_id: str = DEFAULT_USER):
    return await get_hourly_patterns(user_id)


@app.get("/api/analytics/weekly")
async def api_weekly(user_id: str = DEFAULT_USER):
    return await get_weekly_patterns(user_id)


@app.get("/api/analytics/trend")
async def api_trend(user_id: str = DEFAULT_USER, months: int = 3):
    return await get_monthly_trend(user_id, months)


@app.get("/api/analytics/activities")
async def api_activities(user_id: str = DEFAULT_USER):
    return await get_activity_correlations(user_id)


@app.get("/api/analytics/full")
async def api_full_analysis(user_id: str = DEFAULT_USER):
    return await get_comprehensive_analysis(user_id)


# ─── Chat API ────────────────────────────────────────────────
@app.post("/api/chat", response_model=ChatResponse)
async def api_chat(req: ChatRequest):
    try:
        # Pull full analysis from MongoDB for AI context
        mood_context = None
        if req.include_analysis:
            mood_context = await get_comprehensive_analysis(req.user_id)

        reply = await chat_with_agent(
            message=req.message,
            thread_id=req.thread_id,
            mood_context=mood_context,
        )

        return ChatResponse(reply=reply, thread_id=req.thread_id)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─── Health ───────────────────────────────────────────────────
@app.get("/api/health")
async def health():
    total = await get_mood_count(DEFAULT_USER)
    return {
        "status": "cooking 🍳",
        "version": "3.0.0",
        "mood_entries": total,
        "database": "MongoDB",
        "ai": "Groq LLaMA 4",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)