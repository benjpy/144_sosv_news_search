import os
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
SERP_API_KEY = os.getenv("SERP_API_KEY_KIRA")
GMAIL_EMAIL = os.getenv("GMAIL_EMAIL_BEN")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD_BEN")
RECIPIENT_EMAIL = "benjamin.joffe@sosv.com"
