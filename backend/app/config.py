import os
from dotenv import load_dotenv

# Load environment variables from backend/.env at import time.
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))


KIMI_API_KEY = os.getenv("KIMI_API_KEY")
KIMI_BASE_URL = os.getenv("KIMI_BASE_URL", "https://api.moonshot.cn/v1")
KIMI_MODEL = os.getenv("KIMI_MODEL", "moonshot-v1-8k")

ASSETS_DIR = os.getenv("ASSETS_DIR", "data/assets")
RENDERER_URL = os.getenv("RENDERER_URL", "http://localhost:8001")
