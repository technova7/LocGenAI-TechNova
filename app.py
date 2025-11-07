import streamlit as st
import os

# --- Streamlit page setup ---
st.set_page_config(page_title="LocGenAI — Regional Knowledge & Query Chatbot", layout="centered")
st.markdown("<meta charset='UTF-8'>", unsafe_allow_html=True)

# --- CSS: removed container height limit + preserve whitespace in bubbles ---
st.markdown("""
<style>
body {
    background: linear-gradient(145deg, #0f2027, #203a43, #2c5364);
    color: #f5f5f5;
    font-family: 'Poppins', sans-serif;
}
/* Hide Streamlit's default link icon beside titles */
h1 a, h2 a, h3 a {
    text-decoration: none;
    color: inherit;
    pointer-events: none;
}
h1 {
    color: #ffb300;
    text-align: center;
    font-weight: 900;
    text-shadow: 0 0 15px rgba(255, 179, 0, 0.7), 0 0 25px rgba(255, 140, 0, 0.6);
    letter-spacing: 1px;
    font-size: 2.4em;
    margin-bottom: 0.3em;
}
.subheading {
    text-align: center;
    color: #4fc3f7;
    font-size: 1.1em;
    font-weight: 600;
    margin-bottom: 1em;
    text-shadow: 0 0 10px rgba(79, 195, 247, 0.6);
}
.stButton>button {
    background-color: #ff4081;
    color: white;
    font-weight: bold;
    border-radius: 12px;
    padding: 0.6rem 1.3rem;
    transition: 0.3s;
    border: none;
    box-shadow: 0px 0px 10px rgba(255, 64, 129, 0.6);
}
.stButton>button:hover {
    background-color: #f50057;
    transform: scale(1.05);
}
/* user bubble (right) */
.user-bubble {
    background-color: #ffb300;
    color: #212121;
    border-radius: 15px;
    padding: 10px 15px;
    margin: 8px 0;
    text-align: right;
    box-shadow: 0px 0px 10px rgba(255, 179, 0, 0.3);
    display: block;
    margin-left: 20%;
    max-width: 78%;
    white-space: pre-wrap;
    word-break: break-word;
}
/* bot bubble (left) - big change: allow wrapping and full length */
.bot-bubble {
    background-color: #1e1e1e;
    color: #f8f8f8;
    border-radius: 15px;
    padding: 10px 15px;
    margin: 8px 0;
    text-align: left;
    box-shadow: 0px 0px 10px rgba(79, 195, 247, 0.3);
    display: block;
    margin-right: 20%;
    max-width: 78%;
    white-space: pre-wrap;        /* preserve newlines from the model */
    word-break: break-word;       /* break long words properly */
    line-height: 1.7;
}
/* chat container - removed fixed height so content grows naturally */
.chat-container {
    background-color: #102027;
    padding: 20px;
    border-radius: 12px;
    /* no max-height, allow full vertical growth */
    overflow-y: visible;
    box-shadow: inset 0px 0px 10px rgba(255, 255, 255, 0.03);
}
/* sidebar */
.sidebar .sidebar-content {
    background: linear-gradient(180deg, #1a237e, #0d47a1);
    color: white;
}
/* hide default footer */
footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# --- Header (styled) ---
st.markdown("""
<div style='text-align:center; margin-top:-20px;'>
    <h1>🤖 LocGenAI — Regional Knowledge & Query Chatbot 🌍</h1>
    <p class='subheading'>Bridging Generative AI with Local Knowledge Systems</p>
    <p style='color:#ff80ab; font-size:14px; font-weight:500;'>🏆 Built by <b>TechNova</b> • for <b>HackNPitch 2025</b></p>
</div>
""", unsafe_allow_html=True)

# --- Sidebar info (with TechNova credit) ---
st.sidebar.header("💡 About LocGenAI")
st.sidebar.write(
    """
    LocGenAI is a regional knowledge chatbot that connects local insights with Generative AI for accessible, multilingual, and culturally aware information exchange.
    🧑‍💻 **Built by:** TechNova  
    🏆 **Hackathon:** HackNPitch 2025
    """
)
st.sidebar.caption("Simple • Smart • Scalable")

# --- Import model wrapper safely ---
try:
    from locgenai.model_wrapper import get_response, detect_language
    MODEL_OK = True
except Exception:
    MODEL_OK = False

# --- Chat history in session state ---
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# --- Chat input ---
st.markdown("<h3 style='color:#4fc3f7;'>💬 Start Chatting</h3>", unsafe_allow_html=True)
query = st.text_input("Type your question here...", value="What is the cultural significance of Durga Puja?")

# --- Send handling ---
if st.button("🚀 Send"):
    if not query.strip():
        st.warning("Please type a message first.")
    elif not MODEL_OK:
        st.warning("Model not available. Please check configuration.")
    else:
        with st.spinner("✨ Thinking..."):
            resp = get_response(query)
            answer = resp.get("answer", "Sorry, I couldn’t generate a response.")
        # Append user then bot to history (preserve order)
        st.session_state.chat_history.append(("user", query))
        st.session_state.chat_history.append(("bot", answer))

# --- Render chat history (bubbles will expand fully) ---
st.markdown("<div class='chat-container'>", unsafe_allow_html=True)
for role, text in st.session_state.chat_history:
    # sanitize text minimally and preserve whitespace/newlines
    safe_text = text.replace("<", "&lt;").replace(">", "&gt;")
    if role == "user":
        st.markdown(f"<div style='text-align:right;'><div class='user-bubble'>🧍 You: {safe_text}</div></div>", unsafe_allow_html=True)
    else:
        st.markdown(f"<div style='text-align:left;'><div class='bot-bubble'>🤖 AI: {safe_text}</div></div>", unsafe_allow_html=True)
st.markdown("</div>", unsafe_allow_html=True)

# --- Footer credit ---
st.markdown("<hr style='border:1px solid #4fc3f7;'>", unsafe_allow_html=True)
st.markdown("<p style='text-align:center; color:#f8bbd0;'>🌐 Developed by <b>TechNova</b> — HackNPitch 2025</p>", unsafe_allow_html=True)

