"""
Cleanup service for periodic maintenance tasks.
"""

from apscheduler.schedulers.background import BackgroundScheduler
from .session_manager import cleanup_expired_sessions


def setup_cleanup():
    """Setup periodic cleanup tasks."""
    scheduler = BackgroundScheduler()
    
    def cleanup_task():
        """Periodic cleanup task for expired sessions."""
        try:
            cleanup_expired_sessions()
        except Exception as e:
            print(f"Error during session cleanup: {e}")
    
    # Schedule cleanup every 10 minutes
    scheduler.add_job(
        func=cleanup_task,
        trigger="interval",
        minutes=10,
        id='session_cleanup'
    )
    
    scheduler.start()
    print("Cleanup scheduler started - running every 10 minutes") 