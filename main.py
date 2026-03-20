import os
import json
from datetime import date, datetime
from collections import Counter
from dataclasses import dataclass
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from dotenv import load_dotenv

from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from langchain.messages import HumanMessage
from langgraph.checkpoint.memory import InMemorySaver

load_dotenv()

# ─── Data Layer ───────────────────────────────────────────────
DATA_FILE = "mood_data.json"

MOOD_EMOJIS = {
    "happy": "😊",
    "sad": "😢",
    "angry": "😤",
    "anxious": "😰",
    "excited": "🤩",
    "calm": "😌",
    "tired": "😴",
    "loved": "🥰",
    "confused": "😵‍💫",
    "productive": "💪",
    "creative": "🎨",
    "grateful": "🙏",
}

def load_data() -> list:
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return []

def save_data(data: list):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

# ─── Agent Setup ──────────────────────────────────────────────
checkpointer = InMemorySaver()

model = init_chat_model(
    "meta-llama/llama-4-scout-17b-16e-instruct",
    model_provider="groq",
    temperature=0.7,
)

SYSTEM_PROMPT = """
**Role:** You are an AI mood buddy — high-key helpful, low-key hilarious.
You help users understand their moods, give advice, and keep the vibes immaculate.

**Voice & Tone:**
* Charismatic, quick-witted, and sharp. You speak internet fluently.
* Use modern slang (bet, valid, real, cooking, based, rent-free, gas) only when natural.
* If they ask something great, tell them they're *cooking*.
* If something's off, give a playful side-eye.

**Mood Expertise:**
* You have deep knowledge of emotional intelligence, psychology, and wellness.
* When users share their mood, validate it, give context, and suggest micro-actions.
* You can analyze mood patterns if given data.
* You're like a therapist who also has a fire meme collection.

**Core Rules:**
1. Cut the fluff — get to it but keep personality maxed.
2. No cringe corporate humor.
3. Be a peer who knows everything, not a textbook on TikTok.
4. Light roasts are acceptable. Heavy emotional support also available.
5. Always end responses encouraging the user to keep tracking their moods.
"""

@dataclass
class Context:
    user_id: str

agent = create_agent(
    model=model,
    checkpointer=checkpointer,
    system_prompt=SYSTEM_PROMPT,
    context_schema=Context,
)

# ─── FastAPI App ──────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 Mood Tracker + AI Agent is live and cooking!")
    yield
    print("👋 Shutting down...")

app = FastAPI(
    title="Mood Tracker + AI Chatbot",
    description="Track your vibes. Chat with AI. Stay based.",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# ─── Pydantic Models ─────────────────────────────────────────
class ChatRequest(BaseModel):
    message: str
    thread_id: str = "default"
    user_id: str = "user_1"
    include_mood_context: bool = True

class ChatResponse(BaseModel):
    reply: str
    thread_id: str

class MoodEntry(BaseModel):
    mood: str
    note: str = ""
    intensity: int = 5  # 1-10 scale

class MoodStats(BaseModel):
    total_entries: int
    most_frequent_mood: str
    most_frequent_count: int
    mood_distribution: dict
    streak_days: int
    avg_intensity: float
    recent_trend: str

# ─── Page Routes ──────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    data = load_data()
    recent = data[-20:][::-1]  # last 20, reversed (newest first)
    return templates.TemplateResponse("index.html", {
        "request": request,
        "entries": recent,
        "mood_emojis": MOOD_EMOJIS,
        "total_entries": len(data),
    })

# ─── Mood API Routes ─────────────────────────────────────────
@app.post("/api/mood")
async def add_mood(entry: MoodEntry):
    data = load_data()
    new_entry = {
        "date": date.today().isoformat(),
        "time": datetime.now().strftime("%H:%M"),
        "mood": entry.mood.lower(),
        "note": entry.note,
        "intensity": max(1, min(10, entry.intensity)),
        "emoji": MOOD_EMOJIS.get(entry.mood.lower(), "🫠"),
    }
    data.append(new_entry)
    save_data(data)
    return {"status": "saved", "entry": new_entry}

@app.post("/mood/form")
async def add_mood_form(
    mood: str = Form(...),
    note: str = Form(""),
    intensity: int = Form(5),
):
    data = load_data()
    new_entry = {
        "date": date.today().isoformat(),
        "time": datetime.now().strftime("%H:%M"),
        "mood": mood.lower(),
        "note": note,
        "intensity": max(1, min(10, intensity)),
        "emoji": MOOD_EMOJIS.get(mood.lower(), "🫠"),
    }
    data.append(new_entry)
    save_data(data)
    return RedirectResponse(url="/", status_code=303)

@app.get("/api/moods")
async def get_moods(limit: int = 50):
    data = load_data()
    return {"entries": data[-limit:][::-1], "total": len(data)}

@app.get("/api/stats")
async def get_stats():
    data = load_data()
    if not data:
        return {"message": "No data yet. Start tracking your vibes!"}

    moods = [e["mood"] for e in data]
    counter = Counter(moods)
    most_common = counter.most_common(1)[0]

    # Calculate streak
    dates = sorted(set(e["date"] for e in data), reverse=True)
    streak = 1
    for i in range(len(dates) - 1):
        d1 = date.fromisoformat(dates[i])
        d2 = date.fromisoformat(dates[i + 1])
        if (d1 - d2).days == 1:
            streak += 1
        else:
            break

    # Average intensity
    intensities = [e.get("intensity", 5) for e in data]
    avg_intensity = round(sum(intensities) / len(intensities), 1)

    # Recent trend (last 7 entries)
    recent = data[-7:]
    recent_moods = [e["mood"] for e in recent]
    positive = {"happy", "excited", "calm", "loved", "productive", "creative", "grateful"}
    pos_count = sum(1 for m in recent_moods if m in positive)
    if pos_count >= 5:
        trend = "📈 Vibes are immaculate lately!"
    elif pos_count >= 3:
        trend = "📊 Mixed bag — keeping it balanced."
    else:
        trend = "📉 Rough patch — hang in there, it gets better."

    return MoodStats(
        total_entries=len(data),
        most_frequent_mood=f"{MOOD_EMOJIS.get(most_common[0], '')} {most_common[0]}",
        most_frequent_count=most_common[1],
        mood_distribution={k: v for k, v in counter.most_common()},
        streak_days=streak,
        avg_intensity=avg_intensity,
        recent_trend=trend,
    )

@app.delete("/api/moods")
async def clear_moods():
    save_data([])
    return {"status": "cleared", "message": "Fresh start unlocked 🔓"}

# ─── Chat API Routes ─────────────────────────────────────────
@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(req: ChatRequest):
    try:
        # Optionally inject mood context
        message_content = req.message
        if req.include_mood_context:
            data = load_data()
            if data:
                recent = data[-5:]
                mood_summary = ", ".join(
                    [f"{e['emoji']} {e['mood']}({e.get('intensity',5)}/10) on {e['date']}" for e in recent]
                )
                message_content = (
                    f"[MOOD CONTEXT — User's recent moods: {mood_summary}]\n\n"
                    f"User message: {req.message}"
                )

        config = {"configurable": {"thread_id": req.thread_id}}
        question = HumanMessage(content=message_content)

        response = agent.invoke(
            {"messages": [question]},
            config=config,
            context=Context(user_id=req.user_id),
        )

        ai_reply = response["messages"][-1].content
        return ChatResponse(reply=ai_reply, thread_id=req.thread_id)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/health")
async def health():
    return {
        "status": "cooking 🍳",
        "mood_entries": len(load_data()),
        "agent": "online",
    }

# ─── Run ──────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    os.makedirs("static", exist_ok=True)
    os.makedirs("templates", exist_ok=True)
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)