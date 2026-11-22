import os
from dotenv import load_dotenv

load_dotenv()

MODE = os.getenv("INFERENCE_MODE", "mock").lower()
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
MODEL_ID = os.getenv("MODEL_ID", "openai/gpt-oss-20b")
MODEL_VISION = os.getenv("MODEL_VISION", "qwen/qwen3.8-27b")
MODEL_AUDIO = os.getenv("MODEL_AUDIO", "whisper-large-v3-turbo")
REVIEW_THRESHOLD = float(os.getenv("REVIEW_THRESHOLD", "0.60"))
