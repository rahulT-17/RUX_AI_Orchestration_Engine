import os
from dotenv import load_dotenv

load_dotenv()

LM_STUDIO_URL = os.getenv("LM_STUDIO_URL", "http://127.0.0.1:1234")
PLANNER_MODEL = os.getenv("PLANNER_MODEL", "qwen/qwen3-vl-4b")
CRITIC_MODEL = os.getenv("CRITIC_MODEL", "mistralai/mistral-7b-instruct-v0.3")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")