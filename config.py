import os

from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
CHAT_ID = os.getenv("CHAT_ID", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5-mini")
DATABASE_PATH = os.getenv("DATABASE_PATH", "data/spainradar_tax.db")
SCHEDULE_INTERVAL_MINUTES = int(os.getenv("SCHEDULE_INTERVAL_MINUTES", "10"))
LOG_PATH = os.getenv("LOG_PATH", "logs/spainradar_tax.log")
CHANNEL_TIMEZONE = os.getenv("CHANNEL_TIMEZONE", "Europe/Madrid")

# Minimal configuration validation
if not BOT_TOKEN or not CHAT_ID:
    raise EnvironmentError("BOT_TOKEN and CHAT_ID must be defined in the environment")
