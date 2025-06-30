"""
Session management service for TTS and conversational sessions.
"""

import os
import tempfile
import time
from datetime import datetime, timedelta

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
        
        # Clean up audio files - handle both audio_a and audio_b
        audio_paths = []
        if 'audio_a' in session_data:
            audio_paths.append(session_data['audio_a'])
        if 'audio_b' in session_data:
            audio_paths.append(session_data['audio_b'])
            
        for file_path in audio_paths:
            try:
                if file_path and os.path.exists(file_path):
                    os.remove(file_path)
            except Exception as e:
                print(f"Error deleting audio file {file_path}: {e}")
        
        # Remove session data - handle case where session might already be deleted
        try:
            del TTS_SESSIONS[session_id]
            print(f"Cleaned up TTS session: {session_id}")
        except KeyError:
            print(f"TTS session {session_id} was already cleaned up")


def cleanup_conversational_session(session_id):
    """Clean up conversational session files and data."""
    if session_id in CONVERSATIONAL_SESSIONS:
        session_data = CONVERSATIONAL_SESSIONS[session_id]
        
        # Clean up audio files - handle both audio_a and audio_b
        audio_paths = []
        if 'audio_a' in session_data:
            audio_paths.append(session_data['audio_a'])
        if 'audio_b' in session_data:
            audio_paths.append(session_data['audio_b'])
            
        for file_path in audio_paths:
            try:
                if file_path and os.path.exists(file_path):
                    os.remove(file_path)
            except Exception as e:
                print(f"Error deleting conversational audio file {file_path}: {e}")
        
        # Remove session data - handle case where session might already be deleted
        try:
            del CONVERSATIONAL_SESSIONS[session_id]
            print(f"Cleaned up conversational session: {session_id}")
        except KeyError:
            print(f"Conversational session {session_id} was already cleaned up")


def cleanup_expired_sessions():
    """Clean up expired sessions (older than 1 hour)."""
    current_time = datetime.utcnow()
    expired_sessions = []
    
    # Check TTS sessions
    for session_id, session_data in TTS_SESSIONS.items():
        created_at = session_data.get('created_at')
        if created_at and (current_time - created_at).total_seconds() > 3600:  # 1 hour
            expired_sessions.append(('tts', session_id))
    
    # Check conversational sessions
    for session_id, session_data in CONVERSATIONAL_SESSIONS.items():
        created_at = session_data.get('created_at')
        if created_at and (current_time - created_at).total_seconds() > 3600:  # 1 hour
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