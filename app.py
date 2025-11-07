import streamlit as st
import os
import time
import re

# --- Streamlit setup ---
st.set_page_config(page_title="LocGenAI — Regional Knowledge & Query Chatbot", layout="centered")
st.markdown("<meta charset='UTF-8'>", unsafe_allow_html=True)

# --- CSS (keeps your dark theme + header glow + chat bubbles) ---
st.markdown("""
<style>
body {
    background: linear-gradient(145deg, #0f2027, #203a43, #2c5364);
    color: #f5f5f5;
    font-family: 'Poppins', sans-serif;
    padding-bottom: 140px;
}
h1 a, h2 a, h3 a { display: none !important; }

.header-container { text-align: center; padding: 8px 0 4px 0; }
.header-title { font-size: 2.3rem; font-weight: 900; background: linear-gradient(90deg, #ffd54f, #ff6e7f, #7dd3fc); -webkit-background-clip: text; color: transparent; letter-spacing: 1px; text-shadow: 0 4px 18px rgba(0,0,0,0.45); animation: glowA 4s ease-in-out infinite; }
@keyframes glowA { 0% { text-shadow: 0 0 20px #ffd54f; } 50% { text-shadow: 0 0 30px #7dd3fc; } 100% { text-shadow: 0 0 20px #ff6e7f; } }
.header-sub { color: #9fe7ff; font-weight: 600; margin-top:6px; text-shadow: 0 2px 8px rgba(79,195,247,0.12); }
.credit-line { color: #ff80ab; font-size: 13px; margin-top:6px; }

/* bubbles */
.bubble { display:block; padding: 12px 16px; margin: 10px 6%; border-radius: 14px; max-width: 88%; white-space: pre-wrap; word-break: break-word; line-height:1.6; box-shadow: 0 4px 18px rgba(0,0,0,0.35); }
.user-bubble { margin-left: 20%; margin-right: 6%; background: linear-gradient(90deg, #ffd54f, #ffb300); color:#111; text-align:right; }
.bot-bubble { margin-left: 6%; margin-right: 20%; background: linear-gradient(180deg, rgba(30,30,30,1), rgba(25,25,25,0.95)); color:#f8f8f8; border:1px solid rgba(79,195,247,0.12); box-shadow: 0 0 10px rgba(79,195,247,0.18); }

/* sidebar */
.sidebar .sidebar-content { background: linear-gradient(180deg, #151c4d, #0d47a1); color: white; }

footer { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

# --- Header ---
st.markdown("""
<div class='header-container'>
  <div class='header-title'>🤖💬🌏 LocGenAI — Regional Knowledge & Query Chatbot ⚡</div>
  <div class='header-sub'>Bridging Generative AI with Local Knowledge Systems</div>
  <div class='credit-line'>🏆 Built by <b>TechNova</b> • for <b>HackNPitch 2025</b></div>
</div>
""", unsafe_allow_html=True)

# --- Sidebar ---
st.sidebar.header("💡 About")
st.sidebar.write("""
LocGenAI connects regional insights with generative AI to make local knowledge accessible, trustworthy, and culturally aware.

🧑‍💻 Built by: TechNova  
🏆 Hackathon: HackNPitch 2025  
🌐 Theme: GenAI for Localized Knowledge Systems
""")
if st.sidebar.button("🧹 Clear Chat"):
    st.session_state.messages = []

# --- Backend import (safe) ---
try:
    from locgenai.model_wrapper import get_response, detect_language
    MODEL_OK = True
except Exception:
    MODEL_OK = False

# --- Chat memory ---
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- Sanitizer that allows a short whitelist of HTML tags for assistant replies ---
ALLOWED_TAGS = ["b", "i", "strong", "em", "br"]

def sanitize_allow_tags(text: str, allowed_tags=ALLOWED_TAGS) -> str:
    """
    Escape all HTML special chars except a tiny whitelist of tags.
    This prevents arbitrary HTML while allowing <b>, <i>, <strong>, <em>, <br>.
    """
    if not isinstance(text, str):
        text = str(text)
    # escape & first
    escaped = text.replace("&", "&amp;")
    # escape < and >
    escaped = escaped.replace("<", "&lt;").replace(">", "&gt;")
    # unescape allowed tags (both open and close)
    for tag in allowed_tags:
        # simple patterns without attributes
        escaped = re.sub(f"&lt;{tag}&gt;", f"<{tag}>", escaped, flags=re.IGNORECASE)
        escaped = re.sub(f"&lt;/{tag}&gt;", f"</{tag}>", escaped, flags=re.IGNORECASE)
    return escaped

# --- Render function using sanitizer ---
def render_messages():
    for msg in st.session_state.messages:
        role = msg.get("role")
        content = msg.get("content", "")
        if role == "user":
            # user content is fully escaped (no allowed tags) to be safe
            safe = content.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br>")
            st.markdown(f"<div class='bubble user-bubble'>🧍 <b>You:</b> {safe}</div>", unsafe_allow_html=True)
        else:
            # assistant content: allow our small set of tags
            safe = sanitize_allow_tags(content)
            safe = safe.replace("\n", "<br>")
            st.markdown(f"<div class='bubble bot-bubble'>🤖 <b>AI:</b> {safe}</div>", unsafe_allow_html=True)

# initial render
render_messages()

# --- Input / typing logic using st.chat_input ---
prompt = st.chat_input("Type your message here...")

if prompt:
    # append user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    render_messages()

    # if model not available, append assistant error (allows bold)
    if not MODEL_OK:
        st.session_state.messages.append({"role": "assistant", "content": "<b>⚠️ Model unavailable.</b> Please check configuration."})
        render_messages()
    else:
        with st.spinner("✨ Thinking..."):
            try:
                model_resp = get_response(prompt)
                full_answer = model_resp.get("answer", "Sorry — I couldn't generate a response.")
            except Exception as e:
                full_answer = f"<b>⚠️ Error:</b> {str(e)}"

        # typing animation: add empty assistant message, then progressively reveal
        st.session_state.messages.append({"role": "assistant", "content": ""})
        render_messages()

        total_len = len(full_answer)
        # tune chunk & delay
        if total_len < 200:
            chunk, delay = 8, 0.015
        elif total_len < 1000:
            chunk, delay = 12, 0.012
        else:
            chunk, delay = 18, 0.01

        for i in range(0, total_len, chunk):
            part = full_answer[: i + chunk]
            st.session_state.messages[-1]["content"] = part
            render_messages()
            time.sleep(delay)

        # ensure full answer stored (with allowed tags preserved)
        st.session_state.messages[-1]["content"] = full_answer
        render_messages()

# --- Footer ---
st.markdown("<hr style='border:1px solid rgba(79,195,247,0.3);'>", unsafe_allow_html=True)
st.markdown("<div style='text-align:center; color:#f8bbd0;'>🌐 Developed by <b>TechNova</b> — HackNPitch 2025</div>", unsafe_allow_html=True)
