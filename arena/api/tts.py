"""
TTS API endpoints for generation, audio serving, and voting.
"""

import os
import uuid
import json
import shutil
import logging
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
from threading import Thread
from flask import Blueprint, request, jsonify, send_file, current_app
from flask_login import current_user
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from models import Model, ModelType, db
from models.vote import record_vote
from services import get_weighted_random_models, TTS_SESSIONS, cleanup_session, get_security_service
from config import get_client_ip, TEMP_AUDIO_DIR
from services.tts import predict_tts

# Create blueprint
tts_bp = Blueprint('tts', __name__, url_prefix='/api/tts')

# Initialize rate limiter (will be configured by main app)
limiter = Limiter(key_func=get_remote_address)


@tts_bp.route("/generate", methods=["POST"])
@limiter.limit("10 per minute")
def generate_tts():
    """
    Generate TTS audio for model comparison.
    
    Expected JSON payload:
        {
            "text": "Text to synthesize (max 1000 characters)"
        }
        
    Returns:
        JSON with session_id and model information for comparison
    """
    # Authentication has been disabled for development - anonymous access allowed
    
    data = request.get_json()
    if not data:
        return jsonify({"error": "No JSON data provided"}), 400
        
    text = data.get("text", "").strip()

    if not text or len(text) > 1000:
        return jsonify({"error": "Invalid or too long text (max 1000 characters)"}), 400

    # Get available TTS models
    available_models = Model.query.filter_by(
        model_type=ModelType.TTS.value, is_active=True
    ).all()
    
    if len(available_models) < 2:
        return jsonify({"error": "Not enough TTS models available for comparison"}), 500

    # Select two random models for comparison using weighted selection
    selected_models = get_weighted_random_models(available_models, 2, ModelType.TTS)

    try:
        audio_files = []
        model_ids = []

        # Function to process a single model
        def process_model(model):
            """Generate TTS audio for a single model."""
            try:
                # Generate TTS audio
                audio_content = predict_tts(text, model.id)
                if not audio_content:
                    raise ValueError(f"predict_tts failed for model {model.id}")

                # Handle different return types from TTS service
                if isinstance(audio_content, str):
                    # TTS service returned a file path (e.g., from router)
                    if os.path.exists(audio_content):
                        # Get the original file extension
                        _, original_ext = os.path.splitext(audio_content)
                        if not original_ext:
                            original_ext = '.wav'  # fallback
                        
                        # Create destination with correct extension
                        file_uuid = str(uuid.uuid4())
                        dest_path = os.path.join(TEMP_AUDIO_DIR, f"{file_uuid}{original_ext}")
                        
                        # Copy the file to our temp directory
                        import shutil
                        shutil.copy2(audio_content, dest_path)
                        
                        # Clean up the original temp file
                        try:
                            os.remove(audio_content)
                        except OSError:
                            pass
                    else:
                        # Treat as audio content string, encode as bytes
                        file_uuid = str(uuid.uuid4())
                        dest_path = os.path.join(TEMP_AUDIO_DIR, f"{file_uuid}.wav")
                        
                        with open(dest_path, "wb") as f:
                            f.write(audio_content.encode())
                else:
                    # TTS service returned bytes directly
                    file_uuid = str(uuid.uuid4())
                    dest_path = os.path.join(TEMP_AUDIO_DIR, f"{file_uuid}.wav")
                    
                    with open(dest_path, "wb") as f:
                        f.write(audio_content)

                return {"model_id": model.id, "audio_path": dest_path}
                
            except Exception as e:
                # Use standard logging instead of current_app.logger to avoid context issues
                logging.error(f"Error processing model {model.id}: {str(e)}")
                raise

        # Use ThreadPoolExecutor to process models concurrently
        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(process_model, selected_models))

        # Extract results
        for result in results:
            model_ids.append(result["model_id"])
            audio_files.append(result["audio_path"])

        # Create session
        session_id = str(uuid.uuid4())
        TTS_SESSIONS[session_id] = {
            "model_a": model_ids[0],
            "model_b": model_ids[1],
            "audio_a": audio_files[0],
            "audio_b": audio_files[1],
            "text": text,
            "created_at": datetime.utcnow(),
            "expires_at": datetime.utcnow() + timedelta(minutes=30),
            "voted": False,
            "cache_hit": False,
        }

        # Return audio file paths and session
        return jsonify({
            "session_id": session_id,
            "audio_a": f"/api/tts/audio/{session_id}/a",
            "audio_b": f"/api/tts/audio/{session_id}/b",
            "expires_in": 1800,  # 30 minutes
            "cache_hit": False,
            "models": [
                {"id": model_ids[0], "key": "a"},
                {"id": model_ids[1], "key": "b"}
            ]
        })

    except Exception as e:
        # Use standard logging to avoid application context issues  
        logging.error(f"TTS generation error: {str(e)}", exc_info=True)
        
        # Cleanup any files potentially created during the failed attempt
        if 'results' in locals():
            for res in results:
                if 'audio_path' in res and os.path.exists(res['audio_path']):
                    try:
                        os.remove(res['audio_path'])
                    except OSError:
                        pass
        
        return jsonify({"error": "Failed to generate TTS audio"}), 500


@tts_bp.route("/audio/<session_id>/<model_key>")
def get_audio(session_id, model_key):
    """
    Serve audio file for a specific model in a TTS comparison session.
    
    Args:
        session_id: Unique session identifier
        model_key: Either 'a' or 'b' to identify which model's audio to serve
        
    Returns:
        Audio file (WAV format) or error JSON
    """
    if session_id not in TTS_SESSIONS:
        return jsonify({"error": "Invalid or expired session"}), 404

    session_data = TTS_SESSIONS[session_id]

    # Check if session expired
    if datetime.utcnow() > session_data["expires_at"]:
        cleanup_session(session_id)
        return jsonify({"error": "Session expired"}), 410

    # Get the appropriate audio file path
    if model_key == "a":
        audio_path = session_data["audio_a"]
    elif model_key == "b":
        audio_path = session_data["audio_b"]
    else:
        return jsonify({"error": "Invalid model key. Use 'a' or 'b'"}), 400

    # Check if file exists
    if not os.path.exists(audio_path):
        return jsonify({"error": "Audio file not found"}), 404

    # Determine correct mimetype based on file extension
    _, ext = os.path.splitext(audio_path)
    mimetype_map = {
        '.wav': 'audio/wav',
        '.mp3': 'audio/mpeg',
        '.m4a': 'audio/mp4',
        '.ogg': 'audio/ogg',
        '.flac': 'audio/flac'
    }
    mimetype = mimetype_map.get(ext.lower(), 'audio/wav')  # fallback to wav

    return send_file(audio_path, as_attachment=False, mimetype=mimetype)


@tts_bp.route("/vote", methods=["POST"])
@limiter.limit("30 per minute")
def submit_vote():
    """
    Submit a vote for TTS model comparison.
    
    Expected JSON payload:
        {
            "session_id": "session_uuid",
            "chosen_model": "a" or "b"
        }
        
    Returns:
        JSON with vote success status and updated model information
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "No JSON data provided"}), 400
    session_id = data.get("session_id")
    chosen_model_key = data.get("chosen_model")  # "a" or "b"

    if not session_id or session_id not in TTS_SESSIONS:
        return jsonify({"error": "Invalid or expired session"}), 404

    if not chosen_model_key or chosen_model_key not in ["a", "b"]:
        return jsonify({"error": "Invalid chosen model. Must be 'a' or 'b'"}), 400

    session_data = TTS_SESSIONS[session_id]

    # Check if session expired
    if datetime.utcnow() > session_data["expires_at"]:
        cleanup_session(session_id)
        return jsonify({"error": "Session expired"}), 410

    # Check if already voted
    if session_data["voted"]:
        return jsonify({"error": "Vote already submitted for this session"}), 400

    # Get model IDs and audio paths
    chosen_id = (
        session_data["model_a"] if chosen_model_key == "a" else session_data["model_b"]
    )
    rejected_id = (
        session_data["model_b"] if chosen_model_key == "a" else session_data["model_a"]
    )
    chosen_audio_path = (
        session_data["audio_a"] if chosen_model_key == "a" else session_data["audio_b"]
    )
    rejected_audio_path = (
        session_data["audio_b"] if chosen_model_key == "a" else session_data["audio_a"]
    )

    # Calculate session duration and gather analytics data
    vote_time = datetime.utcnow()
    session_duration = (vote_time - session_data["created_at"]).total_seconds()
    client_ip = get_client_ip()
    user_agent = request.headers.get('User-Agent')
    cache_hit = session_data.get("cache_hit", False)

    # Record vote with analytics data
    user_id = current_user.id if current_user.is_authenticated else None
    vote_result = record_vote(
        user_id,
        session_data["text"],
        chosen_id,
        rejected_id,
        ModelType.TTS.value,
        session_duration=session_duration,
        ip_address=client_ip,
        user_agent=user_agent,
        generation_date=session_data.get("created_at"),
        cache_hit=cache_hit,
    )

    if not vote_result.get("success"):
        return jsonify({"error": "Vote recording failed"}), 500

    # Save preference data for research purposes
    try:
        vote_uuid = str(uuid.uuid4())
        vote_dir = os.path.join("./votes", vote_uuid)
        os.makedirs(vote_dir, exist_ok=True)

        # Copy audio files
        shutil.copy(chosen_audio_path, os.path.join(vote_dir, "chosen.wav"))
        shutil.copy(rejected_audio_path, os.path.join(vote_dir, "rejected.wav"))

        # Create metadata
        chosen_model_obj = db.session.get(Model, chosen_id)
        rejected_model_obj = db.session.get(Model, rejected_id)
        metadata = {
            "text": session_data["text"],
            "chosen_model": chosen_model_obj.name if chosen_model_obj else "Unknown",
            "chosen_model_id": chosen_model_obj.id if chosen_model_obj else "Unknown",
            "rejected_model": rejected_model_obj.name if rejected_model_obj else "Unknown",
            "rejected_model_id": rejected_model_obj.id if rejected_model_obj else "Unknown",
            "session_id": session_id,
            "timestamp": datetime.utcnow().isoformat(),
            "username": current_user.username if current_user.is_authenticated else "Anonymous",
            "model_type": "TTS",
            "vote_id": vote_result.get("vote_id"),
            "session_duration_seconds": session_duration
        }
        
        with open(os.path.join(vote_dir, "metadata.json"), "w") as f:
            json.dump(metadata, f, indent=2)

    except Exception as e:
        current_app.logger.error(f"Error saving preference data for vote {session_id}: {str(e)}")
        # Continue even if saving preference data fails, vote is already recorded

    # Mark session as voted
    session_data["voted"] = True

    # Check for coordinated voting campaigns (async to not slow down response)
    try:
        security_service = get_security_service()
        if security_service:
            campaign_check_thread = Thread(
                target=security_service.check_for_coordinated_campaigns
            )
            campaign_check_thread.daemon = True
            campaign_check_thread.start()
    except Exception as e:
        current_app.logger.error(f"Error starting coordinated campaign check thread: {str(e)}")

    # Get model objects for response
    chosen_model_obj = db.session.get(Model, chosen_id)
    rejected_model_obj = db.session.get(Model, rejected_id)
    model_a_obj = db.session.get(Model, session_data["model_a"])
    model_b_obj = db.session.get(Model, session_data["model_b"])

    # Return success response with model information (including names field for frontend)
    return jsonify({
        "success": True,
        "vote_id": vote_result.get("vote_id"),
        "chosen_model": {
            "id": chosen_id, 
            "name": chosen_model_obj.name if chosen_model_obj else "Unknown"
        },
        "rejected_model": {
            "id": rejected_id, 
            "name": rejected_model_obj.name if rejected_model_obj else "Unknown"
        },
        "names": {
            "a": model_a_obj.name if model_a_obj else "Unknown",
            "b": model_b_obj.name if model_b_obj else "Unknown",
        },
        "session_duration_seconds": session_duration,
        "new_elo_scores": {
            "chosen": vote_result.get("chosen_model_new_elo"),
            "rejected": vote_result.get("rejected_model_new_elo")
        }
    })


@tts_bp.route("/session/<session_id>/status")
@limiter.limit("60 per minute")
def get_session_status(session_id):
    """
    Get the current status of a TTS session.
    
    Args:
        session_id: Unique session identifier
        
    Returns:
        JSON with session status information
    """
    if session_id not in TTS_SESSIONS:
        return jsonify({"error": "Session not found"}), 404
    
    session_data = TTS_SESSIONS[session_id]
    
    # Check if expired
    is_expired = datetime.utcnow() > session_data["expires_at"]
    if is_expired:
        cleanup_session(session_id)
        return jsonify({"error": "Session expired"}), 410
    
    # Calculate remaining time
    remaining_seconds = (session_data["expires_at"] - datetime.utcnow()).total_seconds()
    
    return jsonify({
        "session_id": session_id,
        "status": "active",
        "voted": session_data.get("voted", False),
        "text": session_data["text"],
        "created_at": session_data["created_at"].isoformat(),
        "expires_in_seconds": max(0, int(remaining_seconds)),
        "cache_hit": session_data.get("cache_hit", False)
    })


@tts_bp.route("/health")
@limiter.limit("120 per minute")
def health_check():
    """
    Health check endpoint for TTS API.
    
    Returns:
        JSON with service health status
    """
    try:
        # Check if we have active TTS models
        active_models = Model.query.filter_by(
            model_type=ModelType.TTS.value, 
            is_active=True
        ).count()
        
        return jsonify({
            "status": "healthy",
            "service": "tts_api",
            "active_models": active_models,
            "active_sessions": len(TTS_SESSIONS),
            "timestamp": datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        current_app.logger.error(f"TTS API health check failed: {str(e)}")
        return jsonify({
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }), 500 