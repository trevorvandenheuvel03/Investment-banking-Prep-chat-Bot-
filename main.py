import asyncio
import json
import os
import random
import uuid
from typing import Dict

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import openai

openai.api_key = os.getenv("OPENAI_API_KEY")

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# --- simple in‑code question bank -------------------------------------------
QUESTIONS: Dict[str, Dict[str, list[str]]] = {
    "technical": {
        "easy": [
            "Walk me through the three financial statements.",
            "Define enterprise value.",
        ],
        "medium": [
            "How does a $10 depreciation flow through all three statements?",
            "Why might two companies with identical EBITDA trade at different EV/EBITDA multiples?",
        ],
        "hard": [
            "Explain how to value a company with negative cash flow and no comparables.",
            "Describe a precedent‑transaction analysis step‑by‑step and its pitfalls.",
        ],
    },
    "behavioural": {
        "easy": [
            "Tell me about yourself.",
            "Why investment banking?",
        ],
        "medium": [
            "Describe a time you worked under extreme pressure.",
            "What is your greatest professional failure and what did you learn?",
        ],
        "hard": [
            "Tell me about a time you had to persuade senior stakeholders to change strategy.",
            "Describe a situation where you balanced ethical considerations against profit.",
        ],
    },
}

LEVELS = ["easy", "medium", "hard"]


# --- helpers -----------------------------------------------------------------
def next_level(current: str, up: bool) -> str:
    idx = LEVELS.index(current)
    idx = min(idx + 1, 2) if up else max(idx - 1, 0)
    return LEVELS[idx]


async def score_answer(question: str, answer: str) -> (int, str):
    """
    Uses OpenAI to score the answer 1‑5 and give a brief explanation.
    Returns (score, explanation).
    """
    sys_prompt = (
        "You are an investment‑banking interviewer. "
        "For the candidate answer you will:\n"
        "1. Give a single integer score 1‑5 (5 = excellent).\n"
        "2. Briefly (<=30 words) justify the score.\n"
        "Return JSON like {\"score\":3,\"explanation\":\"…\"}"
    )
    user_msg = f"QUESTION: {question}\nANSWER: {answer}"
    resp = await openai.ChatCompletion.acreate(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": user_msg},
        ],
        max_tokens=60,
    )
    content = resp.choices[0].message.content
    try:
        data = json.loads(content)
        return int(data["score"]), data["explanation"]
    except Exception:
        # fallback if model didn't return JSON
        # look for first digit 1‑5
        digit = next((int(c) for c in content if c in "12345"), 3)
        return digit, content.strip()


def random_question(level: str) -> (str, str):
    category = random.choice(["technical", "behavioural"])
    return category, random.choice(QUESTIONS[category][level])


# --- Web routes --------------------------------------------------------------
@app.get("/", response_class=HTMLResponse)
async def index(request):
    return templates.TemplateResponse("index.html", {"request": request})


# --- WebSocket endpoint ------------------------------------------------------
@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    session_id = str(uuid.uuid4())
    state = {
        "level": "easy",
        "streak_up": 0,
        "streak_down": 0,
        "answered": 0,
        "total_score": 0,
    }

    # Send initial question
    category, q_text = random_question(state["level"])
    await ws.send_json(
        {
            "type": "question",
            "text": q_text,
            "category": category,
            "level": state["level"],
            "time": 120 if state["level"] == "easy" else 90 if state["level"] == "medium" else 60,
            "stats": state,
        }
    )

    try:
        while True:
            data = await ws.receive_json()
            if data.get("type") != "answer":
                continue

            user_answer = data.get("answer", "")
            score, explanation = await score_answer(q_text, user_answer)

            # Update stats
            state["answered"] += 1
            state["total_score"] += score

            if score >= 4:
                state["streak_up"] += 1
                state["streak_down"] = 0
            elif score <= 2:
                state["streak_down"] += 1
                state["streak_up"] = 0
            else:
                state["streak_up"] = state["streak_down"] = 0

            if state["streak_up"] == 2 and state["level"] != "hard":
                state["level"] = next_level(state["level"], up=True)
                state["streak_up"] = 0
            elif state["streak_down"] == 2 and state["level"] != "easy":
                state["level"] = next_level(state["level"], up=False)
                state["streak_down"] = 0

            # Prepare next question
            category, q_text = random_question(state["level"])
            await ws.send_json(
                {
                    "type": "feedback",
                    "score": score,
                    "explanation": explanation,
                    "stats": state,
                }
            )
            await ws.send_json(
                {
                    "type": "question",
                    "text": q_text,
                    "category": category,
                    "level": state["level"],
                    "time": 120 if state["level"] == "easy" else 90 if state["level"] == "medium" else 60,
                    "stats": state,
                }
            )
    except WebSocketDisconnect:
        pass
