"""
TTS Core - Main prediction routing and interface.

This module provides the main predict_tts function that routes requests
to appropriate providers based on the model type.
"""

from .config import SPECIAL_MODELS
from .providers import predict_csm, predict_playdialog, predict_dia, predict_router


def predict_tts(text, model):
    """
    Generate TTS audio using the specified model.
    
    This is the main entry point for TTS generation. It routes requests
    to the appropriate provider based on the model type.
    
    Args:
        text (str or list): Text to synthesize. For conversational models,
                           can be a list of dicts with 'text' and 'speaker_id' keys.
        model (str): Model identifier (e.g., 'minimax-02-hd', 'csm-1b', etc.)
        
    Returns:
        str or bytes: For standard TTS models, returns path to temporary audio file.
                     For conversational models, returns audio content as bytes.
                     
    Raises:
        ValueError: If model is not supported
        RuntimeError: If TTS generation fails
    """
    print(f"Predicting TTS for model: {model}")
    
    # Check if it's a special model that doesn't use the router
    if model in SPECIAL_MODELS:
        provider_type = SPECIAL_MODELS[model]
        
        if provider_type == "csm":
            return predict_csm(text)
        elif provider_type == "playdialog":
            return predict_playdialog(text)
        elif provider_type == "dia":
            return predict_dia(text)
        else:
            raise ValueError(f"Unknown special provider type: {provider_type}")
    
    # For standard TTS models, use the router
    # Note: text should be a string for router-based models
    if isinstance(text, list):
        # Convert list format to string for standard TTS
        text_str = " ".join([item["text"] if isinstance(item, dict) else str(item) for item in text])
    else:
        text_str = str(text)
    
    return predict_router(text_str, model)


# For backward compatibility during testing
if __name__ == "__main__":
    # Test conversational model
    test_script = [
        {"text": "Hello, how are you?", "speaker_id": 0},
        {"text": "I'm great, thank you!", "speaker_id": 1},
    ]
    
    print("Testing Dia model...")
    try:
        result = predict_tts(test_script, "dia-1.6b")
        print(f"Dia result type: {type(result)}")
    except Exception as e:
        print(f"Dia test failed: {e}")
    
    # Test standard TTS model
    print("Testing standard TTS model...")
    try:
        result = predict_tts("Hello world", "minimax-02-hd")
        print(f"Standard TTS result: {result}")
    except Exception as e:
        print(f"Standard TTS test failed: {e}") 