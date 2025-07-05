import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
import random
import tempfile

# Get current date info
year = datetime.now().year
month = datetime.now().month

load_dotenv()

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

MODEL_MAPPING = {
    # Currently active models
    "minimax-02-hd": {
        "provider": "minimax",
        "model": "speech-02-hd",
    },
    "seed-tts": {
        "provider": "seed-tts", 
        "model": "zh_male_M392_conversation_wvae_bigtts",
    },
}

TTS_ROUTER_URL = "http://b1a19babde7c47e097a30796348d049c.ai-nm-z1-link.lanyun.net:8090/tts"

TTS_ROUTER_HEADERS = {
    "accept": "application/json",
    "Content-Type": "application/json", 
    "Authorization": f'Bearer {os.getenv("HF_TOKEN")}',
}

SPECIAL_MODELS = {
    "csm-1b": "csm",
    "playdialog-1.0": "playdialog", 
    "dia-1.6b": "dia",
}

# PlayDialog voice configurations
PLAYDIALOG_VOICES = {
    "voice_1": "s3://voice-cloning-zero-shot/baf1ef41-36b6-428c-9bdf-50ba54682bd8/original/manifest.json",
    "voice_2": "s3://voice-cloning-zero-shot/e040bd1b-f190-4bdb-83f0-75ef85b18f84/original/manifest.json",
}

# Token management for Zero GPU services
ZEROGPU_TOKENS = os.getenv("ZEROGPU_TOKENS", "").split(",")

# OpenAI configuration for LLM content generation
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")  # Default to GPT-3.5-turbo for cost efficiency


def get_zerogpu_token():
    """Get a random Zero GPU token for load balancing."""
    return random.choice(ZEROGPU_TOKENS) if ZEROGPU_TOKENS and ZEROGPU_TOKENS[0] else ""


class FlaskConfig:
    """Flask application configuration."""
    
    SECRET_KEY = os.getenv("SECRET_KEY", os.urandom(24))
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URI", "sqlite:///tts_arena.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_SAMESITE = "Lax"
    PERMANENT_SESSION_LIFETIME = timedelta(days=30)


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