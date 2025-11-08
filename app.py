import streamlit as st
import time
import re
from urllib.parse import urlparse

# --- Page Config ---
st.set_page_config(page_title="LocGenAI — Regional Knowledge & Query Chatbot", layout="wide")

# --- Try importing your model functions ---
try:
    from locgenai.model_wrapper import get_response, detect_language
    MODEL_OK = True
except Exception:
    MODEL_OK = False

# --- CSS: polished modern UI ---
st.markdown("""
<style>
body {
  background: linear-gradient(160deg,#081229 0%, #0f1b2b 50%, #151a23 100%);
  color: #e6eef6;
  font-family: "Inter", "Poppins", sans-serif;
  padding-bottom: 120px;
}
.header {
  text-align:center;
  margin-top: 8px;
  margin-bottom: 6px;
}
.title {
  font-size: 2rem;
  font-weight: 800;
  background: linear-gradient(90deg, #ffd54f, #ff6e7f, #7dd3fc);
  -webkit-background-clip: text;
  color: transparent;
  letter-spacing: 0.6px;
  text-shadow: 0 6px 18px rgba(0,0,0,0.6);
}
.subtitle { color:#9fe7ff; margin-top:4px; font-weight:600; }

/* chat area */
.block-container { display:flex; flex-direction:column; }
.bubble {
  display:inline-block;
  padding:12px 16px;
  border-radius:14px;
  line-height:1.5;
  word-break: break-word;
  max-width:75%;
  box-shadow: 0 6px 24px rgba(2,8,23,0.6);
  animation: popIn 0.2s ease-out;
  white-space: pre-wrap;
}
@keyframes popIn {
  from { opacity:0; transform:translateY(6px) scale(0.99);}
  to { opacity:1; transform:translateY(0) scale(1);}
}
.user {
  margin-left:auto;
  margin-right:6%;
  text-align:right;
  background:linear-gradient(90deg,#ffd54f,#ffb300);
  color:#111;
  border-top-right-radius:6px;
}
.assistant {
  margin-left:6%;
  margin-right:auto;
  background:linear-gradient(180deg,rgba(20,24,30,0.95),rgba(15,18,22,0.95));
  color:#f4f8fb;
  border:1px solid rgba(125,211,252,0.06);
}
.assist-blue { border-left:4px solid rgba(64,196,255,0.12);}
.assist-pink { border-left:4px solid rgba(255,64,129,0.12);}
.assist-purple { border-left:4px solid rgba(180,150,255,0.10);}
.typing {
  display:inline-block;
  padding:10px 14px;
  margin-left:6%;
  border-radius:14px;
  background:linear-gradient(180deg,#0f1318,#101217);
  border:1px solid rgba(125,211,252,0.06);
  color:#9fe7ff;
}
/* animated dots */
.dots span {
  display:inline-block;
  width:6px; height:6px;
  margin:0 3px;
  background:#9fe7ff;
  border-radius:50%;
  opacity:0.25;
  animation: blink 1.2s infinite;
}
.dots span:nth-child(2){ animation-delay:.15s;}
.dots span:nth-child(3){ animation-delay:.3s;}
@keyframes blink {
  0% { transform:translateY(0); opacity:0.25;}
  50% { transform:translateY(-4px); opacity:1;}
  100% { transform:translateY(0); opacity:0.25;}
}

/* link styling */
.bubble a {
  color:#7dd3fc;
  text-decoration:underline;
}
.bubble a:hover {
  text-decoration:none;
  color:#b3f0ff;
}

/* sidebar */
[data-testid="stSidebar"] .block-container { padding:16px; }
.stButton>button {
  background:linear-gradient(90deg,#7dd3fc,#ff6e7f);
  border:none; color:#012; font-weight:700;
}
footer { visibility:hidden; }
@media(max-width:900px){ .bubble{max-width:86%;}.title{font-size:1.6rem;} }
</style>
""", unsafe_allow_html=True)

# --- Header ---
st.markdown("""
<div class="header">
  <div class="title">🤖✨ LocGenAI — Regional Knowledge & Query Chatbot</div>
  <div class="subtitle">Localized, empathetic, and culturally aware answers</div>
</div>
""", unsafe_allow_html=True)

# --- Sidebar ---
st.sidebar.header("About")
st.sidebar.write("Built by **TechNova** • HackNPitch 2025\n\nLocal knowledge + safe AI responses.")
if st.sidebar.button("🧹 Clear Chat"):
    st.session_state.pop("messages", None)
    st.session_state.pop("assist_count", None)

# --- Session init ---
if "messages" not in st.session_state:
    st.session_state.messages = []
if "typing_lock" not in st.session_state:
    st.session_state.typing_lock = False
if "assist_count" not in st.session_state:
    st.session_state.assist_count = 0

# --- Sanitizer and Safe Linkifier ---
ALLOWED = ["b", "i", "strong", "em", "br"]
URL_REGEX = re.compile(r'(https?://[^\s<>"\']+)', flags=re.IGNORECASE)

def is_safe_url(url: str) -> bool:
    try:
        p = urlparse(url)
        return (p.scheme in ("http","https")) and bool(p.netloc)
    except Exception:
        return False

def sanitize_allow(text: str) -> str:
    if not isinstance(text,str):
        text = str(text)
    esc = text.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")
    for tag in ALLOWED:
        esc = re.sub(f"&lt;{tag}&gt;",f"<{tag}>",esc,flags=re.IGNORECASE)
        esc = re.sub(f"&lt;/{tag}&gt;",f"</{tag}>",esc,flags=re.IGNORECASE)
    return esc

def linkify_safe(text: str) -> str:
    def repl(m):
        url = m.group(0)
        if is_safe_url(url):
            safe_url = url.replace('"', "%22")
            return f'<a href="{safe_url}" target="_blank" rel="noopener noreferrer">{safe_url}</a>'
        return url
    return URL_REGEX.sub(repl, text)

# --- Safe message append ---
def add_message(role, content):
    if st.session_state.messages:
        last = st.session_state.messages[-1]
        if last.get("role")==role and last.get("content")==content:
            return
    st.session_state.messages.append({"role":role,"content":content})

# --- Render Chat ---
chat_container = st.container()
def render_chat():
    chat_container.empty()
    with chat_container:
        for msg in st.session_state.messages:
            role = msg.get("role")
            text = msg.get("content","")
            if role == "user":
                safe = text.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;").replace("\n","<br>")
                st.markdown(f"<div class='bubble user'><b>You:</b> {safe}</div>", unsafe_allow_html=True)
            else:
                idx = st.session_state.messages.index(msg)
                c = (st.session_state.assist_count + idx) % 3
                accent = "assist-blue" if c==0 else ("assist-pink" if c==1 else "assist-purple")
                safe = sanitize_allow(text)
                safe = linkify_safe(safe)
                safe = safe.replace("\n","<br>")
                st.markdown(f"<div class='bubble assistant {accent}'><b>AI:</b> {safe}</div>", unsafe_allow_html=True)

# --- Typing indicator ---
typing_holder = st.empty()
render_chat()

# --- Chat input logic ---
prompt = st.chat_input("Type your message here...")

if prompt:
    add_message("user", prompt)
    render_chat()
    if not MODEL_OK:
        add_message("assistant", "<b>⚠️ Model unavailable.</b> Please check configuration.")
        render_chat()
    else:
        if st.session_state.typing_lock:
            add_message("assistant","Please wait — still generating previous reply...")
            render_chat()
        else:
            st.session_state.typing_lock = True
            typing_holder.markdown("<div class='typing'><span class='dots'><span></span><span></span><span></span></span></div>", unsafe_allow_html=True)
            try:
                resp = get_response(prompt)
                full_answer = resp.get("answer", "Sorry — could not produce a response.")
            except Exception as e:
                full_answer = f"<b>⚠️ Error:</b> {str(e)}"
            typing_holder.empty()

            add_message("assistant", "")
            render_chat()
            total = len(full_answer)
            if total < 200: chunk, delay = 10, 0.016
            elif total < 800: chunk, delay = 16, 0.012
            else: chunk, delay = 24, 0.009

            for i in range(0, total, chunk):
                part = full_answer[: i + chunk]
                if st.session_state.messages and st.session_state.messages[-1]["role"]=="assistant":
                    st.session_state.messages[-1]["content"] = part
                else:
                    add_message("assistant", part)
                render_chat()
                time.sleep(delay)

            st.session_state.messages[-1]["content"] = full_answer
            st.session_state.assist_count += 1
            render_chat()
            st.session_state.typing_lock = False

# --- Footer ---
st.markdown("<hr style='opacity:0.06'/>", unsafe_allow_html=True)
st.markdown("<div style='text-align:center; color:#c9f7ff'>Built by <b>TechNova</b> • HackNPitch 2025</div>", unsafe_allow_html=True)
