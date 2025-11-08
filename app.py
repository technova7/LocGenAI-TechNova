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
  background: linear-gradient(16
