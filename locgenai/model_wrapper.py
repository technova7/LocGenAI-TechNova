# locgenai/model_wrapper.py
# Final Default Wrapper — Gemini + Local fallback

import os
import json
import random
import google.generativeai as genai

# ───────────────────────────────────────────────
# CONFIGURATION
# ───────────────────────────────────────────────

# Load Gemini API key from environment (for Hugging Face Space secret)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
if not GEMINI_API_KEY:
    print("⚠️ GEMINI_API_KEY not found in environment — Gemini may not work.")
else:
    print("✅ GEMINI_API_KEY loaded successfully.")

# Configure Gemini
genai.configure(api_key=GEMINI_API_KEY)

# Model selection
PRIMARY_MODEL = "gemini-2.5-flash-lite"
BACKUP_MODEL = "gemini-2.5-pro"

# Local data file
PACKAGE_ROOT = os.path.dirname(__file__)
SEED_PATH = os.path.join(PACKAGE_ROOT, "seed_qas.json")

# Load local Q&A data
try:
    with open(SEED_PATH, "r", encoding="utf-8") as f:
        SEED_DATA = json.load(f)
        print(f"✅ Loaded {len(SEED_DATA)} seed QAs")
except Exception as e:
    SEED_DATA = []
    print(f"⚠️ Could not load seed_qas.json: {e}")

# ───────────────────────────────────────────────
# LOCAL LOOKUP
# ───────────────────────────────────────────────

def find_local_answer(query: str):
    """Simple substring-based match from local knowledge base."""
    q = query.strip().lower()
    for item in SEED_DATA:
        if q in item["q"].lower() or item["q"].lower() in q:
            return item
    return None

# ───────────────────────────────────────────────
# GEMINI CALL
# ───────────────────────────────────────────────

def _call_gemini(model_name: str, prompt: str):
    """Call Gemini model and return plain text response."""
    try:
        model = genai.GenerativeModel(model_name)
        response = model.generate_content(prompt)
        if hasattr(response, "text") and response.text:
            return response.text.strip()
    except Exception as e:
        print(f"[Gemini Error] {model_name}: {e}")
    return None

# ───────────────────────────────────────────────
# MAIN FUNCTION
# ───────────────────────────────────────────────

def get_response(prompt: str):
    """Return dict with {'answer': str, 'sources': list}"""
    if not prompt or not prompt.strip():
        return {"answer": "Please enter a question.", "sources": []}

    # Step 1: Try local seed knowledge first
    local_match = find_local_answer(prompt)
    if local_match:
        return {
            "answer": local_match["a"],
            "sources": local_match.get("sources", [])
        }

    # Step 2: Add instruction for Benglish style
    instruction = (
        "Reply in Benglish (mix of Bengali and English), friendly tone, "
        "short and natural, relevant to the user's question only."
    )
    final_prompt = f"{instruction}\n\nUser: {prompt}\nAssistant:"

    # Step 3: Try Gemini Flash Lite first
    reply = _call_gemini(PRIMARY_MODEL, final_prompt)
    if not reply:
        # Step 4: Backup model
        reply = _call_gemini(BACKUP_MODEL, final_prompt)

    # Step 5: Fallback if everything fails
    if not reply:
        fallback = random.choice([
            "Sorry re, amar connection ta thik nei, abar try korbe?",
            "Hmm... ektu samasya holo, please try again!",
        ])
        return {"answer": fallback, "sources": []}

    # Step 6: Return final Gemini answer
    return {"answer": reply, "sources": []}
