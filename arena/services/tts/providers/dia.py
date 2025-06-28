"""
Dia Provider

Handles dialogue generation using the Dia-1.6B model.
"""

import json
import requests
from config import get_zerogpu_token


def predict_dia(script):
    """
    Generate dialogue audio using Dia-1.6B model.
    
    Args:
        script: List of dictionaries with 'text' and 'speaker_id' keys,
                or a formatted string
                
    Returns:
        bytes: Audio content in binary format
    """
    # Convert script to the required format for Dia
    if isinstance(script, list):
        # Convert from list of dictionaries to formatted string
        formatted_text = ""
        for turn in script:
            speaker_id = turn.get("speaker_id", 0)
            speaker_tag = "[S1]" if speaker_id == 0 else "[S2]"
            text = turn.get("text", "").strip().replace("[S1]", "").replace("[S2]", "")
            formatted_text += f"{speaker_tag} {text} "
        text = formatted_text.strip()
    else:
        # If it's already a string, use as is
        text = script
    
    print(f"Dia generation for: {text}")
    
    # Make a POST request to initiate the dialogue generation
    headers = {
        "Authorization": f"Bearer {get_zerogpu_token()}"
    }

    response = requests.post(
        "https://mrfakename-dia-1-6b.hf.space/gradio_api/call/generate_dialogue",
        headers=headers,
        json={"data": [text]},
    )

    # Extract the event ID from the response
    event_id = response.json()["event_id"]

    # Make a streaming request to get the generated dialogue
    stream_url = f"https://mrfakename-dia-1-6b.hf.space/gradio_api/call/generate_dialogue/{event_id}"

    # Use a streaming request to get the audio data
    with requests.get(stream_url, headers=headers, stream=True) as stream_response:
        # Process the streaming response
        for line in stream_response.iter_lines():
            if line:
                if line.startswith(b"data: ") and not line.startswith(b"data: null"):
                    audio_data = line[6:]
                    audio_url = json.loads(audio_data)[0]["url"]
                    return requests.get(audio_url).content
                    
    raise RuntimeError("Failed to generate audio with Dia provider") 