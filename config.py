import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
LLM_API_KEY = os.getenv("LLM_API_KEY")
LLM_BASE_URL = os.getenv("LLM_BASE_URL")
LLM_MODEL = os.getenv("LLM_MODEL")
EMBED_MODEL = os.getenv("EMBED_MODEL")

CHUNK_SIZE = 800
CHUNK_OVERLAP = 100
TOP_K = 4
MAX_FILE_MB = 20
TG_MESSAGE_LIMIT = 4096
