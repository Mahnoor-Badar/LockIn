import os

from dotenv import load_dotenv
import streamlit as st


load_dotenv()


def get_gemini_api_key() -> str:
    # First: environment variable
    api_key = os.getenv("GEMINI_API_KEY")

    if api_key:
        return api_key

    # Second: Streamlit Secrets (top level, or inside any section)
    try:
        if "GEMINI_API_KEY" in st.secrets:
            return st.secrets["GEMINI_API_KEY"]

        for name in st.secrets:
            section = st.secrets[name]
            try:
                if "GEMINI_API_KEY" in section:
                    return section["GEMINI_API_KEY"]
            except TypeError:
                pass

    except Exception:
        pass

    raise ValueError(
        "GEMINI_API_KEY not found. "
        "Add it as an environment variable or Streamlit Secret."
    )