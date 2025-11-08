# app.py — LocGenAI: Regional Knowledge & Query Chatbot
# Wire your model: Replace the import with your actual model wrapper
# The wrapper should expose: get_response(user_query: str) -> dict or str

import streamlit as st
import hashlib
import uuid
import json
import re
from urllib.parse import urlparse
from typing import Any

# ═══════════════════════════════════════════════════════════════════════════════
#  PAGE CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

st.set_page_config(
    page_title="LocGenAI - Regional Knowledge & Query Chatbot",
    layout="wide",
    page_icon="🌏",
    initial_sidebar_state="collapsed"
)

# ═══════════════════════════════════════════════════════════════════════════════
#  SAFE MODEL IMPORT
# ═══════════════════════════════════════════════════════════════════════════════

try:
    from locgenai.model_wrapper import get_response
    MODEL_OK = True
    MODEL_ERROR = None
except Exception as e:
    MODEL_OK = False
    MODEL_ERROR = str(e)

# ═══════════════════════════════════════════════════════════════════════════════
#  SESSION STATE
# ═══════════════════════════════════════════════════════════════════════════════

if "messages" not in st.session_state:
    st.session_state.messages = []
if "last_submission_hash" not in st.session_state:
    st.session_state.last_submission_hash = None
if "user_language_style" not in st.session_state:
    st.session_state.user_language_style = None
if "user_input" not in st.session_state:
    st.session_state.user_input = ""
if "preferred_language" not in st.session_state:
    # default preference: Benglish (user asked default to be Benglish)
    st.session_state.preferred_language = "Benglish"

# ═══════════════════════════════════════════════════════════════════════════════
#  UTILITY FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

URL_PATTERN = re.compile(r'(https?://[^\s<>"\'\\)]+)', flags=re.IGNORECASE)


def is_safe_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
        return parsed.scheme in ("http", "https") and bool(parsed.netloc)
    except:
        return False


def sanitize_html(text: Any) -> str:
    if text is None:
        return ""
    s = str(text)
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def linkify_urls(text: str) -> str:
    def replace_url(match):
        url = match.group(0)
        if is_safe_url(url):
            safe_url = url.replace('"', "%22")
            return f'<a href="{safe_url}" target="_blank" rel="noopener noreferrer" class="source-link">{safe_url}</a>'
        return url

    return URL_PATTERN.sub(replace_url, text)


def detect_language_style(text: str) -> str:
    """Detect if text is code-mixed (Benglish/Hinglish), native, or english"""
    if not text:
        return "english"
    has_english = bool(re.search(r'[a-zA-Z]', text))
    has_non_ascii = bool(re.search(r'[^\x00-\x7F]', text))
    if has_english and has_non_ascii:
        return "code-mixed"
    elif has_non_ascii and not has_english:
        return "native"
    return "english"


def extract_text_from_response(response: Any) -> str:
    if response is None:
        return ""
    if isinstance(response, str):
        return response
    if isinstance(response, dict):
        for key in ("answer", "text", "content", "response"):
            if key in response and response[key]:
                return str(response[key])
        if "choices" in response:
            parts = []
            for choice in response.get("choices", []):
                if isinstance(choice, dict):
                    parts.append(choice.get("text") or choice.get("message", {}).get("content", "") or "")
            if parts:
                return " ".join(parts).strip()
        # fallback: pretty-print json
        try:
            return json.dumps(response, indent=2)
        except:
            return str(response)
    try:
        return str(response)
    except:
        return "[Unable to display response]"


def extract_sources(response: Any) -> list:
    if not isinstance(response, dict):
        return []
    sources = []
    for key in ("source", "sources", "references", "urls", "links"):
        if key in response:
            value = response[key]
            if isinstance(value, str) and is_safe_url(value):
                sources.append(value)
            elif isinstance(value, (list, tuple)):
                sources.extend([s for s in value if isinstance(s, str) and is_safe_url(s)])
    # Normalize and unique
    out = []
    seen = set()
    for s in sources:
        if s not in seen:
            seen.add(s)
            out.append(s)
    return out


def make_anchor_prefix(text_raw: str = "") -> str:
    """Create a short stable hash suffix for anchors / ids."""
    if text_raw is None:
        text_raw = ""
    try:
        _hash_digest = hashlib.sha1(text_raw.encode()).hexdigest()[:8]
    except Exception:
        _hash_digest = uuid.uuid4().hex[:8]
    return _hash_digest


# ═══════════════════════════════════════════════════════════════════════════════
#  INSTRUCTION PROMPT
# ═══════════════════════════════════════════════════════════════════════════════

instruction = """You are LocGenAI — a regional knowledge assistant.
- Mirror the user's language style (if they use code-mixed/Benglish, reply in the same style).
- Match the user's emotional tone (empathetic, formal, casual) where appropriate.
- Provide clear, concise answers with helpful local examples or analogies.
- When relevant, include 1-3 trusted source links (government or authoritative pages) with brief labels.
- Do NOT stream or output partial tokens. Return the finished answer in one reply.
- Keep the answer accurate and, when you are uncertain, say you are uncertain and suggest where to verify.
"""

# ═══════════════════════════════════════════════════════════════════════════════
#  CUSTOM CSS (unchanged)
# ═══════════════════════════════════════════════════════════════════════════════

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=Inter:wght@400;500;600;700&family=Outfit:wght@400;500;600;700;800;900&display=swap');

:root {
    --bg-primary: #0D0D0D;
    --bg-secondary: #161616;
    --bg-tertiary: #1C1C1C;
    --bg-elevated: #242424;
    --text-primary: #FFFFFF;
    --text-secondary: #E0E0E0;
    --text-muted: #A0A0A0;
    --text-dim: #707070;
    --accent-primary: #00D9FF;
    --accent-secondary: #FF10F0;
    --accent-success: #00FF88;
    --accent-warning: #FFB800;
    --accent-cyan: #00D9FF;
    --accent-purple: #B388FF;
    --accent-orange: #FF6E40;
    --accent-pink: #FF10F0;
    --user-bubble: linear-gradient(135deg, #00D9FF 0%, #7B2FF7 100%);
    --ai-bubble: #242424;
    --border-subtle: #2A2A2A;
    --border-medium: #3A3A3A;
    --shadow-sm: 0 2px 8px rgba(0, 0, 0, 0.5);
    --shadow-md: 0 4px 16px rgba(0, 0, 0, 0.6);
    --shadow-lg: 0 10px 40px rgba(0, 0, 0, 0.7);
    --shadow-glow-cyan: 0 0 20px rgba(0, 217, 255, 0.3);
    --shadow-glow-pink: 0 0 20px rgba(255, 16, 240, 0.3);
}

* {
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
}

.stApp {
    background: var(--bg-primary);
    background-attachment: fixed;
}

.stApp::before {
    content: '';
    position: fixed;
    top: -50%;
    left: -50%;
    width: 200%;
    height: 200%;
    background: 
        radial-gradient(circle at 20% 30%, rgba(0, 217, 255, 0.08) 0%, transparent 50%),
        radial-gradient(circle at 80% 70%, rgba(255, 16, 240, 0.08) 0%, transparent 50%),
        radial-gradient(circle at 50% 50%, rgba(0, 255, 136, 0.05) 0%, transparent 50%);
    pointer-events: none;
    z-index: 0;
    animation: float 20s ease-in-out infinite;
}

@keyframes float {
    0%, 100% { transform: translate(0, 0) rotate(0deg); }
    33% { transform: translate(30px, -30px) rotate(5deg); }
    66% { transform: translate(-20px, 20px) rotate(-5deg); }
}

/* Aggressively remove ALL Streamlit default elements */
div[data-testid="stToolbar"],
div[data-testid="stDecoration"],
div[data-testid="stStatusWidget"],
#MainMenu,
footer,
header,
.stDeployButton,
.viewerBadge_container__1QSob {
    visibility: hidden !important;
    height: 0 !important;
    max-height: 0 !important;
    margin: 0 !important;
    padding: 0 !important;
    display: none !important;
    position: absolute !important;
}

/* Force remove top spacing */
section[data-testid="stSidebar"] + div,
.main > div:first-child,
.block-container {
    padding-top: 0 !important;
    margin-top: 0 !important;
}

.element-container {
    margin: 0 !important;
}

/* Remove spacing around form and text area */
.stForm {
    border: none !important;
    padding: 0 !important;
    margin: 0 !important;
    background: transparent !important;
}

div[data-baseweb="base-input"],
.stTextArea > div {
    margin: 0 !important;
}

/* Hide all labels */
label {
    display: none !important;
}

/* Remove extra containers */
.stMarkdown {
    margin: 0 !important;
    padding: 0 !important;
}

body, .stApp {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    color: var(--text-primary);
}

.app-header {
    text-align: center;
    padding: 1.5rem 1rem 1rem 1rem;
    margin-bottom: 0.5rem;
    position: relative;
    z-index: 2;
}

.app-title {
    font-family: 'Outfit', sans-serif;
    font-size: 3.5rem;
    font-weight: 900;
    letter-spacing: -0.03em;
    background: linear-gradient(135deg, #00D9FF 0%, #7B2FF7 25%, #FF10F0 50%, #FFB800 75%, #00FF88 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    margin-bottom: 0.5rem;
    line-height: 1.1;
    animation: shimmer 3s ease-in-out infinite;
    background-size: 200% 200%;
    filter: drop-shadow(0 0 30px rgba(0, 217, 255, 0.4));
}

@keyframes shimmer {
    0%, 100% { background-position: 0% 50%; }
    50% { background-position: 100% 50%; }
}

.app-subtitle {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 1.1rem;
    color: var(--text-secondary);
    font-weight: 500;
    letter-spacing: 0.02em;
}

.sidebar-container {
    background: var(--bg-secondary);
    border-radius: 24px;
    padding: 1.75rem;
    border: 1px solid var(--border-medium);
    box-shadow: var(--shadow-lg);
    position: relative;
    z-index: 2;
    transition: all 0.3s ease;
}

.sidebar-container:hover {
    transform: translateY(-2px);
    border-color: var(--accent-cyan);
    box-shadow: var(--shadow-lg), var(--shadow-glow-cyan);
}

.sidebar-title {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 1.2rem;
    font-weight: 700;
    background: linear-gradient(135deg, var(--accent-cyan), var(--accent-purple));
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    margin-bottom: 0.75rem;
    padding-bottom: 0.75rem;
    border-bottom: 1px solid var(--border-medium);
}

.sidebar-content {
    color: var(--text-secondary);
    line-height: 1.7;
    font-size: 0.95rem;
}

.sidebar-content b {
    color: var(--text-primary);
    font-weight: 700;
}

.sidebar-divider {
    height: 1px;
    background: linear-gradient(90deg, transparent, var(--border-medium), transparent);
    margin: 1.25rem 0;
}

.chat-container {
    max-width: 900px;
    margin: 0 auto;
    background: var(--bg-secondary);
    border-radius: 28px;
    padding: 0;
    box-shadow: var(--shadow-lg);
    position: relative;
    z-index: 2;
    border: 1px solid var(--border-medium);
    overflow: hidden;
}

.chat-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 1.5rem 2rem;
    background: linear-gradient(135deg, rgba(0, 217, 255, 0.05) 0%, rgba(255, 16, 240, 0.05) 100%);
    border-bottom: 1px solid var(--border-medium);
}

.chat-title {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 1.5rem;
    font-weight: 700;
    color: var(--text-primary);
    display: flex;
    align-items: center;
    gap: 0.5rem;
}

.status-indicator {
    width: 10px;
    height: 10px;
    background: var(--accent-success);
    border-radius: 50%;
    animation: pulse 2s ease-in-out infinite;
    box-shadow: 0 0 0 0 rgba(0, 255, 136, 0.7);
}

@keyframes pulse {
    0%, 100% { box-shadow: 0 0 0 0 rgba(0, 255, 136, 0.7); }
    50% { box-shadow: 0 0 0 8px rgba(0, 255, 136, 0); }
}

.clear-chat-btn {
    background: linear-gradient(135deg, #FF10F0 0%, #FF6E40 100%);
    color: white;
    border: none;
    border-radius: 16px;
    padding: 0.7rem 1.5rem;
    font-family: 'Space Grotesk', sans-serif;
    font-weight: 700;
    font-size: 0.9rem;
    cursor: pointer;
    transition: all 0.3s ease;
    box-shadow: 0 4px 16px rgba(255, 16, 240, 0.3);
    display: flex;
    align-items: center;
    gap: 0.5rem;
    position: relative;
    overflow: hidden;
}

.clear-chat-btn::before {
    content: '';
    position: absolute;
    top: 0;
    left: -100%;
    width: 100%;
    height: 100%;
    background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.3), transparent);
    transition: left 0.5s ease;
}

.clear-chat-btn:hover::before {
    left: 100%;
}

.clear-chat-btn:hover {
    transform: translateY(-2px) scale(1.05);
    box-shadow: 0 6px 24px rgba(255, 16, 240, 0.5), var(--shadow-glow-pink);
}

.clear-icon {
    font-size: 1.1rem;
    animation: spin-slow 3s linear infinite;
}

@keyframes spin-slow {
    from { transform: rotate(0deg); }
    to { transform: rotate(360deg); }
}

.clear-chat-btn:hover .clear-icon {
    animation: spin-fast 0.5s linear infinite;
}

@keyframes spin-fast {
    from { transform: rotate(0deg); }
    to { transform: rotate(360deg); }
}

.clear-text {
    background: linear-gradient(90deg, #FFFFFF 0%, #00D9FF 50%, #FFFFFF 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    background-size: 200% 100%;
    animation: text-shine 2s ease-in-out infinite;
}

@keyframes text-shine {
    0%, 100% { background-position: 0% 50%; }
    50% { background-position: 100% 50%; }
}

.chat-window {
    min-height: 400px;
    max-height: 65vh;
    overflow-y: auto;
    overflow-x: hidden;
    padding: 1.5rem 2rem;
    background: var(--bg-primary);
    scroll-behavior: smooth;
}

.chat-window::-webkit-scrollbar {
    width: 8px;
}

.chat-window::-webkit-scrollbar-track {
    background: transparent;
}

.chat-window::-webkit-scrollbar-thumb {
    background: linear-gradient(180deg, var(--accent-cyan), var(--accent-pink));
    border-radius: 10px;
}

.chat-window::-webkit-scrollbar-thumb:hover {
    background: linear-gradient(180deg, var(--accent-pink), var(--accent-cyan));
}

.message-list {
    display: flex;
    flex-direction: column;
    gap: 0;
}

.message-wrapper {
    padding: 1.5rem 0;
    border-bottom: 1px solid var(--border-subtle);
}

.message-wrapper:last-child {
    border-bottom: none;
}

.message-wrapper.user {
    background: var(--bg-secondary);
}

.message-wrapper.assistant {
    background: var(--bg-primary);
}

.message-content {
    max-width: 800px;
    margin: 0 auto;
    line-height: 1.7;
    font-size: 0.98rem;
    color: var(--text-primary);
}

.message-wrapper.user .message-content {
    color: var(--text-primary);
}

.message-wrapper.assistant .message-content {
    color: var(--text-secondary);
}

.message-role {
    font-family: 'Space Grotesk', sans-serif;
    font-weight: 700;
    margin-bottom: 0.75rem;
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-size: 0.8rem;
    letter-spacing: 0.5px;
    text-transform: uppercase;
}

.message-wrapper.user .message-role {
    color: var(--accent-cyan);
}

.message-wrapper.assistant .message-role {
    background: linear-gradient(135deg, var(--accent-cyan), var(--accent-purple));
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}

.role-badge {
    font-size: 1rem;
}

.message-meta {
    margin-top: 0.85rem;
    padding-top: 0.85rem;
    border-top: 1px solid var(--border-subtle);
    display: flex;
    gap: 0.75rem;
    align-items: center;
    flex-wrap: wrap;
    font-size: 0.8rem;
    color: var(--text-muted);
}

.copy-button {
    background: rgba(0, 217, 255, 0.15);
    color: var(--accent-cyan);
    border: 1px solid rgba(0, 217, 255, 0.3);
    padding: 0.35rem 0.8rem;
    border-radius: 12px;
    cursor: pointer;
    font-size: 0.7rem;
    font-weight: 700;
    transition: all 0.2s ease;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    font-family: 'Space Grotesk', sans-serif;
}

.copy-button:hover {
    background: rgba(0, 217, 255, 0.25);
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(0, 217, 255, 0.4);
}

.source-link {
    color: var(--accent-cyan);
    text-decoration: none;
    font-weight: 600;
    border-bottom: 1px solid rgba(0, 217, 255, 0.3);
    transition: all 0.2s ease;
}

.source-link:hover {
    color: var(--accent-pink);
    border-bottom-color: var(--accent-pink);
}

.warning-banner {
    background: linear-gradient(135deg, rgba(255, 184, 0, 0.15) 0%, rgba(255, 110, 64, 0.15) 100%);
    border: 1px solid var(--accent-warning);
    border-radius: 20px;
    padding: 1.25rem 1.5rem;
    margin-bottom: 1.5rem;
    color: var(--text-primary);
}

.warning-banner strong {
    color: var(--accent-warning);
    font-weight: 700;
}

.empty-state {
    text-align: center;
    padding: 4rem 2rem;
    color: var(--text-muted);
}

.empty-icon {
    font-size: 4rem;
    margin-bottom: 1.5rem;
    opacity: 0.6;
    animation: float-gentle 3s ease-in-out infinite;
    filter: drop-shadow(0 0 20px rgba(0, 217, 255, 0.3));
}

@keyframes float-gentle {
    0%, 100% { transform: translateY(0px); }
    50% { transform: translateY(-10px); }
}

.empty-text {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 1.15rem;
    font-weight: 600;
    color: var(--text-primary);
}

.empty-subtext {
    font-size: 0.95rem;
    color: var(--text-muted);
    margin-top: 0.5rem;
}

.input-container {
    padding: 1.5rem 2rem 2rem 2rem;
    background: var(--bg-secondary);
    border-top: 1px solid var(--border-medium);
}

.app-footer {
    text-align: center;
    padding: 2.5rem 1rem 2rem;
    color: var(--text-muted);
    font-size: 0.95rem;
    z-index: 2;
    position: relative;
}

.app-footer strong {
    background: linear-gradient(135deg, var(--accent-cyan), var(--accent-purple));
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    font-weight: 700;
}

.footer-emoji {
    font-size: 1.1rem;
    display: inline-block;
    animation: heartbeat 1.5s ease-in-out infinite;
}

@keyframes heartbeat {
    0%, 100% { transform: scale(1); }
    25% { transform: scale(1.2); }
    50% { transform: scale(1); }
}

/* Streamlit Component Overrides */
.stTextArea textarea {
    background-color: var(--bg-tertiary) !important;
    border: 2px solid var(--border-medium) !important;
    border-radius: 20px !important;
    color: var(--text-primary) !important;
    font-size: 1rem !important;
    padding: 1.25rem 4rem 1.25rem 1.25rem !important;
    font-family: 'Inter', sans-serif !important;
    transition: all 0.2s ease !important;
    box-shadow: var(--shadow-sm) !important;
}

.stTextArea textarea:focus {
    border-color: var(--accent-cyan) !important;
    box-shadow: 0 0 0 3px rgba(0, 217, 255, 0.2), var(--shadow-md) !important;
    outline: none !important;
    background-color: var(--bg-elevated) !important;
}

.stTextArea textarea::placeholder {
    color: var(--text-dim) !important;
}

.stButton button {
    background: linear-gradient(135deg, var(--accent-cyan), var(--accent-purple)) !important;
    color: white !important;
    border: none !important;
    border-radius: 50% !important;
    padding: 0 !important;
    font-weight: 700 !important;
    font-size: 1.5rem !important;
    transition: all 0.3s ease !important;
    box-shadow: 0 4px 16px rgba(0, 217, 255, 0.4) !important;
    font-family: 'Space Grotesk', sans-serif !important;
    position: absolute;
    right: 2.5rem;
    bottom: 2.75rem;
    width: 50px;
    height: 50px;
    display: flex;
    align-items: center;
    justify-content: center;
}

.stButton button:hover {
    transform: translateY(-3px) scale(1.1) rotate(45deg) !important;
    box-shadow: 0 6px 24px rgba(0, 217, 255, 0.6), var(--shadow-glow-cyan) !important;
}

.stButton button::before {
    content: "↑";
    font-size: 1.5rem;
    font-weight: 800;
}

.stForm {
    position: relative;
}

/* Hide default button text */
.stButton button > div {
    display: none;
}

@media (max-width: 768px) {
    .app-title { 
        font-size: 2.5rem; 
    }
    
    .chat-container { 
        padding: 0; 
        border-radius: 24px; 
        margin: 0 0.5rem;
    }
    
    .message-bubble { 
        max-width: 88%; 
    }
    
    .chat-window { 
        max-height: 50vh; 
        padding: 1.5rem;
    }
    
    .chat-header {
        padding: 1.25rem 1.5rem;
    }
    
    .input-container {
        padding: 1.25rem 1.5rem 1.5rem 1.5rem;
    }
    
    .stButton button {
        right: 2rem;
        bottom: 2.5rem;
    }
    
    .clear-chat-btn {
        padding: 0.6rem 1rem;
        font-size: 0.8rem;
    }
}
</style>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
#  HEADER
# ═══════════════════════════════════════════════════════════════════════════════

st.markdown("""
<div class="app-header">
    <div class="app-title">🌏✨ LocGenAI-Regional Knowledge & Query Chatbot</div>
    <div class="app-subtitle">Your Regional Knowledge Companion</div>
</div>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
#  LAYOUT
# ═══════════════════════════════════════════════════════════════════════════════

col_sidebar, col_chat = st.columns([1, 2.8])

with col_sidebar:
    st.markdown("""
    <div class="sidebar-container">
        <div class="sidebar-title">📖 About LocGenAI</div>
        <div class="sidebar-content">
            Get answers to region-specific questions with rich cultural context. 
            I understand code-mixed queries and respond in your language style! 🌐
            <br><br><b>Built by TechNova</b><br>HackNPitch 2025
        </div>
        <div class="sidebar-divider"></div>
        <div class="sidebar-title">🧠 Powered By</div>
        <div class="sidebar-content">
            <b>Primary Model:</b> Gemini Flash Lite<br>
            <b>Backup Model:</b> Gemini 2.5 Flash<br>
            <b>Knowledge Base:</b> Regional Seed Data<br>
            <b>Special Feature:</b> Multilingual Support
        </div>
        <div class="sidebar-divider"></div>
        <div class="sidebar-title">💡 Pro Tip</div>
        <div class="sidebar-content">
            Talk to me in any language or mix! I'll match your style naturally. 
            Try Benglish, Hinglish, or any code-mixed format! 🎯
        </div>
    </div>
    """, unsafe_allow_html=True)

with col_chat:
    st.markdown('<div class="chat-container">', unsafe_allow_html=True)

    # Chat Header with Custom Clear Button
    st.markdown("""
    <div class="chat-header">
        <div class="chat-title">
            <span class="status-indicator"></span>
            💬 Chat with LocGenAI
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Custom Clear Chat Button (keeps your custom DOM hack but safe)
    header_col1, header_col2 = st.columns([5, 1])
    with header_col2:
        clear_clicked = st.button("Clear", key="clear_btn_hidden", type="secondary")
        st.markdown("""
        <script>
        // If the default hidden Streamlit button exists, create a styled button next to it.
        (function(){
            try {
                const buttons = window.parent.document.querySelectorAll('button[kind="secondary"]');
                buttons.forEach(btn => {
                    if (btn.textContent.includes('Clear')) {
                        // avoid adding duplicates
                        if (btn.parentElement.querySelector('.clear-chat-btn')) return;
                        const customBtn = document.createElement('button');
                        customBtn.className = 'clear-chat-btn';
                        customBtn.innerHTML = '<span class="clear-icon">🗑️</span><span class="clear-text">Clear Chat</span>';
                        customBtn.onclick = () => btn.click();
                        btn.parentElement.appendChild(customBtn);
                        btn.style.display = 'none';
                    }
                });
            } catch (e) { /* ignore cross-origin if any */ }
        })();
        </script>
        """, unsafe_allow_html=True)

        if clear_clicked:
            st.session_state.messages = []
            st.session_state.last_submission_hash = None
            st.session_state.user_language_style = None
            # clear preferred language? keep as is so user choice persists
            st.session_state.user_input = ""

    # Model Warning
    if not MODEL_OK:
        st.markdown(f"""
        <div class="warning-banner">
            <strong>⚠️ Model Configuration Notice</strong><br>
            The AI model wrapper couldn't be loaded. The interface is fully functional, 
            but AI responses are currently disabled.
            <br><small><b>Technical Details:</b> {sanitize_html(MODEL_ERROR)}</small>
        </div>
        """, unsafe_allow_html=True)

    # Language selector prompt (automatic when opening). The user requested default Benglish.
    # If preferred_language exists, show it; otherwise prompt user to choose.
    lang_display = st.session_state.get("preferred_language", None)
    if not lang_display:
        # show inline chooser
        chosen = st.selectbox("Choose interface language", ["Benglish", "Hinglish", "English"], index=0)
        if st.button("Set language"):
            st.session_state.preferred_language = chosen
            st.experimental_rerun()
    else:
        # small top hint of chosen language with option to change
        st.markdown(f"<div style='padding:0.4rem 0 0.6rem 0; color: #cfcfcf; font-size:0.95rem;'>Chat language: <b>{sanitize_html(lang_display)}</b> · <a id='change-lang' href='#' style='color:#00D9FF;'>Change</a></div>", unsafe_allow_html=True)
        # we can't attach a native click handler easily, so provide a simple selectbox to change
        with st.expander("Change chat language", expanded=False):
            new_lang = st.selectbox("Choose", ["Benglish", "Hinglish", "English"], index=["Benglish","Hinglish","English"].index(lang_display) if lang_display in ["Benglish","Hinglish","English"] else 0)
            if st.button("Apply language"):
                st.session_state.preferred_language = new_lang
                st.experimental_rerun()

    # Chat Window
    st.markdown('<div class="chat-window" id="chatWindow">', unsafe_allow_html=True)
    st.markdown('<div class="message-list">', unsafe_allow_html=True)

    if len(st.session_state.messages) == 0:
        st.markdown("""
        <div class="empty-state">
            <div class="empty-icon">💭</div>
            <div class="empty-text">Start Your Conversation</div>
            <div class="empty-subtext">Ask me anything about your region, culture, or local knowledge!</div>
        </div>
        """, unsafe_allow_html=True)

    for idx, msg in enumerate(st.session_state.messages):
        role = msg.get("role", "user")
        content = msg.get("content", "")
        meta = msg.get("meta", {})
        msg_id = msg.get("id", f"msg-{idx}")

        safe_content = sanitize_html(content).replace("\n", "<br>")
        safe_content = linkify_urls(safe_content)
        anchor_id = f"bubble-{msg_id}"

        if role == "user":
            st.markdown(f"""
            <div class="message-wrapper user" id="{anchor_id}">
                <div class="message-content">
                    <span class="message-role"><span class="role-badge">👤</span> You</span>
                    <div>{safe_content}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            # message meta (copy button + sources)
            meta_html = '<div class="message-meta">'
            # copy button (uses JS and will attempt to copy the bubble content)
            meta_html += f'''
            <button class="copy-button" onclick="
                (function() {{
                    try {{
                        const wrapper = document.getElementById('{anchor_id}');
                        if (!wrapper) return;
                        const contentNode = wrapper.querySelector('.message-content');
                        if (!contentNode) return;
                        // prepare text to copy (strip role header)
                        let text = contentNode.innerText || contentNode.textContent || '';
                        // remove role label 'LOCGENAI' or 'You'
                        text = text.replace(/^\\s*LocGenAI\\s*/, '');
                        text = text.replace(/^\\s*You\\s*/, '');
                        text = text.trim();
                        navigator.clipboard.writeText(text).then(() => {{
                            alert('Copied to clipboard');
                        }});
                    }} catch(e) {{
                        console.error(e);
                    }}
                }})();
            ">Copy</button>
            '''

            sources = extract_sources(meta)
            if sources:
                meta_html += '<span>•</span><span><b>Sources:</b> '
                source_links = []
                for si, src in enumerate(sources[:3], start=1):
                    safe_src = src.replace('"', "%22")
                    source_links.append(f'<a href="{safe_src}" target="_blank" class="source-link">Link {si}</a>')
                meta_html += ", ".join(source_links)
                meta_html += '</span>'
            meta_html += '</div>'

            st.markdown(f"""
            <div class="message-wrapper assistant" id="{anchor_id}">
                <div class="message-content">
                    <span class="message-role"><span class="role-badge">🤖</span> LocGenAI</span>
                    <div>{safe_content}</div>
                    {meta_html}
                </div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown('</div></div>', unsafe_allow_html=True)

    # --------------------------
    # INPUT (text_area + button) - replaced the st.form approach to avoid lag
    # --------------------------

    st.markdown('<div class="input-container">', unsafe_allow_html=True)

    # keep the same look/placeholder and key as before
    user_input_text = st.text_area(
        label="Message",
        placeholder="Type your message here... I understand any language! 🌍",
        key="user_input",
        height=80,
        label_visibility="collapsed"
    )

    send_clicked = st.button("Send", key="send_button")

    # If send is clicked, process immediately — append user message first so it shows in the same run
    if send_clicked and user_input_text and user_input_text.strip():
        text = user_input_text.strip()
        submission_hash = hashlib.sha1((text + str(len(st.session_state.messages))).encode()).hexdigest()
        if submission_hash != st.session_state.last_submission_hash:
            st.session_state.last_submission_hash = submission_hash

            # detect user's language style from input and store
            detected_style = detect_language_style(text)
            st.session_state.user_language_style = detected_style

            # Immediately append user message (so it renders right away)
            st.session_state.messages.append({
                "id": str(uuid.uuid4()),
                "role": "user",
                "content": text,
                "meta": {}
            })

            # Build prompt factoring in user's explicit preferred language (persisted) and detected style
            preferred = st.session_state.get("preferred_language", "Benglish")
            style_note = ""
            # Map chosen preference to style hint
            if preferred == "Benglish":
                style_note = "[Respond in Benglish / code-mixed style matching the user preference and tone.] "
            elif preferred == "Hinglish":
                style_note = "[Respond in Hinglish / code-mixed style matching the user preference and tone.] "
            elif preferred == "English":
                style_note = "[Respond in English.] "

            # Also add a hint to mirror input if detection suggests code-mixed/native explicitly
            if detected_style == "code-mixed":
                style_note = "[Reply in the same code-mixed language style (Benglish/Hinglish) as the user.] " + style_note
            elif detected_style == "native":
                style_note = "[Reply in the same native language/style as the user.] " + style_note

            # final prompt
            prompt = f"{instruction}\n{style_note}\nUser: {text}\n\nAnswer:"

            # Call model
            if MODEL_OK:
                try:
                    response = get_response(prompt)
                    ai_content = extract_text_from_response(response)
                    sources = extract_sources(response) if isinstance(response, dict) else []

                    st.session_state.messages.append({
                        "id": str(uuid.uuid4()),
                        "role": "assistant",
                        "content": ai_content,
                        "meta": {"sources": sources} if sources else {}
                    })
                except Exception as e:
                    st.session_state.messages.append({
                        "id": str(uuid.uuid4()),
                        "role": "assistant",
                        "content": f"⚠️ Oops! Something went wrong while generating the answer: {str(e)}",
                        "meta": {}
                    })
            else:
                st.session_state.messages.append({
                    "id": str(uuid.uuid4()),
                    "role": "assistant",
                    "content": "⚠️ The AI model is currently not configured. Please check the setup!",
                    "meta": {}
                })

            # Clear the input after appending messages so no one-step lag happens
            try:
                st.session_state["user_input"] = ""
            except Exception:
                pass

    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# Footer
st.markdown("""
<div class="app-footer">
    Built with <span class="footer-emoji">❤️</span> by <strong>TechNova</strong> • HackNPitch 2025<br>
    <small>Regional Knowledge at Your Fingertips</small>
</div>
""", unsafe_allow_html=True)

# Auto-scroll script
st.markdown("""
<script>
(function() {
    const scrollToBottom = () => {
        const chat = document.getElementById('chatWindow');
        if (chat) { 
            chat.scrollTop = chat.scrollHeight; 
        }
    };
    
    scrollToBottom();
    
    // Scroll after a short delay to ensure content is rendered
    setTimeout(scrollToBottom, 150);
    setTimeout(scrollToBottom, 300);
    
    // Watch for new messages
    const observer = new MutationObserver(scrollToBottom);
    const chat = document.getElementById('chatWindow');
    if (chat) {
        observer.observe(chat, { childList: true, subtree: true });
    }
})();
</script>
""", unsafe_allow_html=True)
