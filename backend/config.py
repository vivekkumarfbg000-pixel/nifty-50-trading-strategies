import os

class Config:
    SENDER_EMAIL = os.getenv("SENDER_EMAIL", "")
    SENDER_PASSWORD = os.getenv("SENDER_PASSWORD", "")
    SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

config = Config()
