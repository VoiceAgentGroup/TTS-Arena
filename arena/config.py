import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
from huggingface_hub import hf_hub_download
import tempfile

# Get current date info
year = datetime.now().year
month = datetime.now().month

# Check if running in a Hugging Face Space
IS_SPACES = False
if os.getenv("SPACE_REPO_NAME"):
    print("Running in a Hugging Face Space 🤗")
    IS_SPACES = True

    # Setup database sync for HF Spaces
    if not os.path.exists("instance/tts_arena.db"):
        os.makedirs("instance", exist_ok=True)
        try:
            print("Database not found, downloading from HF dataset...")
            hf_hub_download(
                repo_id="TTS-AGI/database-arena-v2",
                filename="tts_arena.db",
                repo_type="dataset",
                local_dir="instance",
                token=os.getenv("HF_TOKEN"),
            )
            print("Database downloaded successfully ✅")
        except Exception as e:
            print(f"Error downloading database from HF dataset: {str(e)} ⚠️")

# Load environment variables
if not IS_SPACES:
    load_dotenv()  # Only load .env if not running in a Hugging Face Space

# Configuration constants
SMOOTHING_FACTOR_MODEL_SELECTION = 500  # For weighted random model selection
TEMP_AUDIO_DIR = os.path.join(tempfile.gettempdir(), "tts_arena_audio")

# Initial model configurations
TTS_MODELS = [
    {
        "id": "minimax-02-hd",
        "name": "MiniMax Speech-02-HD",
        "is_open": False,
        "model_url": "http://minimax.io/",
    },
    {
        "id": "seed-tts",
        "name": "ByteDance Seed-TTS",
        "is_open": False,
        "model_url": "https://www.volcengine.com/",
    },
    # Add more TTS models here as needed
]

CONVERSATIONAL_MODELS = [
    {
        "id": "minimax-02-hd-conv",  # Different ID to avoid conflicts
        "name": "MiniMax Speech-02-HD (Conversational)",
        "is_open": False,
        "model_url": "http://minimax.io/",
    },
    {
        "id": "seed-tts-conv",  # Different ID to avoid conflicts
        "name": "ByteDance Seed-TTS (Conversational)",
        "is_open": False,
        "model_url": "https://www.volcengine.com/",
    },
    # Add more conversational models here as needed
]

class Config:
    """Flask application configuration."""
    
    SECRET_KEY = os.getenv("SECRET_KEY", os.urandom(24))
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URI", "sqlite:///tts_arena.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_SAMESITE = "None" if IS_SPACES else "Lax"
    PERMANENT_SESSION_LIFETIME = timedelta(days=30)
    
    # Force HTTPS when running in HuggingFace Spaces
    if IS_SPACES:
        PREFERRED_URL_SCHEME = "https"

def get_client_ip():
    """Get the client's IP address, handling proxies and load balancers."""
    from flask import request
    
    # Check for forwarded headers first (common with reverse proxies)
    forwarded_for = request.headers.get('X-Forwarded-For')
    if forwarded_for:
        # X-Forwarded-For can contain multiple IPs, take the first one
        return forwarded_for.split(',')[0].strip()
    elif request.headers.get('X-Real-IP'):
        return request.headers.get('X-Real-IP')
    elif request.headers.get('CF-Connecting-IP'):  # Cloudflare
        return request.headers.get('CF-Connecting-IP')
    else:
        return request.remote_addr 