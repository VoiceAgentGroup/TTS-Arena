from flask import Flask, render_template, g
from flask_login import LoginManager, current_user
from flask_limiter import Limiter
from flask_migrate import Migrate
import random
import json
import os

# Import our new modular components
from config import FlaskConfig, get_client_ip
from models import db, User
from services.initialization import insert_initial_models
from admin import admin
from api import register_api_blueprints, init_api_limiter
from services import setup_cleanup, setup_periodic_tasks, init_security_service
from config import TEMP_AUDIO_DIR

app = Flask(__name__)
app.config.from_object(FlaskConfig)

# Initialize extensions
db.init_app(app)
migrate = Migrate(app, db)

login_manager = LoginManager()
login_manager.init_app(app)

# Configure rate limits
limiter = Limiter(
    app=app,
    key_func=lambda: get_client_ip() or "unknown",
    default_limits=["2000 per day", "50 per minute"],
    storage_uri="memory://",
)

# Load sentences from data files
all_harvard_sentences = []
with open("data/sentences.txt", "r") as f, open("data/emotional_sentences.txt", "r") as f_emotional:
    # Store all sentences and clean them up
    all_harvard_sentences = [line.strip() for line in f.readlines() if line.strip()] + [line.strip() for line in f_emotional.readlines() if line.strip()]
    # Shuffle for initial random selection if needed, but main list remains ordered
    initial_sentences = random.sample(all_harvard_sentences, min(len(all_harvard_sentences), 500)) # Limit initial pass for template

# Register blueprints
app.register_blueprint(admin)

# Register API blueprints using the new modular system
register_api_blueprints(app)
init_api_limiter(limiter)


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


@app.before_request
def before_request():
    g.user = current_user
    g.is_admin = True


@app.route("/")
def arena():
    # Pass a subset of sentences for the random button fallback
    return render_template("arena.html", harvard_sentences=json.dumps(initial_sentences))


@app.route("/leaderboard")
def leaderboard():
    from models import get_leaderboard_data, get_user_leaderboard, get_key_historical_dates, get_top_voters, ModelType
    
    tts_leaderboard = get_leaderboard_data(ModelType.TTS)
    conversational_leaderboard = get_leaderboard_data(ModelType.CONVERSATIONAL)
    top_voters = get_top_voters(10)  # Get top 10 voters

    # Initialize personal leaderboard data
    tts_personal_leaderboard = None
    conversational_personal_leaderboard = None
    user_leaderboard_visibility = None

    # If user is logged in, get their personal leaderboard and visibility setting
    if current_user.is_authenticated:
        tts_personal_leaderboard = get_user_leaderboard(current_user.id, ModelType.TTS)
        conversational_personal_leaderboard = get_user_leaderboard(
            current_user.id, ModelType.CONVERSATIONAL
        )
        user_leaderboard_visibility = current_user.show_in_leaderboard

    # Get key dates for the timeline
    tts_key_dates = get_key_historical_dates(ModelType.TTS)
    conversational_key_dates = get_key_historical_dates(ModelType.CONVERSATIONAL)

    # Format dates for display in the dropdown
    formatted_tts_dates = [date.strftime("%B %Y") for date in tts_key_dates]
    formatted_conversational_dates = [
        date.strftime("%B %Y") for date in conversational_key_dates
    ]

    return render_template(
        "leaderboard.html",
        tts_leaderboard=tts_leaderboard,
        conversational_leaderboard=conversational_leaderboard,
        tts_personal_leaderboard=tts_personal_leaderboard,
        conversational_personal_leaderboard=conversational_personal_leaderboard,
        tts_key_dates=tts_key_dates,
        conversational_key_dates=conversational_key_dates,
        formatted_tts_dates=formatted_tts_dates,
        formatted_conversational_dates=formatted_conversational_dates,
        top_voters=top_voters,
        user_leaderboard_visibility=user_leaderboard_visibility
    )


@app.route("/about")
def about():
    return render_template("about.html")


@app.cli.command("init-db")
def init_db():
    """Initialize database with initial models."""
    with app.app_context():
        db.create_all()
        insert_initial_models()


# Development server configuration
if __name__ == "__main__":
    with app.app_context():
        # Initialize security service
        init_security_service(app)
        
        # Setup background tasks
        setup_cleanup()
        setup_periodic_tasks()
        
        # Ensure temp directories exist
        os.makedirs(TEMP_AUDIO_DIR, exist_ok=True)
        os.makedirs("./votes", exist_ok=True)
    
    # Run development server
    app.run(host="0.0.0.0", port=5000)
