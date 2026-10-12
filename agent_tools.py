"""
AI Agent setup for mood analysis.
Talks to a self-hosted vLLM server (OpenAI-compatible API) exposed through ngrok.
"""

import json
import os
import re

import httpx
import openai
from dotenv import load_dotenv

from langchain_core.messages import HumanMessage, SystemMessage, trim_messages
from langchain_core.runnables import RunnableConfig
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent

load_dotenv()

# ─── Endpoint config (.env) ───────────────────────────────────
# PUBLIC_URL=https://xxxx.ngrok-free.app   <- changes every time the Kaggle notebook restarts
# API_KEY=...                              <- same key the vLLM server was started with
_base = os.environ["PUBLIC_URL"].rstrip("/")
LLM_BASE_URL = _base if _base.endswith("/v1") else _base + "/v1"
LLM_API_KEY = os.environ["API_KEY"]
LLM_MODEL = os.getenv("LLM_MODEL", "Qwen/Qwen2.5-7B-Instruct-AWQ")

# The vLLM server runs with --max-model-len 8192, so keep the prompt well under that.
MAX_CONTEXT_CHARS = 9000      # ~2-3k tokens of mood data
MAX_HISTORY_MESSAGES = 10     # recent chat turns sent to the model

# ─── HTTP clients ─────────────────────────────────────────────
# local_address="0.0.0.0" forces IPv4. Your network's IPv6 route to ngrok silently
# times out, so this avoids long connection stalls.
_timeout = httpx.Timeout(180.0, connect=10.0)
_sync_http = httpx.Client(
    transport=httpx.HTTPTransport(local_address="0.0.0.0"), timeout=_timeout
)
_async_http = httpx.AsyncClient(
    transport=httpx.AsyncHTTPTransport(local_address="0.0.0.0"), timeout=_timeout
)

# ─── Model Setup ──────────────────────────────────────────────
model = ChatOpenAI(
    base_url=LLM_BASE_URL,
    api_key=LLM_API_KEY,
    model=LLM_MODEL,
    temperature=0.7,
    max_tokens=1024,
    timeout=_timeout,
    max_retries=1,
    http_client=_sync_http,
    http_async_client=_async_http,
    streaming=True
)

checkpointer = MemorySaver()

SYSTEM_PROMPT = """You are **MoodBot** — an AI mood analyst and emotional wellness companion.

## YOUR PERSONALITY
- High-key helpful, low-key hilarious
- You speak internet fluently but never cringe
- Use modern slang naturally: *bet, valid, real, cooking, based, rent-free, gas, no cap*
- You're a therapist who also has fire memes
- Light roasts are acceptable. Heavy emotional support also available.
- Be a peer who knows everything, not a textbook on TikTok

## YOUR CAPABILITIES
You have **FULL ACCESS** to the user's mood database. When mood data is provided in [MOOD_ANALYSIS] blocks, use it deeply:

### Pattern Analysis
- Identify recurring emotional cycles (e.g., "you always crash on Wednesdays")
- Spot intensity trends (improving vs declining)
- Find time-of-day patterns (morning anxiety, evening calm)
- Correlate activities with mood outcomes

### Insights You Should Give
- **Trigger Identification**: What seems to cause negative spirals
- **Strength Spotting**: What consistently makes them feel good
- **Day-of-week Analysis**: Best and worst days with theories why
- **Hourly Patterns**: When they're most/least emotionally stable
- **Trajectory**: Are they trending up or down overall
- **Activity Recommendations**: Based on what correlates with positive moods

### Suggestion Types
1. **Micro-actions**: Small 5-minute things to shift mood RIGHT NOW
2. **Routine Changes**: Based on their patterns (e.g., "your Thursday afternoons are rough — maybe schedule something you enjoy then")
3. **Activity Suggestions**: Based on activity-mood correlations
4. **Mindset Reframes**: Help them see patterns differently
5. **Professional Help**: If you detect persistent negative patterns, gently suggest professional support

## RULES
1. ALWAYS reference specific data points when giving analysis ("you logged anxious 6 times this week")
2. Don't just list stats — interpret them with personality
3. If they're in a rough patch, be supportive first, analytical second
4. End responses encouraging continued tracking
5. Use their actual mood data to make suggestions personalized, not generic
6. If asked about something unrelated to moods, still be helpful but tie it back
7. Keep responses focused and punchy — no walls of text unless they ask for deep analysis
8. Only cite numbers and patterns that are actually in the mood data. If the data doesn't show something, say so instead of guessing
9. SAFETY: if the user mentions self-harm, suicide, or feeling unsafe, drop the jokes and slang completely. Respond warmly and seriously, tell them they deserve real support right now, and encourage them to contact a local crisis line or emergency services, or reach out to someone they trust
"""


def _build_prompt(state, config: RunnableConfig):
    """
    Build the messages sent to the model on every call.

    The system prompt and fresh mood data are added here, so they are never saved
    into the chat history. Otherwise the full mood JSON would pile up on every turn
    and overflow the 8192-token context window.
    """
    system = SYSTEM_PROMPT

    mood_context = (config.get("configurable") or {}).get("mood_context")
    if mood_context and mood_context.get("has_data"):
        data = json.dumps(mood_context, separators=(",", ":"), default=str)
        if len(data) > MAX_CONTEXT_CHARS:
            data = data[:MAX_CONTEXT_CHARS] + "...[truncated]"
        system += (
            "\n\n[MOOD_ANALYSIS — FULL DATABASE ACCESS]\n"
            "Here is the user's mood data from MongoDB:\n"
            f"{data}\n"
            "[END MOOD_ANALYSIS]"
        )

    history = trim_messages(
        state["messages"],
        max_tokens=MAX_HISTORY_MESSAGES,
        token_counter=len,  # count messages, not tokens
        strategy="last",
        start_on="human",
        include_system=False,
    )
    return [SystemMessage(content=system)] + history


def create_mood_agent():
    """Create the mood analysis agent."""
    return create_react_agent(
        model=model,
        tools=[],  # no tools: the vLLM server isn't started with tool calling enabled
        prompt=_build_prompt,
        checkpointer=checkpointer,
    )


# Global agent instance
mood_agent = create_mood_agent()


async def chat_with_agent(
    message: str,
    thread_id: str,
    mood_context: dict = None,
) -> str:
    """Send a message to the agent with optional mood database context."""
    # mood_context goes in as a dict (not a string) so LangGraph doesn't copy it
    # into checkpoint metadata.
    config = {"configurable": {"thread_id": thread_id, "mood_context": mood_context}}

    try:
        response = await mood_agent.ainvoke(
            {"messages": [HumanMessage(content=message)]},
            config=config,
        )
        return response["messages"][-1].content

    except openai.AuthenticationError:
        print("Agent error: API key rejected by the vLLM server")
        return "My brain's locked 🔒 The API key doesn't match the AI server. Check API_KEY in .env."
    except openai.APIConnectionError as e:
        print(f"Agent error: cannot reach LLM server: {e}")
        return (
            "Can't reach my brain right now 😵‍💫 "
            "The AI server looks offline. Is the Kaggle notebook running, "
            "and is PUBLIC_URL in .env the latest ngrok URL?"
        )
    except Exception as e:
        print(f"Agent error: {e}")
        return (
            f"Oof, my brain glitched for a sec 😵‍💫 "
            f"Error: {str(e)[:100]}. Try again?"
        )



# Add this function below your existing chat_with_agent function

async def stream_chat_with_agent(
    message: str,
    thread_id: str,
    mood_context: dict = None,
):
    """Stream response tokens from the agent."""
    config = {"configurable": {"thread_id": thread_id, "mood_context": mood_context}}

    try:
        # astream_events yields events from all runnables inside the graph
        async for event in mood_agent.astream_events(
            {"messages": [HumanMessage(content=message)]},
            config=config,
            version="v2",
        ):
            kind = event["event"]
            # We only care about the tokens coming from the LLM
            if kind == "on_chat_model_stream":
                content = event["data"]["chunk"].content
                if content:
                    yield content

    except openai.AuthenticationError:
        yield "My brain's locked 🔒 The API key doesn't match the AI server. Check API_KEY in .env."
    except openai.APIConnectionError as e:
        yield (
            "Can't reach my brain right now 😵‍💫 "
            "The AI server looks offline. Is the Kaggle notebook running?"
        )
    except Exception as e:
        yield f"\nOof, my brain glitched for a sec 😵‍💫 Error: {str(e)[:100]}. Try again?"

# ─── Music recommendation ─────────────────────────────────────
# vLLM supports OpenAI-style JSON mode, which forces valid JSON output.
_json_model = model.bind(extra_body={"response_format": {"type": "json_object"}})

_MUSIC_FALLBACK = {
    "title": "Weightless",
    "artist": "Marconi Union",
    "reason": "We couldn't generate a personalized recommendation right now, but this track is scientifically proven to reduce anxiety.",
}


def _extract_json(text: str) -> dict:
    """Parse a JSON object from model output, tolerating ``` fences or extra text."""
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            raise
        return json.loads(match.group(0))


async def get_music_recommendation(mood_context: dict) -> dict:
    """Get a personalized music recommendation from the AI based on mood data."""
    prompt = """You are a music recommendation engine. Based on the user's mood data, recommend ONE real song that fits their current vibe or would help them right now.
Respond with a JSON object in exactly this format and nothing else:
{"title": "Song Title", "artist": "Artist Name", "reason": "A short, 1-2 sentence personalized reason based on their data."}

User's mood data:
"""
    if mood_context and mood_context.get("has_data"):
        data = json.dumps(mood_context, separators=(",", ":"), default=str)
        prompt += data[:MAX_CONTEXT_CHARS]
    else:
        prompt += "No mood data available yet. Recommend a generally uplifting song."

    try:
        response = await _json_model.ainvoke([HumanMessage(content=prompt)])
        rec = _extract_json(response.content)
        if not all(rec.get(k) for k in ("title", "artist", "reason")):
            raise ValueError(f"incomplete recommendation: {rec}")
        return {k: str(rec[k]) for k in ("title", "artist", "reason")}
    except Exception as e:
        print(f"Music recommendation error: {e}")
        return _MUSIC_FALLBACK


# ─── Health check ─────────────────────────────────────────────
async def llm_status() -> dict:
    """Quick check that the vLLM server is reachable through the tunnel."""
    try:
        r = await _async_http.get(
            LLM_BASE_URL + "/models",
            headers={"Authorization": f"Bearer {LLM_API_KEY}"},
            timeout=5,
        )
        return {"model": LLM_MODEL, "online": r.status_code == 200}
    except Exception:
        return {"model": LLM_MODEL, "online": False}