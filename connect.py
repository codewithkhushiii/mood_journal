import json
import os

import requests
import urllib3.util.connection as urllib3_cn
from dotenv import load_dotenv

# Your network's IPv6 route to ngrok silently times out, and requests tries
# IPv6 addresses first. Force IPv4 so connections are instant.
urllib3_cn.HAS_IPV6 = False

load_dotenv()

# Free ngrok URLs change every time you restart the Kaggle notebook.
# Put the new one in .env as PUBLIC_URL=https://xxxx.ngrok-free.app
PUBLIC_URL = os.getenv("PUBLIC_URL", "https://0c87-146-148-44-27.ngrok-free.app")
API_KEY = os.environ["API_KEY"]
MODEL = "Qwen/Qwen2.5-7B-Instruct-AWQ"


def stream_chat(messages, temperature=0.7, max_tokens=256):
    """Send a chat request and print tokens as they arrive. Returns the full reply."""
    with requests.post(
        PUBLIC_URL + "/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": MODEL,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        },
        stream=True,
        timeout=(10, 180),  # (connect, wait-between-chunks)
    ) as response:
        if not response.ok:
            raise RuntimeError(f"HTTP {response.status_code}: {response.text[:500]}")

        full_reply = []
        for raw in response.iter_lines():
            if not raw:
                continue
            line = raw.decode("utf-8")
            if not line.startswith("data: "):
                continue
            data = line[len("data: "):]
            if data == "[DONE]":
                break

            chunk = json.loads(data)
            if not chunk.get("choices"):
                continue
            token = chunk["choices"][0]["delta"].get("content")
            if token:
                print(token, end="", flush=True)
                full_reply.append(token)

        print()
        return "".join(full_reply)


if __name__ == "__main__":
    stream_chat(
        [
            {
                "role": "system",
                "content": "You are MoodBot, a supportive, funny and insightful mood-analysis companion.",
            },
            {
                "role": "user",
                "content": (
                    "I've been anxious for three days, "
                    "but exercising yesterday helped. "
                    "Give me a short, personalized response."
                ),
            },
        ]
    )