"""
TTS Module - Text-to-Speech Generation Interface

This module provides a unified interface for various TTS providers and models.
It handles routing to different providers based on model selection and provides
a consistent API for TTS generation across the application.

Usage:
    from tts import predict_tts
    
    # Generate TTS audio
    audio_path = predict_tts("Hello world", "minimax-02-hd")
"""

from .core import predict_tts

# Export public API
__all__ = ['predict_tts'] 