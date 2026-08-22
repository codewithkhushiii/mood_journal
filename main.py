"""
MOODBOARD v3.0 — FastAPI Backend
MongoDB + AI-Powered Mood Analysis + Auth
"""

import os
import shutil
import uuid
from datetime import datetime
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException, Request, Form, UploadFile, File, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, EmailStr
from music_recommender import recommend_music

from database import (
    connect_db, close_db, add_mood_entry, get_recent_moods,
    get_mood_count, delete_all_moods, get_mood_distribution,
    get_streak, get_comprehensive_analysis, get_hourly_patterns,
    get_weekly_patterns, get_monthly_trend, get_activity_correlations,
    search_moods, delete_mood_entry,
    create_user, get_user_by_email, get_user_by_username,
    get_user_by_id, update_user_profile,
    MOOD_EMOJIS, MOOD_CATEGORIES,
)
from agent_tools import chat_with_agent, get_music_recommendation
from auth import (
    hash_password, verify_password,
    create_session_token, get_session_user_id,
    COOKIE_NAME, SESSION_MAX_AGE,
)


# ─── Lifespan ─────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_db()
    print("MOODBOARD v3.0 is live!")
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
os.makedirs("static/uploads", exist_ok=True)
os.makedirs("templates", exist_ok=True)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


# ─── Auth Helpers ─────────────────────────────────────────────
async def get_current_user(request: Request):
    """Get the current user from session cookie. Returns user dict or None."""
    user_id = get_session_user_id(request)
    if not user_id:
        return None
    return await get_user_by_id(user_id)


async def require_user(request: Request):
    """Dependency: require authenticated user. Raises 401 if not logged in."""
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


# ─── Pydantic Models ─────────────────────────────────────────
class MoodEntry(BaseModel):
    mood: str
    note: str = ""
    intensity: int = 5
    tags: list[str] = []
    activities: list[str] = []


class ChatRequest(BaseModel):
    message: str
    thread_id: str = "default"
    include_analysis: bool = True


class ChatResponse(BaseModel):
    reply: str
    thread_id: str


class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str
    display_name: str = ""


class LoginRequest(BaseModel):
    email: str
    password: str


class ProfileUpdate(BaseModel):
    display_name: str = ""
    bio: str = ""
    email: str = ""


class DeleteMoodRequest(BaseModel):
    date: str
    time: str
    mood: str


# ─── Page Routes ──────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    user = await get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "user": user,
            "mood_emojis": MOOD_EMOJIS,
        }
    )


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    user = await get_current_user(request)
    if user:
        return RedirectResponse(url="/", status_code=302)
    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={}
    )


# ─── Auth API ────────────────────────────────────────────────
@app.post("/api/auth/register")
async def api_register(req: RegisterRequest):
    # Validate inputs
    if len(req.username) < 3:
        raise HTTPException(400, "Username must be at least 3 characters")
    if len(req.password) < 6:
        raise HTTPException(400, "Password must be at least 6 characters")
    if "@" not in req.email:
        raise HTTPException(400, "Invalid email address")

    # Check for existing users
    existing_email = await get_user_by_email(req.email)
    if existing_email:
        raise HTTPException(400, "Email already registered")

    existing_username = await get_user_by_username(req.username)
    if existing_username:
        raise HTTPException(400, "Username already taken")

    # Create user
    pw_hash = hash_password(req.password)
    user = await create_user(
        username=req.username,
        email=req.email,
        password_hash=pw_hash,
        display_name=req.display_name or req.username,
    )

    # Create session
    token = create_session_token(user["_id"])
    response = JSONResponse({"status": "registered", "user_id": user["_id"]})
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        max_age=SESSION_MAX_AGE,
        httponly=True,
        samesite="lax",
    )
    return response


@app.post("/api/auth/login")
async def api_login(req: LoginRequest):
    user = await get_user_by_email(req.email)
    if not user:
        raise HTTPException(401, "Invalid email or password")

    if not verify_password(req.password, user["password_hash"]):
        raise HTTPException(401, "Invalid email or password")

    token = create_session_token(user["_id"])
    response = JSONResponse({
        "status": "logged_in",
        "user_id": user["_id"],
        "display_name": user.get("display_name", user["username"]),
    })
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        max_age=SESSION_MAX_AGE,
        httponly=True,
        samesite="lax",
    )
    return response


@app.post("/api/auth/logout")
async def api_logout():
    response = JSONResponse({"status": "logged_out"})
    response.delete_cookie(COOKIE_NAME)
    return response


@app.get("/api/auth/me")
async def api_me(request: Request):
    user = await get_current_user(request)
    if not user:
        raise HTTPException(401, "Not authenticated")
    return {
        "user_id": user["_id"],
        "username": user["username"],
        "email": user["email"],
        "display_name": user.get("display_name", user["username"]),
        "bio": user.get("bio", ""),
        "avatar_url": user.get("avatar_url", ""),
        "created_at": str(user.get("created_at", "")),
    }


# ─── Profile API ─────────────────────────────────────────────
@app.get("/api/profile")
async def api_get_profile(request: Request):
    user = await get_current_user(request)
    if not user:
        raise HTTPException(401, "Not authenticated")
    return {
        "user_id": user["_id"],
        "username": user["username"],
        "email": user["email"],
        "display_name": user.get("display_name", user["username"]),
        "bio": user.get("bio", ""),
        "avatar_url": user.get("avatar_url", ""),
        "created_at": str(user.get("created_at", "")),
    }


@app.put("/api/profile")
async def api_update_profile(update: ProfileUpdate, request: Request):
    user = await get_current_user(request)
    if not user:
        raise HTTPException(401, "Not authenticated")

    updates = {}
    if update.display_name:
        updates["display_name"] = update.display_name
    if update.bio is not None:
        updates["bio"] = update.bio
    if update.email:
        updates["email"] = update.email

    updated_user = await update_user_profile(user["_id"], updates)
    return {"status": "updated", "user": {
        "display_name": updated_user.get("display_name"),
        "bio": updated_user.get("bio"),
        "email": updated_user.get("email"),
        "avatar_url": updated_user.get("avatar_url"),
    }}


@app.post("/api/profile/avatar")
async def api_upload_avatar(request: Request, file: UploadFile = File(...)):
    user = await get_current_user(request)
    if not user:
        raise HTTPException(401, "Not authenticated")

    # Validate file type
    allowed_types = {"image/jpeg", "image/png", "image/gif", "image/webp"}
    if file.content_type not in allowed_types:
        raise HTTPException(400, "Invalid file type. Use JPEG, PNG, GIF, or WebP.")

    # Generate unique filename
    ext = file.filename.split(".")[-1] if "." in file.filename else "jpg"
    filename = f"avatar_{user['_id']}_{uuid.uuid4().hex[:8]}.{ext}"
    filepath = os.path.join("static", "uploads", filename)

    # Delete old avatar if exists
    old_avatar = user.get("avatar_url", "")
    if old_avatar:
        old_path = old_avatar.lstrip("/")
        if os.path.exists(old_path):
            try:
                os.remove(old_path)
            except OSError:
                pass

    # Save new file
    with open(filepath, "wb") as f:
        content = await file.read()
        f.write(content)

    avatar_url = f"/static/uploads/{filename}"
    await update_user_profile(user["_id"], {"avatar_url": avatar_url})

    return {"status": "uploaded", "avatar_url": avatar_url}


# ─── Mood API ────────────────────────────────────────────────
@app.post("/api/mood")
async def api_add_mood(entry: MoodEntry, request: Request):
    user = await get_current_user(request)
    if not user:
        raise HTTPException(401, "Not authenticated")

    result = await add_mood_entry(
        user_id=user["_id"],
        mood=entry.mood,
        note=entry.note,
        intensity=entry.intensity,
        tags=entry.tags,
        activities=entry.activities,
    )
    return {"status": "saved", "entry": result}


@app.get("/api/moods")
async def api_get_moods(request: Request, limit: int = 50, skip: int = 0):
    user = await get_current_user(request)
    if not user:
        raise HTTPException(401, "Not authenticated")

    entries = await get_recent_moods(user["_id"], limit, skip)
    total = await get_mood_count(user["_id"])
    return {"entries": entries, "total": total, "limit": limit, "skip": skip}


@app.delete("/api/moods")
async def api_delete_moods(request: Request):
    user = await get_current_user(request)
    if not user:
        raise HTTPException(401, "Not authenticated")

    count = await delete_all_moods(user["_id"])
    return {"status": "cleared", "deleted": count}


@app.post("/api/mood/delete")
async def api_delete_single_mood(req: DeleteMoodRequest, request: Request):
    user = await get_current_user(request)
    if not user:
        raise HTTPException(401, "Not authenticated")

    deleted = await delete_mood_entry(user["_id"], req.date, req.time, req.mood)
    if deleted == 0:
        raise HTTPException(404, "Entry not found")
    return {"status": "deleted"}


@app.get("/api/search")
async def api_search_moods(q: str, request: Request, limit: int = 50):
    user = await get_current_user(request)
    if not user:
        raise HTTPException(401, "Not authenticated")

    entries = await search_moods(user["_id"], q, limit)
    return {"entries": entries, "count": len(entries)}


# ─── Analytics API ────────────────────────────────────────────
@app.get("/api/stats")
async def api_stats(request: Request):
    user = await get_current_user(request)
    if not user:
        raise HTTPException(401, "Not authenticated")

    user_id = user["_id"]
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
async def api_hourly(request: Request):
    user = await get_current_user(request)
    if not user:
        raise HTTPException(401, "Not authenticated")
    return await get_hourly_patterns(user["_id"])


@app.get("/api/analytics/weekly")
async def api_weekly(request: Request):
    user = await get_current_user(request)
    if not user:
        raise HTTPException(401, "Not authenticated")
    return await get_weekly_patterns(user["_id"])


@app.get("/api/analytics/trend")
async def api_trend(request: Request, months: int = 3):
    user = await get_current_user(request)
    if not user:
        raise HTTPException(401, "Not authenticated")
    return await get_monthly_trend(user["_id"], months)


@app.get("/api/analytics/activities")
async def api_activities(request: Request):
    user = await get_current_user(request)
    if not user:
        raise HTTPException(401, "Not authenticated")
    return await get_activity_correlations(user["_id"])


@app.get("/api/analytics/full")
async def api_full_analysis(request: Request):
    user = await get_current_user(request)
    if not user:
        raise HTTPException(401, "Not authenticated")
    return await get_comprehensive_analysis(user["_id"])


# ─── Chat API ────────────────────────────────────────────────
@app.post("/api/chat", response_model=ChatResponse)
async def api_chat(req: ChatRequest, request: Request):
    user = await get_current_user(request)
    if not user:
        raise HTTPException(401, "Not authenticated")

    try:
        mood_context = None
        if req.include_analysis:
            mood_context = await get_comprehensive_analysis(user["_id"])

        reply = await chat_with_agent(
            message=req.message,
            thread_id=req.thread_id,
            mood_context=mood_context,
        )

        return ChatResponse(reply=reply, thread_id=req.thread_id)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/recommendation/music")
async def api_music_recommendation(request: Request):
    user = await get_current_user(request)
    if not user:
        raise HTTPException(401, "Not authenticated")

    try:
        mood_context = await get_comprehensive_analysis(user["_id"])
        rec = await get_music_recommendation(mood_context)
        return rec
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─── Health ───────────────────────────────────────────────────
@app.get("/api/health")
async def health():
    return {
        "status": "cooking 🍳",
        "version": "3.0.0",
        "database": "MongoDB",
        "ai": "Groq LLaMA 4",
    }


# ─── Music Recommendation API ────────────────────────────────
@app.get("/api/music")
async def api_music(request: Request, mood: Optional[str] = None):
    """
    Get music recommendation based on:
    - Direct mood input OR
    - Latest user mood from database
    """
    user = await get_current_user(request)
    if not user:
        raise HTTPException(401, "Not authenticated")

    # If mood not provided → fetch latest mood
    if not mood:
        recent = await get_recent_moods(user["_id"], limit=1)
        if not recent:
            return {"message": "No mood data available"}
        mood = recent[0].get("mood", "calm")

    return recommend_music(mood)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
