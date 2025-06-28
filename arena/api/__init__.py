"""
TTS Arena API Module

This module provides a comprehensive API for the TTS Arena application.
It includes endpoints for TTS generation, conversational generation, 
leaderboard management, and user interaction.

API Structure:
- /api/tts/* - TTS generation, audio serving, and voting
- /api/conversational/* - Conversational/podcast generation and voting  
- /api/leaderboard/* - Leaderboard data and analytics
- /api/user/* - User preferences and settings
"""

from flask import Blueprint

# Import all API blueprints - using lazy imports to avoid circular dependencies

# Create main API blueprint
api_bp = Blueprint('api', __name__, url_prefix='/api')

def register_api_blueprints(app):
    """
    Register all API blueprints with the Flask app.
    
    Args:
        app: Flask application instance
    """
    # Register individual API modules - import locally to avoid circular deps
    from .tts import tts_bp
    from .conversational import conversational_bp
    from .leaderboard import leaderboard_bp
    
    app.register_blueprint(tts_bp)
    app.register_blueprint(conversational_bp) 
    app.register_blueprint(leaderboard_bp)

def init_api_limiter(limiter):
    """
    Initialize rate limiting for API endpoints.
    
    Args:
        limiter: Flask-Limiter instance
    """
    # Import locally to avoid circular dependencies
    from .tts import tts_bp
    from .conversational import conversational_bp
    from .leaderboard import leaderboard_bp
    
    # Apply rate limiting to specific blueprints
    limiter.limit("100 per hour")(tts_bp)
    limiter.limit("50 per hour")(conversational_bp)
    limiter.limit("200 per hour")(leaderboard_bp)

__all__ = ['api_bp', 'register_api_blueprints', 'init_api_limiter'] 