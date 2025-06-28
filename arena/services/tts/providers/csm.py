"""
CSM (Creative Speech Model) Provider

Handles conversational TTS generation using the CSM-1B model.
"""

import fal_client
import requests


def predict_csm(script):
    """
    Generate conversational audio using CSM-1B model.
    
    Args:
        script: List of dictionaries with 'text' and 'speaker_id' keys,
                or a string for single-speaker generation
                
    Returns:
        bytes: Audio content in binary format
    """
    result = fal_client.subscribe(
        "fal-ai/csm-1b",
        arguments={
            "scene": script
        },
        with_logs=True,
    )
    
    # Download and return the audio content
    return requests.get(result["audio"]["url"]).content 