import os
import json
from rapidfuzz import fuzz
from dotenv import load_dotenv

# Load .env file (for Gemini key later)
load_dotenv()

# Path to seed data file
SEED_PATH = os.path.join(os.path.dirname(__file__), "data_seed.json")

# Function to load seed data
def load_seed_data():
    with open(SEED_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

# Simple language detection
def detect_language(text):
    for ch in text:
        if '\u0980' <= ch <= '\u09FF':
            return "Bengali"
    # Hinglish detection (basic)
    low = text.lower()
    if any(word in low for word in ["ami", "kibhabe", "kothay", "ache", "korbo"]):
        return "Bengali"
    return "English"

# Fuzzy matching with RapidFuzz
def _closest_seed(user_q):
    seeds = load_seed_data()
    best_score = 0
    best_item = None
    for s in seeds:
        score = fuzz.token_set_ratio(user_q.lower(), s["question"].lower())
        if score > best_score:
            best_score = score
            best_item = s
    return best_item, best_score

# Main function: chatbot logic
def get_response(user_prompt, lang="English"):
    """
    Returns:
      {
        "answer": str,
        "confidence": float,
        "source": optional str,
        "from_seed": bool
      }
    """
    seeds = load_seed_data()
    user_q = user_prompt.strip().lower()

    # 1️⃣ Exact match
    for s in seeds:
        if user_q == s["question"].lower():
            ans = s["answer_bn"] if lang.startswith("Beng") and s.get("answer_bn") else s["answer"]
            return {"answer": ans, "confidence": 0.98, "source": s.get("source","seed"), "from_seed": True}

    # 2️⃣ Fuzzy match (approx)
    best, score = _closest_seed(user_prompt)
    if best and score >= 85:
        ans = best["answer_bn"] if lang.startswith("Beng") and best.get("answer_bn") else best["answer"]
        return {"answer": ans, "confidence": 0.9, "source": best.get("source","seed (fuzzy)"), "from_seed": True}

    # 3️⃣ Fallback if nothing found
    fallback = "I don't have a verified answer for that yet. (This is where Gemini will answer later.)"
    return {"answer": fallback, "confidence": 0.4, "source": None, "from_seed": False}
