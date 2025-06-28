"""
Models package for TTS Arena application.

This package contains all database models and related functionality.
"""

from flask_sqlalchemy import SQLAlchemy

# Initialize database
db = SQLAlchemy()

# Import all models to make them available when the package is imported
from .user import User
from .model import Model, ModelType
from .vote import Vote, EloHistory
from .security import CoordinatedVotingCampaign, CampaignParticipant, UserTimeout

# Import utility functions
from .vote import calculate_elo_change, record_vote
from .model import (
    get_leaderboard_data, get_user_leaderboard, get_historical_leaderboard_data, 
    get_key_historical_dates, get_top_voters, 
    toggle_user_leaderboard_visibility
)
from .security import (
    check_user_timeout, create_user_timeout, cancel_user_timeout, 
    log_coordinated_campaign, get_user_timeouts, get_coordinated_campaigns, 
    resolve_campaign
)
from .utils import anonymize_ip_address

__all__ = [
    'db',
    'User', 'Model', 'ModelType', 'Vote', 'EloHistory',
    'CoordinatedVotingCampaign', 'CampaignParticipant', 'UserTimeout',
    'calculate_elo_change', 'record_vote',
    'get_leaderboard_data', 'get_user_leaderboard', 'get_historical_leaderboard_data',
    'get_key_historical_dates', 'get_top_voters',
    'toggle_user_leaderboard_visibility',
    'check_user_timeout', 'create_user_timeout', 'cancel_user_timeout',
    'log_coordinated_campaign', 'get_user_timeouts', 'get_coordinated_campaigns',
    'resolve_campaign', 'anonymize_ip_address'
]