import os
import streamlit as st
from dotenv import load_dotenv

# Load local .env if it exists
load_dotenv()

def get_config(key, default=None):
    """
    Get configuration from Streamlit Secrets (Cloud) or Environment Variables (Local)
    """
    # 1. Try Streamlit Secrets First (Recommended for Cloud)
    try:
        if key in st.secrets:
            return st.secrets[key]
    except Exception:
        pass
        
    # 2. Try Environment Variables
    return os.getenv(key, default)

# Prioritize st.secrets and try both 'KIRA' and 'BEN' suffixes for flexibility
SERP_API_KEY = get_config("SERP_API_KEY") or get_config("SERP_API_KEY_KIRA")
OPENAI_API_KEY = get_config("OPENAI_API_KEY")
GMAIL_EMAIL = get_config("GMAIL_EMAIL") or get_config("GMAIL_EMAIL_BEN")
GMAIL_APP_PASSWORD = get_config("GMAIL_APP_PASSWORD") or get_config("GMAIL_APP_PASSWORD_BEN")
RECIPIENT_EMAIL = get_config("RECIPIENT_EMAIL", "benjamin.joffe@sosv.com")