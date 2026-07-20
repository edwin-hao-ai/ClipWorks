import os
from dotenv import load_dotenv

# Load environment variables from backend/.env at import time.
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))


KIMI_API_KEY = os.getenv("KIMI_API_KEY")
KIMI_BASE_URL = os.getenv("KIMI_BASE_URL", "https://api.kimi.com/coding/v1")
KIMI_MODEL = os.getenv("KIMI_MODEL", "moonshot-v1-8k")
# Use a stronger / longer-context model for the planning conversation.
KIMI_PLANNING_MODEL = os.getenv("KIMI_PLANNING_MODEL", "moonshot-v1-32k")
# 自动配图：有 key 走 Pexels 主题搜索，无 key 走 Lorem Picsum 确定性兜底。
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY")

ASSETS_DIR = os.path.abspath(os.getenv("ASSETS_DIR", "data/assets"))
ASSETS_BASE_URL = os.getenv("ASSETS_BASE_URL", "http://localhost:8000")
RENDERER_URL = os.getenv("RENDERER_URL", "http://localhost:8001")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
