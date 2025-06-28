"""
PlayDialog Provider

Handles multi-speaker conversational TTS using PlayHT's PlayDialog engine.
"""

import os
from pyht import Client as PyhtClient
from pyht.client import TTSOptions
from ..config import PLAYDIALOG_VOICES


def predict_playdialog(script):
    """
    Generate conversational audio using PlayDialog.
    
    Args:
        script: List of dictionaries with 'text' and 'speaker_id' keys,
                or a string with conversation format
                
    Returns:
        bytes: Audio content in binary format
    """
    # Initialize the PyHT client
    user_id = os.getenv("PLAY_USERID")
    api_key = os.getenv("PLAY_SECRETKEY")
    
    if not user_id or not api_key:
        raise RuntimeError("PlayDialog credentials not configured. Set PLAY_USERID and PLAY_SECRETKEY environment variables.")
    
    pyht_client = PyhtClient(
        user_id=user_id,
        api_key=api_key,
    )

    # Convert script format if needed
    if isinstance(script, list):
        # Process script in CSM format (list of dictionaries)
        text = ""
        for turn in script:
            speaker_id = turn.get("speaker_id", 0)
            prefix = "Host 1:" if speaker_id == 0 else "Host 2:"
            text += f"{prefix} {turn['text']}\n"
    else:
        # If it's already a string, use as is
        text = script

    # Set up TTSOptions with predefined voices
    options = TTSOptions(
        voice=PLAYDIALOG_VOICES["voice_1"], 
        voice_2=PLAYDIALOG_VOICES["voice_2"], 
        turn_prefix="Host 1:", 
        turn_prefix_2="Host 2:"
    )

    # Generate audio using PlayDialog
    audio_chunks = []
    for chunk in pyht_client.tts(text, options, voice_engine="PlayDialog"):
        audio_chunks.append(chunk)

    # Combine all chunks into a single audio file
    return b"".join(audio_chunks) 