"""
Session management service for TTS and conversational sessions.
"""

import os
import tempfile
import time

# Store active TTS sessions
TTS_SESSIONS = {}

# Store active conversational sessions
CONVERSATIONAL_SESSIONS = {}

# Create temp directories
TEMP_AUDIO_DIR = os.path.join(tempfile.gettempdir(), "tts_arena_audio")
os.makedirs(TEMP_AUDIO_DIR, exist_ok=True)


def cleanup_session(session_id):
    """Clean up TTS session files and data."""
    if session_id in TTS_SESSIONS:
        session_data = TTS_SESSIONS[session_id]
        
        # Clean up audio files
        if 'audio_files' in session_data:
            for model_key, file_path in session_data['audio_files'].items():
                try:
                    if os.path.exists(file_path):
                        os.remove(file_path)
                except Exception as e:
                    print(f"Error deleting audio file {file_path}: {e}")
        
        # Remove session data
        del TTS_SESSIONS[session_id]
        print(f"Cleaned up TTS session: {session_id}")


def cleanup_conversational_session(session_id):
    """Clean up conversational session files and data."""
    if session_id in CONVERSATIONAL_SESSIONS:
        session_data = CONVERSATIONAL_SESSIONS[session_id]
        
        # Clean up audio files
        if 'audio_files' in session_data:
            for model_key, file_path in session_data['audio_files'].items():
                try:
                    if os.path.exists(file_path):
                        os.remove(file_path)
                except Exception as e:
                    print(f"Error deleting conversational audio file {file_path}: {e}")
        
        # Remove session data
        del CONVERSATIONAL_SESSIONS[session_id]
        print(f"Cleaned up conversational session: {session_id}")


def cleanup_expired_sessions():
    """Clean up expired sessions (older than 1 hour)."""
    current_time = time.time()
    expired_sessions = []
    
    # Check TTS sessions
    for session_id, session_data in TTS_SESSIONS.items():
        if current_time - session_data.get('created_at', 0) > 3600:  # 1 hour
            expired_sessions.append(('tts', session_id))
    
    # Check conversational sessions
    for session_id, session_data in CONVERSATIONAL_SESSIONS.items():
        if current_time - session_data.get('created_at', 0) > 3600:  # 1 hour
            expired_sessions.append(('conversational', session_id))
    
    # Clean up expired sessions
    for session_type, session_id in expired_sessions:
        if session_type == 'tts':
            cleanup_session(session_id)
        else:
            cleanup_conversational_session(session_id)
    
    if expired_sessions:
        print(f"Cleaned up {len(expired_sessions)} expired sessions")


def get_session_count():
    """Get current session counts for monitoring."""
    return {
        'tts_sessions': len(TTS_SESSIONS),
        'conversational_sessions': len(CONVERSATIONAL_SESSIONS),
        'total_sessions': len(TTS_SESSIONS) + len(CONVERSATIONAL_SESSIONS)
    } 