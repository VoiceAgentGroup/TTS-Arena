"""
Sync service for HuggingFace Spaces database synchronization and periodic tasks.
"""

import os
import logging
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from concurrent.futures import ThreadPoolExecutor
from huggingface_hub import HfApi
from config import IS_SPACES
from models import db
from services.initialization import insert_initial_models


def setup_periodic_tasks(security_service=None):
    """Setup periodic background tasks for the application."""
    if not IS_SPACES:
        print("Not running in HF Spaces - skipping periodic tasks setup")
        return
    
    scheduler = BackgroundScheduler()
    executor = ThreadPoolExecutor(max_workers=2)
    
    def sync_database():
        """Sync database to HuggingFace dataset every 30 minutes."""
        try:
            print("Starting database sync to HuggingFace dataset...")
            
            # Upload database file
            api = HfApi()
            api.upload_file(
                path_or_fileobj="instance/tts_arena.db",
                path_in_repo="tts_arena.db",
                repo_id="TTS-AGI/database-arena-v2",
                repo_type="dataset",
                token=os.getenv("HF_TOKEN"),
            )
            print("Database synced successfully to HuggingFace dataset ✅")
            
        except Exception as e:
            print(f"Error syncing database: {str(e)} ⚠️")
    
    def sync_preferences_data():
        """Sync user preferences and other data."""
        try:
            print("Syncing preferences data...")
            
            # Add any additional data sync logic here
            # For now, this is a placeholder for future functionality
            
            print("Preferences data sync completed ✅")
            
        except Exception as e:
            print(f"Error syncing preferences data: {str(e)} ⚠️")
    
    def check_coordinated_voting():
        """Check for coordinated voting campaigns."""
        try:
            if security_service:
                security_service.check_for_coordinated_campaigns()
            else:
                logging.warning("Security service not available for coordinated voting check")
        except Exception as e:
            logging.error(f"Error checking for coordinated campaigns: {str(e)}")
    
    def initialize_models():
        """Initialize models if they don't exist."""
        try:
            insert_initial_models()
        except Exception as e:
            logging.error(f"Error initializing models: {str(e)}")
    
    # Schedule database sync every 30 minutes
    scheduler.add_job(
        func=lambda: executor.submit(sync_database),
        trigger="interval",
        minutes=30,
        id='database_sync'
    )
    
    # Schedule preferences sync every 2 hours
    scheduler.add_job(
        func=lambda: executor.submit(sync_preferences_data),
        trigger="interval",
        hours=2,
        id='preferences_sync'
    )
    
    # Schedule coordinated voting check every hour
    scheduler.add_job(
        func=lambda: executor.submit(check_coordinated_voting),
        trigger="interval",
        hours=1,
        id='coordinated_voting_check'
    )
    
    # Initialize models on startup
    scheduler.add_job(
        func=lambda: executor.submit(initialize_models),
        trigger="date",
        run_date=datetime.now(),
        id='initialize_models'
    )
    
    scheduler.start()
    print("Periodic tasks scheduler started") 