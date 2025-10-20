# main.py - FastAPI backend with OpenAI integration and explicit startup logging
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
from dotenv import load_dotenv
import json

# load env file
load_dotenv()
OPENAI_KEY = os.getenv("OPENAI_API_KEY")
MODEL = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")

# Try to import openai only if key present
if OPENAI_KEY:
    try:
        import openai
        openai.api_key = OPENAI_KEY
        openai.api_base = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")

    except Exception as e:
        # If import fails, we'll still run but log below
        openai = None
        print("OpenAI import failed:", e)

app = FastAPI(title="JKSSB Micro-SaaS - Backend (OpenAI)")

# CORS for local dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Print a safe startup message so we know if the key is visible to the app
if OPENAI_KEY and ('openai' in globals() and openai is not None):
    print("OpenAI key configured (backend)")
else:
    print("OpenAI key NOT configured (backend) - using mock responses")

class MCQRequest(BaseModel):
    topic: str
    count: int = 5
    difficulty: str = "medium"
    context: str | None = None
def build_mcq_prompt(topic: str, count: int, difficulty: str, context: str | None):
    """
    Returns (system_message, user_message) pair for generating clean, JKSSB-style MCQs
    that the backend will parse as strict JSON. Keep temperature low (0.2) when calling.
    """
    system = (
        "You are an expert JKSSB exam writer and teacher. Your job: produce clear, factual, "
        "unambiguous multiple-choice questions suitable for competitive exams. "
        "Do NOT invent facts. If you do not know a fact, say so in the explanation. "
        "Always return valid JSON only (no surrounding markdown)."
    )

    user = (
        f"Task: Create exactly {count} multiple-choice questions on the topic: \"{topic}\".\n\n"
        "Requirements for each question object:\n"
        " - id: integer\n"
        " - question: concise, clear question statement (avoid ambiguous pronouns)\n"
        " - options: array of 4 distinct short option texts (A-D). Place the correct option among them.\n"
        " - answer_letter: single uppercase letter 'A'/'B'/'C'/'D' indicating the correct option position\n"
        " - answer: the full text of the correct option\n"
        " - explain: one-line (12-30 words) fact-based explanation referencing the reason for the correct answer\n"
        " - difficulty: one of [easy, medium, hard]\n"
        " - source_note: short phrase saying either 'derived from provided context' OR 'common knowledge'\n"
        " - mnemonic: optional short memory tip (<=12 words) or empty string if none\n\n"
        "Rules:\n"
        " 1) Prefer facts from the provided context. If context is provided, say 'derived from provided context' in source_note.\n"
        " 2) Do NOT hallucinate specific dates/names outside the context. If unsure, keep question conceptual and mark answer explain accordingly.\n"
        " 3) Use straightforward language suitable for JKSSB aspirants.\n"
        " 4) Output MUST be valid JSON with a top-level key \"questions\" whose value is an array of question objects exactly like above.\n\n"
        "Example required output format (must follow exactly):\n"
        '{"questions":[{"id":1,"question":"...","options":["A","B","C","D"],"answer_letter":"B","answer":"...","explain":"...","difficulty":"easy","source_note":"common knowledge","mnemonic":""}]}\n\n'
    )

    if context:
        # prepend context and a short instruction to prefer context facts
        user = f"Context:\n{context}\n\nPlease prioritize facts from the context above.\n\n" + user

    return system, user
# -------------------------
# Important points generator
# -------------------------
def build_points_prompt(topic: str, max_points: int = 8, context: str | None = None):
    system = (
        "You are an expert JKSSB instructor who writes clear, concise study notes for aspirants. "
        "Return only valid JSON. Keep language simple and memorization-focused."
    )

    user = (
        f"Task: Summarize the topic \"{topic}\" into up to {max_points} short bullet points that a JKSSB aspirant can memorize.\n\n"
        "Requirements for each bullet:\n"
        " - Keep it one short sentence (<= 14 words) when possible.\n"
        " - Preserve key facts, names, or numbers if necessary.\n"
        " - Use a short mnemonic (<= 6 words) for the topic if helpful. If none, put empty string.\n\n"
        "Return JSON with top-level key \"points\" whose value is an array of objects:\n"
        '{"points":[{"id":1,"text":"...", "mnemonic":""}, ...]}\n\n'
        "If context is provided, prefer facts from the context and mention 'derived from provided context' in a source_note inside each object where relevant."
    )

    if context:
        user = f"Context:\n{context}\n\n" + user

    return system, user


@app.post("/generate/points")
async def generate_points(req: dict):
    """
    POST /generate/points
    body: { "topic": "Indian Polity", "max_points": 8, "context": null }
    returns: { request_id, status, tokens_used, result: [ {id, text, mnemonic} ] }
    """
    topic = req.get("topic", "")
    max_points = int(req.get("max_points", 8))
    context = req.get("context")

    # If no OpenAI key, return a small mock to let frontend work
    if not OPENAI_KEY or not ('openai' in globals() and openai is not None):
        # simple mock
        mock = [
            {"id": i+1, "text": f"[MOCK] Key point {i+1} about {topic}", "mnemonic": "" }
            for i in range(max(1, min(12, max_points)))
        ]
        return {"request_id": "local-mock-points", "status": "ok", "tokens_used": 0, "result": mock}

    system_msg, user_msg = build_points_prompt(topic, max_points, context)

    try:
        resp = openai.ChatCompletion.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_msg}
            ],
            temperature=0.2,
            max_tokens=450,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OpenAI request failed: {e}")

    text = resp.choices[0].message.get("content", "").strip()
    try:
        parsed = json.loads(text)
        points = parsed.get("points") or parsed.get("result") or parsed
        if isinstance(points, list):
            return {
                "request_id": getattr(resp, "id", "openai-1"),
                "status": "ok",
                "tokens_used": resp.usage.get("total_tokens") if hasattr(resp, "usage") else None,
                "result": points
            }
        # fallback
        return {"request_id": getattr(resp, "id", "openai-1"), "status": "ok", "tokens_used": resp.usage.get("total_tokens") if hasattr(resp, "usage") else None, "result": parsed}
    except json.JSONDecodeError:
        return {
            "request_id": getattr(resp, "id", "openai-1"),
            "status": "parse_error",
            "tokens_used": resp.usage.get("total_tokens") if hasattr(resp, "usage") else None,
            "raw_text": text
        }


@app.get("/")
async def root():
    return {"message": "JKSSB backend with OpenAI is running. POST /generate/mcq"}

@app.post("/generate/mcq")
async def generate_mcq(req: MCQRequest):
    # If no OpenAI key or openai import failed, fallback to mock
    if not OPENAI_KEY or not ('openai' in globals() and openai is not None):
        def make_q(i):
            return {
                "id": i,
                "question": f"[MOCK] What is a key fact about {req.topic}? (mock #{i})",
                "options": ["Option A", "Option B", "Option C", "Option D"],
                "answer": "Option B",
                "explain": f"Because of reason {i} — memorize the key phrase for {req.topic}.",
                "difficulty": req.difficulty
            }
        result = [make_q(i+1) for i in range(max(1, min(20, req.count)))]
        return {"request_id": "local-mock-no-key", "status": "ok", "tokens_used": 0, "result": result}

    # build prompt and call OpenAI
    system_msg, user_msg = build_mcq_prompt(req.topic, req.count, req.difficulty, req.context)

    try:
        resp = openai.ChatCompletion.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_msg}
            ],
            temperature=0.2,
            max_tokens=800,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OpenAI request failed: {e}")

    text = resp.choices[0].message.get("content", "").strip()
    try:
        parsed = json.loads(text)
        questions = parsed.get("questions") or parsed.get("result") or parsed.get("data") or parsed
        if isinstance(questions, dict) and "questions" in questions:
            questions = questions["questions"]
        if isinstance(questions, list):
            return {
                "request_id": getattr(resp, "id", "openai-1"),
                "status": "ok",
                "tokens_used": resp.usage.get("total_tokens") if hasattr(resp, "usage") else None,
                "result": questions
            }
        return {"request_id": getattr(resp, "id", "openai-1"), "status": "ok", "tokens_used": resp.usage.get("total_tokens") if hasattr(resp, "usage") else None, "result": parsed}
    except json.JSONDecodeError:
        return {
            "request_id": getattr(resp, "id", "openai-1"),
            "status": "parse_error",
            "tokens_used": resp.usage.get("total_tokens") if hasattr(resp, "usage") else None,
            "raw_text": text
        }
