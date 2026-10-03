import os
from dotenv import load_dotenv
import streamlit as st

load_dotenv()

def get_gemini_api_key() -> str:
    # 1. Streamlit Cloud Secrets
    if hasattr(st, "secrets") and "GEMINI_API_KEY" in st.secrets:
        return st.secrets["GEMINI_API_KEY"]
    
    # 2. Local Environment Variable (.env)
    api_key = os.getenv("GEMINI_API_KEY")
    if api_key:
        return api_key
        
    raise ValueError("GEMINI_API_KEY not found. Add it to .env or Streamlit Secrets.")