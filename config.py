import os

from dotenv import load_dotenv
import streamlit as st


load_dotenv()


def get_gemini_api_key() -> str:
    # Colab / local environment
    api_key = os.getenv("GEMINI_API_KEY")

    if api_key:
        return api_key

    # Streamlit Cloud
    try:
        api_key = st.secrets["GEMINI_API_KEY"]

        if api_key:
            return api_key

    except Exception:
        pass

    raise ValueError(
        "GEMINI_API_KEY not found. "
        "Add it as an environment variable or Streamlit Secret."
    )
