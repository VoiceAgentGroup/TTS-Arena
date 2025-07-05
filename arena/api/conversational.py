"""
Conversational API endpoints for podcast-style generation.
"""

from flask import Blueprint, request, jsonify, send_file, current_app as app, session
from models import db, Model, ModelType, record_vote
from config import get_client_ip
from services import get_weighted_random_models, CONVERSATIONAL_SESSIONS, cleanup_conversational_session
from services.tts import predict_tts
from datetime import datetime, timedelta
import os
import uuid
import json
import shutil
from concurrent.futures import ThreadPoolExecutor
from threading import Thread

from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Create blueprint
conversational_bp = Blueprint('conversational', __name__, url_prefix='/api/conversational')

# Initialize limiter for this blueprint (will be configured by main app)
limiter = Limiter(
    key_func=get_remote_address,
    storage_uri="memory://",
    default_limits=["1000 per day", "100 per hour"]
)

# Get temp audio directory from app config
# Use the same temp directory as TTS API for consistency
from config import TEMP_AUDIO_DIR

@conversational_bp.route("/generate-from-theme", methods=["POST"])
@limiter.limit("3 per minute")  # More restrictive since this uses LLM API
def generate_podcast_from_theme():
    """Generate conversational/podcast audio from theme and keywords."""
    data = request.get_json()
    if not data:
        return jsonify({"error": "No JSON data provided"}), 400
        
    theme = data.get("theme")
    keywords = data.get("keywords", [])
    length = data.get("length", "medium")
    style = data.get("style", "podcast")

    if not theme or not isinstance(theme, str) or len(theme.strip()) < 3:
        return jsonify({"error": "Theme must be a non-empty string with at least 3 characters"}), 400
    
    if not isinstance(keywords, list):
        return jsonify({"error": "Keywords must be a list"}), 400
    
    if length not in ["short", "medium", "long"]:
        return jsonify({"error": "Length must be 'short', 'medium', or 'long'"}), 400
        
    if style not in ["podcast", "interview", "debate", "casual", "educational", "news"]:
        return jsonify({"error": "Invalid style parameter"}), 400

    try:
        # Generate script using LLM
        from services import get_content_generator
        content_generator = get_content_generator()
        
        if not content_generator.is_available():
            return jsonify({"error": "LLM content generation service not available. Please configure OPENAI_API_KEY."}), 503
        
        # Generate the conversational script
        script = content_generator.generate_conversation(
            theme=theme.strip(),
            keywords=[k.strip() for k in keywords if k.strip()],
            length=length,
            style=style
        )
        
        # Now use the generated script with the existing TTS generation logic
        return _generate_podcast_audio(script)
        
    except Exception as e:
        app.logger.error(f"Theme-based generation error: {str(e)}")
        return jsonify({"error": f"Failed to generate conversation: {str(e)}"}), 500

@conversational_bp.route("/generate", methods=["POST"])
@limiter.limit("5 per minute")
def generate_podcast():
    """Generate conversational/podcast audio from pre-written script or theme."""
    data = request.get_json()
    if not data:
        return jsonify({"error": "No JSON data provided"}), 400
    
    # Check if this is a script-based request or theme-based request
    if "script" in data:
        # Original script-based generation
        script = data.get("script")
        
        if not script or not isinstance(script, list) or len(script) < 2:
            return jsonify({"error": "Invalid script format or too short"}), 400

        # Validate script format
        for line in script:
            if not isinstance(line, dict) or "text" not in line or "speaker_id" not in line:
                return (
                    jsonify(
                        {
                            "error": "Invalid script line format. Each line must have text and speaker_id"
                        }
                    ),
                    400,
                )
            if (
                not line["text"]
                or not isinstance(line["speaker_id"], int)
                or line["speaker_id"] not in [0, 1]
            ):
                return (
                    jsonify({"error": "Invalid script content. Speaker ID must be 0 or 1"}),
                    400,
                )
        
        return _generate_podcast_audio(script)
        
    elif "theme" in data:
        # Theme-based generation (redirect to the dedicated endpoint logic)
        theme = data.get("theme")
        keywords = data.get("keywords", [])
        length = data.get("length", "medium")
        style = data.get("style", "podcast")

        if not theme or not isinstance(theme, str) or len(theme.strip()) < 3:
            return jsonify({"error": "Theme must be a non-empty string with at least 3 characters"}), 400
        
        if not isinstance(keywords, list):
            return jsonify({"error": "Keywords must be a list"}), 400
        
        if length not in ["short", "medium", "long"]:
            return jsonify({"error": "Length must be 'short', 'medium', or 'long'"}), 400
            
        if style not in ["podcast", "interview", "debate", "casual", "educational", "news"]:
            return jsonify({"error": "Invalid style parameter"}), 400

        try:
            # Generate script using LLM
            from services import get_content_generator
            content_generator = get_content_generator()
            
            if not content_generator.is_available():
                return jsonify({"error": "LLM content generation service not available. Please configure OPENAI_API_KEY."}), 503
            
            # Generate the conversational script
            script = content_generator.generate_conversation(
                theme=theme.strip(),
                keywords=[k.strip() for k in keywords if k.strip()],
                length=length,
                style=style
            )
            
            # Now use the generated script with the existing TTS generation logic
            return _generate_podcast_audio(script)
            
        except Exception as e:
            app.logger.error(f"Theme-based generation error: {str(e)}")
            return jsonify({"error": f"Failed to generate conversation: {str(e)}"}), 500
    else:
        return jsonify({"error": "Either 'script' or 'theme' must be provided"}), 400

def _generate_podcast_audio(script):
    """Internal function to generate podcast audio from a validated script."""
    # Get two conversational models (currently only CSM and PlayDialog)
    available_models = Model.query.filter_by(
        model_type=ModelType.CONVERSATIONAL.value, is_active=True
    ).all()

    if len(available_models) < 2:
        return jsonify({"error": "Not enough conversational models available"}), 500

    selected_models = get_weighted_random_models(available_models, 2, ModelType.CONVERSATIONAL)

    try:
        # Generate audio for both models concurrently
        audio_files = []
        model_ids = []

        # Function to process a single model
        def process_model(model):
            # Call conversational TTS service
            audio_content = predict_tts(script, model.id)

            # Handle different return types from TTS service
            if isinstance(audio_content, str):
                # TTS service returned a file path
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

        # Use ThreadPoolExecutor to process models concurrently
        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(process_model, selected_models))

        # Extract results
        for result in results:
            model_ids.append(result["model_id"])
            audio_files.append(result["audio_path"])

        # Create session
        session_id = str(uuid.uuid4())
        script_text = " ".join([line["text"] for line in script])
        CONVERSATIONAL_SESSIONS[session_id] = {
            "model_a": model_ids[0],
            "model_b": model_ids[1],
            "audio_a": audio_files[0],
            "audio_b": audio_files[1],
            "text": script_text[:1000],  # Limit text length
            "created_at": datetime.utcnow(),
            "expires_at": datetime.utcnow() + timedelta(minutes=30),
            "voted": False,
            "script": script,
            "cache_hit": False,  # Conversational is always generated on-demand
        }

        # Return audio file paths and session
        return jsonify(
            {
                "session_id": session_id,
                "audio_a": f"/api/conversational/audio/{session_id}/a",
                "audio_b": f"/api/conversational/audio/{session_id}/b",
                "expires_in": 1800,  # 30 minutes in seconds
                "generated_script": script,  # Include the script in response for theme-based generation
            }
        )

    except Exception as e:
        app.logger.error(f"Conversational generation error: {str(e)}")
        return jsonify({"error": f"Failed to generate podcast: {str(e)}"}), 500

@conversational_bp.route("/audio/<session_id>/<model_key>")
def get_podcast_audio(session_id, model_key):
    """Serve audio file for conversational session."""
    # If verification not setup, handle it first
    if app.config.get("TURNSTILE_ENABLED") and not session.get("turnstile_verified"):
        return jsonify({"error": "Turnstile verification required"}), 403

    if session_id not in CONVERSATIONAL_SESSIONS:
        return jsonify({"error": "Invalid or expired session"}), 404

    session_data = CONVERSATIONAL_SESSIONS[session_id]

    # Check if session expired
    if datetime.utcnow() > session_data["expires_at"]:
        cleanup_conversational_session(session_id)
        return jsonify({"error": "Session expired"}), 410

    if model_key == "a":
        audio_path = session_data["audio_a"]
    elif model_key == "b":
        audio_path = session_data["audio_b"]
    else:
        return jsonify({"error": "Invalid model key"}), 400

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

    return send_file(audio_path, mimetype=mimetype)

@conversational_bp.route("/vote", methods=["POST"])
@limiter.limit("30 per minute")
def submit_podcast_vote():
    """Submit vote for conversational comparison. Supports tie votes."""

    data = request.get_json()
    if not data:
        return jsonify({"error": "No JSON data provided"}), 400
        
    session_id = data.get("session_id")
    chosen_model_key = data.get("chosen_model")  # "a", "b", or "tie"

    if not session_id or session_id not in CONVERSATIONAL_SESSIONS:
        return jsonify({"error": "Invalid or expired session"}), 404

    if not chosen_model_key or chosen_model_key not in ["a", "b", "tie"]:
        return jsonify({"error": "Invalid chosen model"}), 400

    session_data = CONVERSATIONAL_SESSIONS[session_id]

    # Check if session expired
    if datetime.utcnow() > session_data["expires_at"]:
        cleanup_conversational_session(session_id)
        return jsonify({"error": "Session expired"}), 410

    # Check if already voted
    if session_data["voted"]:
        return jsonify({"error": "Vote already submitted for this session"}), 400

    # Get model IDs and audio paths
    model_a_id = session_data["model_a"]
    model_b_id = session_data["model_b"]
    audio_a_path = session_data["audio_a"]
    audio_b_path = session_data["audio_b"]

    # Calculate session duration and gather analytics data
    vote_time = datetime.utcnow()
    session_duration = (vote_time - session_data["created_at"]).total_seconds()
    client_ip = get_client_ip()
    user_agent = request.headers.get('User-Agent')
    cache_hit = session_data.get("cache_hit", False)

    user_id = None  # Anonymous voting

    if chosen_model_key == "tie":
        vote_id = record_vote(
            user_id,
            {"model_a": model_a_id, "model_b": model_b_id},
            'tie',
            'tie',
            ModelType.CONVERSATIONAL.value,
            session_duration=session_duration,
            ip_address=client_ip,
            user_agent=user_agent,
            generation_date=session_data.get("created_at"),
            cache_hit=cache_hit,
        )
        chosen_id = model_a_id
        rejected_id = model_b_id
        chosen_audio_path = audio_a_path
        rejected_audio_path = audio_b_path
    else:
        chosen_id = model_a_id if chosen_model_key == "a" else model_b_id
        rejected_id = model_b_id if chosen_model_key == "a" else model_a_id
        chosen_audio_path = audio_a_path if chosen_model_key == "a" else audio_b_path
        rejected_audio_path = audio_b_path if chosen_model_key == "a" else audio_a_path
        vote_id = record_vote(
            user_id,
            session_data["text"],
            chosen_id,
            rejected_id,
            ModelType.CONVERSATIONAL.value,
            session_duration=session_duration,
            ip_address=client_ip,
            user_agent=user_agent,
            generation_date=session_data.get("created_at"),
            cache_hit=cache_hit,
        )

    if not vote_id or (isinstance(vote_id, dict) and not vote_id.get("success", True)):
        return jsonify({"error": "Vote recording failed"}), 500

    # --- Save preference data ---
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
            "script": session_data["script"], # Save the full script
            "chosen_model": chosen_model_obj.name if chosen_model_obj else "Unknown",
            "chosen_model_id": chosen_model_obj.id if chosen_model_obj else "Unknown",
            "rejected_model": rejected_model_obj.name if rejected_model_obj else "Unknown",
            "rejected_model_id": rejected_model_obj.id if rejected_model_obj else "Unknown",
            "session_id": session_id,
            "timestamp": datetime.utcnow().isoformat(),
            "username": "Anonymous",
            "model_type": "CONVERSATIONAL"
        }
        with open(os.path.join(vote_dir, "metadata.json"), "w") as f:
            json.dump(metadata, f, indent=2)

    except Exception as e:
        app.logger.error(f"Error saving preference data for conversational vote {session_id}: {str(e)}")
        # Continue even if saving preference data fails, vote is already recorded

    # Mark session as voted
    session_data["voted"] = True

    # Check for coordinated voting campaigns (async to not slow down response)
    try:
        from services import get_security_service
        security_service = get_security_service()
        if security_service:
            campaign_check_thread = Thread(target=security_service.check_for_coordinated_campaigns)
            campaign_check_thread.daemon = True
            campaign_check_thread.start()
    except Exception as e:
        app.logger.error(f"Error starting coordinated campaign check thread: {str(e)}")

    # Get model objects for response
    chosen_model_obj = db.session.get(Model, chosen_id)
    rejected_model_obj = db.session.get(Model, rejected_id)
    model_a_obj = db.session.get(Model, session_data["model_a"])
    model_b_obj = db.session.get(Model, session_data["model_b"])

    # Return updated models (use previously fetched objects)
    return jsonify(
        {
            "success": True,
            "chosen_model": {
                "id": chosen_id, 
                "name": chosen_model_obj.name if chosen_model_obj else "Unknown"
            },
            "rejected_model": {
                "id": rejected_id,
                "name": rejected_model_obj.name if rejected_model_obj else "Unknown",
            },
            "names": {
                "a": model_a_obj.name if model_a_obj else "Unknown",
                "b": model_b_obj.name if model_b_obj else "Unknown",
            },
        }
    ) 