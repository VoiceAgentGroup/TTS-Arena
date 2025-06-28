"""
Leaderboard API endpoints for historical data, statistics, and user preferences.
"""

from datetime import datetime
from flask import Blueprint, request, jsonify, current_app
from flask_login import current_user
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from models import ModelType, get_historical_leaderboard_data, User, db

# Create blueprint
leaderboard_bp = Blueprint('leaderboard', __name__, url_prefix='/api/leaderboard')

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)


@leaderboard_bp.route("/historical/<model_type>")
@limiter.limit("60 per hour")
def get_historical_leaderboard(model_type):
    """
    Get historical leaderboard data for a specific date.
    
    Args:
        model_type: Either 'tts' or 'conversational'
        
    Query Parameters:
        date: Date in YYYY-MM-DD format
        
    Returns:
        JSON with historical leaderboard data
    """
    # Validate model type
    if model_type not in [ModelType.TTS, ModelType.CONVERSATIONAL]:
        return jsonify({"error": "Invalid model type. Must be 'tts' or 'conversational'"}), 400

    # Get date from query parameter
    date_str = request.args.get("date")
    if not date_str:
        return jsonify({"error": "Date parameter is required in YYYY-MM-DD format"}), 400

    try:
        # Parse date from URL parameter
        target_date = datetime.strptime(date_str, "%Y-%m-%d")
        
        # Get historical leaderboard data
        leaderboard_data = get_historical_leaderboard_data(model_type, target_date)
        
        return jsonify({
            "success": True,
            "date": target_date.strftime("%B %d, %Y"),
            "model_type": model_type,
            "leaderboard": leaderboard_data
        })
        
    except ValueError as e:
        return jsonify({
            "error": "Invalid date format. Use YYYY-MM-DD format",
            "example": "2024-01-15"
        }), 400
    except Exception as e:
        current_app.logger.error(f"Error fetching historical leaderboard: {str(e)}")
        return jsonify({"error": "Failed to fetch historical data"}), 500


@leaderboard_bp.route("/toggle-visibility", methods=["POST"])
@limiter.limit("20 per hour")
def toggle_leaderboard_visibility():
    """
    Toggle user's visibility on the public leaderboard.
    
    Note: Authentication is currently disabled for development.
    
    Returns:
        JSON with updated visibility status
    """
    try:
        data = request.get_json()
        show_in_leaderboard = data.get("show_in_leaderboard", False)
        
        # For development: create/update anonymous user
        # In production, this would require authentication
        user_id = current_user.id if current_user.is_authenticated else 1
        
        user = db.session.get(User, user_id)
        if not user:
            # Create anonymous user for development - note: hf_id is required
            user = User(
                username="anonymous", 
                hf_id="anonymous_dev", 
                show_in_leaderboard=show_in_leaderboard
            )
            db.session.add(user)
        else:
            user.show_in_leaderboard = show_in_leaderboard
        
        db.session.commit()
        
        return jsonify({
            "success": True,
            "show_in_leaderboard": show_in_leaderboard,
            "message": f"Leaderboard visibility {'enabled' if show_in_leaderboard else 'disabled'}"
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error toggling leaderboard visibility: {str(e)}")
        return jsonify({"error": "Failed to update visibility setting"}), 500


@leaderboard_bp.route("/stats/<model_type>")
@limiter.limit("100 per hour")
def get_leaderboard_stats(model_type):
    """
    Get comprehensive statistics for a model type leaderboard.
    
    Args:
        model_type: Either 'tts' or 'conversational'
        
    Returns:
        JSON with detailed statistics
    """
    if model_type not in [ModelType.TTS, ModelType.CONVERSATIONAL]:
        return jsonify({"error": "Invalid model type"}), 400
    
    try:
        from models import Model, Vote
        
        # Get model statistics
        models = Model.query.filter_by(
            model_type=model_type,
            is_active=True
        ).all()
        
        # Get vote count for this model type
        total_votes = Vote.query.filter_by(model_type=model_type).count()
        
        # Calculate statistics
        if models:
            avg_elo = sum(model.current_elo for model in models) / len(models)
            max_elo = max(model.current_elo for model in models)
            min_elo = min(model.current_elo for model in models)
            total_matches = sum(model.match_count for model in models)
        else:
            avg_elo = max_elo = min_elo = total_matches = 0
        
        return jsonify({
            "success": True,
            "model_type": model_type,
            "statistics": {
                "total_models": len(models),
                "total_votes": total_votes,
                "total_matches": total_matches,
                "average_elo": round(avg_elo, 1),
                "highest_elo": round(max_elo, 1),
                "lowest_elo": round(min_elo, 1)
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"Error fetching leaderboard stats: {str(e)}")
        return jsonify({"error": "Failed to fetch statistics"}), 500 