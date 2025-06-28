"""
TTS Router Provider

Handles standard TTS generation through the TTS Router service.
"""

import json
import base64
import tempfile
import requests
from config import MODEL_MAPPING, TTS_ROUTER_URL, TTS_ROUTER_HEADERS


def predict_router(text, model):
    """
    Generate TTS audio using the TTS Router service.
    
    Args:
        text (str): Text to synthesize
        model (str): Model identifier
        
    Returns:
        str: Path to temporary audio file
        
    Raises:
        ValueError: If model is not found in mapping
        RuntimeError: If TTS generation fails
    """
    if model not in MODEL_MAPPING:
        raise ValueError(f"Model {model} not found in model mapping")

    model_config = MODEL_MAPPING[model]
    
    # Prepare request payload
    payload = {
        "text": text,
        "provider": model_config["provider"],
        "model": model_config["model"],
    }
    
    try:
        # Make request to TTS router
        response = requests.post(
            TTS_ROUTER_URL,
            headers=TTS_ROUTER_HEADERS,
            data=json.dumps(payload),
            timeout=60  # 60 second timeout
        )
        
        response.raise_for_status()
        response_json = response.json()

        # Extract audio data
        audio_data = response_json["audio_data"]  # base64 encoded audio data
        extension = response_json.get("extension", "wav")
        
        # Decode the base64 audio data
        audio_bytes = base64.b64decode(audio_data)

        # Create a temporary file to store the audio data
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{extension}") as temp_file:
            temp_file.write(audio_bytes)
            temp_path = temp_file.name

        return temp_path
        
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"TTS Router request failed: {str(e)}")
    except (KeyError, json.JSONDecodeError) as e:
        raise RuntimeError(f"Invalid response from TTS Router: {str(e)}")
    except Exception as e:
        raise RuntimeError(f"TTS generation failed: {str(e)}") 