"""
Security service for handling coordinated voting campaign detection.
"""

import logging
from typing import Optional


class SecurityService:
    """Service for handling security-related operations like coordinated voting detection."""
    
    def __init__(self, flask_app=None):
        """Initialize the security service with optional Flask app."""
        self.app = flask_app
        
    def init_app(self, app):
        """Initialize with Flask app (factory pattern)."""
        self.app = app
        
    def check_for_coordinated_campaigns(self):
        """Check all active models for potential coordinated voting campaigns."""
        if not self.app:
            logging.error("SecurityService: Flask app not initialized")
            return
            
        try:
            # Use Flask app context to access database
            with self.app.app_context():
                from .security import detect_coordinated_voting
                from models import Model, ModelType
                
                # Check TTS models
                tts_models = Model.query.filter_by(model_type=ModelType.TTS.value, is_active=True).all()
                for model in tts_models:
                    try:
                        detect_coordinated_voting(model.id)
                    except Exception as e:
                        logging.error(f"Error checking coordinated voting for TTS model {model.id}: {str(e)}")
                
                # Check conversational models
                conv_models = Model.query.filter_by(model_type=ModelType.CONVERSATIONAL.value, is_active=True).all()
                for model in conv_models:
                    try:
                        detect_coordinated_voting(model.id)
                    except Exception as e:
                        logging.error(f"Error checking coordinated voting for conversational model {model.id}: {str(e)}")
                        
        except Exception as e:
            logging.error(f"Error in coordinated campaign check: {str(e)}")


# Global service instance (will be initialized by app.py)
security_service: Optional[SecurityService] = None


def get_security_service() -> Optional[SecurityService]:
    """Get the global security service instance."""
    return security_service


def init_security_service(app):
    """Initialize the global security service."""
    global security_service
    security_service = SecurityService(app)
    return security_service 