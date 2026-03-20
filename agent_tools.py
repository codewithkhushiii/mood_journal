"""
AI Agent setup with full database access for mood analysis.
The agent can query MongoDB and provide deep personalized insights.
"""

import os
import json
from dataclasses import dataclass
from dotenv import load_dotenv

from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent

load_dotenv()

# ─── Model Setup ──────────────────────────────────────────────
model = ChatGroq(
    model="meta-llama/llama-4-scout-17b-16e-instruct",
    api_key=os.getenv("GROQ_API_KEY"),
    temperature=0.7,
    max_tokens=2048,
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
"""


def create_mood_agent():
    """Create the mood analysis agent."""
    agent = create_react_agent(
        model=model,
        tools=[],  # Tools could be added for live DB queries
        checkpointer=checkpointer,
    )
    return agent


# Global agent instance
mood_agent = create_mood_agent()


async def chat_with_agent(
    message: str,
    thread_id: str,
    mood_context: dict = None,
) -> str:
    """
    Send a message to the agent with optional mood database context.
    """
    # Build the full message with mood data context
    full_message = ""

    if mood_context and mood_context.get("has_data"):
        context_json = json.dumps(mood_context, indent=2, default=str)
        full_message += f"""[MOOD_ANALYSIS — FULL DATABASE ACCESS]
Here is the user's complete mood data from MongoDB:

{context_json}

[END MOOD_ANALYSIS]

"""

    full_message += f"User message: {message}"

    config = {"configurable": {"thread_id": thread_id}}

    try:
        response = await mood_agent.ainvoke(
            {
                "messages": [
                    SystemMessage(content=SYSTEM_PROMPT),
                    HumanMessage(content=full_message),
                ]
            },
            config=config,
        )

        ai_reply = response["messages"][-1].content
        return ai_reply

    except Exception as e:
        print(f"Agent error: {e}")
        return (
            f"Oof, my brain glitched for a sec 😵‍💫 "
            f"Error: {str(e)[:100]}. Try again?"
        )