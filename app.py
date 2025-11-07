import streamlit as st
from locgenai.model_wrapper import get_response, detect_language, load_seed_data

st.set_page_config(page_title="LocGenAI — Kolkata Assistant", layout="centered")

st.title("🪔 LocGenAI — Local Chatbot for Kolkata & West Bengal")
st.write("Ask about civic services, festivals, education, or transport. Supports English, বাংলা, and Hinglish.")

# Sidebar options
st.sidebar.header("Settings ⚙️")
lang_choice = st.sidebar.selectbox("Language (optional)", ["Auto-detect", "English", "Bengali"])
show_examples = st.sidebar.checkbox("Show example questions", value=True)

if show_examples:
    examples = load_seed_data()
    st.sidebar.write("Try asking:")
    for e in examples:
        st.sidebar.write("- " + e["question"])

# Input box
user_input = st.text_input("💬 Ask a question about Kolkata or West Bengal", "")

if st.button("Send"):
    if not user_input.strip():
        st.warning("Please type a question first.")
    else:
        auto_lang = detect_language(user_input)
        lang = lang_choice if lang_choice != "Auto-detect" else auto_lang

        with st.spinner("Thinking..."):
            resp = get_response(user_input, lang=lang)

        st.subheader("Answer:")
        st.write(resp.get("answer", "Sorry, I couldn’t find an answer."))

        meta = []
        if resp.get("source"):
            meta.append(f"Source: {resp['source']}")
        meta.append(f"Confidence: {resp.get('confidence')}")
        meta.append("Verified: Seed" if resp.get("from_seed") else "Generated: Model/Fallback")
        st.caption(" • ".join(meta))

st.markdown("---")
st.caption("⚠️ LocGenAI provides local information for Kolkata & West Bengal. Always verify important details from official sources.")
