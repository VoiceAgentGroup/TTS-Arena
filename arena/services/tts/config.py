"""
TTS Configuration - Model mappings and provider settings.
"""

import os
import random
from dotenv import load_dotenv

load_dotenv()

# Token management for Zero GPU services
ZEROGPU_TOKENS = os.getenv("ZEROGPU_TOKENS", "").split(",")


def get_zerogpu_token():
    """Get a random Zero GPU token for load balancing."""
    return random.choice(ZEROGPU_TOKENS) if ZEROGPU_TOKENS and ZEROGPU_TOKENS[0] else ""


# Model mapping for TTS Router
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
    
    # Commented out models - can be enabled as needed
    # "eleven-multilingual-v2": {
    #     "provider": "elevenlabs",
    #     "model": "eleven_multilingual_v2",
    # },
    # "eleven-turbo-v2.5": {
    #     "provider": "elevenlabs",
    #     "model": "eleven_turbo_v2_5",
    # },
    # "eleven-flash-v2.5": {
    #     "provider": "elevenlabs", 
    #     "model": "eleven_flash_v2_5",
    # },
    # "cartesia-sonic-2": {
    #     "provider": "cartesia",
    #     "model": "sonic-2",
    # },
    # "spark-tts": {
    #     "provider": "spark",
    #     "model": "spark-tts",
    # },
    # "playht-2.0": {
    #     "provider": "playht",
    #     "model": "PlayHT2.0", 
    # },
    # "styletts2": {
    #     "provider": "styletts",
    #     "model": "styletts2",
    # },
    # "kokoro-v1": {
    #     "provider": "kokoro",
    #     "model": "kokoro_v1",
    # },
    # "cosyvoice-2.0": {
    #     "provider": "cosyvoice", 
    #     "model": "cosyvoice_2_0",
    # },
    # "papla-p1": {
    #     "provider": "papla",
    #     "model": "papla_p1",
    # },
    # "hume-octave": {
    #     "provider": "hume",
    #     "model": "octave",
    # },
    # "megatts3": {
    #     "provider": "megatts3",
    #     "model": "megatts3",
    # },
    # "lanternfish-1": {
    #     "provider": "fish",
    #     "model": "s1",
    # },
}

# TTS Router configuration
TTS_ROUTER_URL = "http://b1a19babde7c47e097a30796348d049c.ai-nm-z1-link.lanyun.net:8090/tts"
# Alternative URL: "https://tts-agi-tts-router-v2.hf.space/tts"

TTS_ROUTER_HEADERS = {
    "accept": "application/json",
    "Content-Type": "application/json", 
    "Authorization": f'Bearer {os.getenv("HF_TOKEN")}',
}

# Special models that don't use the TTS router
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