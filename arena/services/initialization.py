"""
Database initialization service for TTS Arena.
Handles initial data seeding and setup operations.
"""

import logging
from config import TTS_MODELS, CONVERSATIONAL_MODELS
from models import db

logger = logging.getLogger(__name__)


def insert_initial_models():
    """Insert initial TTS and conversational models if they don't exist."""
    from models.model import Model, ModelType
    
    # Prepare all models with their types
    all_models = []
    
    # Add TTS models
    for model_config in TTS_MODELS:
        model_data = model_config.copy()
        model_data["model_type"] = ModelType.TTS.value
        all_models.append(model_data)
    
    # Add conversational models  
    for model_config in CONVERSATIONAL_MODELS:
        model_data = model_config.copy()
        model_data["model_type"] = ModelType.CONVERSATIONAL.value
        all_models.append(model_data)
    
    # Insert models that don't exist
    models_added = 0
    for model_data in all_models:
        existing_model = db.session.get(Model, model_data["id"])
        if not existing_model:
            model = Model(**model_data)
            db.session.add(model)
            logger.info(f"Added model: {model.name} ({model.model_type})")
            models_added += 1
        else:
            logger.debug(f"Model already exists: {existing_model.name}")
    
    try:
        db.session.commit()
        if models_added > 0:
            logger.info(f"Successfully inserted {models_added} initial models")
        else:
            logger.info("All initial models already exist")
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error inserting initial models: {str(e)}")
        raise


def initialize_database():
    """Initialize the database with all required initial data."""
    logger.info("Initializing database...")
    
    try:
        # Create all tables
        db.create_all()
        logger.info("Database tables created/verified")
        
        # Insert initial models
        insert_initial_models()
        
        # Add more initialization steps here as needed
        # For example: default admin users, settings, etc.
        
        logger.info("Database initialization completed successfully")
        
    except Exception as e:
        logger.error(f"Database initialization failed: {str(e)}")
        raise


def reset_database():
    """Reset the database (WARNING: This will delete all data!)"""
    logger.warning("Resetting database - ALL DATA WILL BE LOST!")
    
    try:
        db.drop_all()
        db.create_all()
        insert_initial_models()
        logger.info("Database reset completed successfully")
    except Exception as e:
        logger.error(f"Database reset failed: {str(e)}")
        raise 