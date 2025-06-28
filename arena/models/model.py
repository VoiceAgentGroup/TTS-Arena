"""
Model class and model-related functionality.
"""

from datetime import datetime
from sqlalchemy import func
import logging
from enum import Enum
from models import db


class ModelType(Enum):
    """Constants for model types."""
    TTS = "tts"
    CONVERSATIONAL = "conversational"


class Model(db.Model):
    """Model representing TTS and conversational models."""
    
    id = db.Column(db.String(100), primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    model_type = db.Column(db.String(20), nullable=False)  # 'tts' or 'conversational'
    # Fix ambiguous foreign keys by specifying which foreign key to use
    votes = db.relationship(
        "Vote",
        primaryjoin="or_(Model.id==Vote.model_chosen, Model.id==Vote.model_rejected)",
        viewonly=True,
    )
    current_elo = db.Column(db.Float, default=1500.0)
    win_count = db.Column(db.Integer, default=0)
    match_count = db.Column(db.Integer, default=0)
    is_open = db.Column(db.Boolean, default=False)
    is_active = db.Column(
        db.Boolean, default=True
    )  # Whether the model is active and can be voted on
    model_url = db.Column(db.String(255), nullable=True)

    @property
    def win_rate(self):
        if self.match_count == 0:
            return 0
        return (self.win_count / self.match_count) * 100

    def __repr__(self):
        return f"<Model {self.name} ({self.model_type})>"


def get_leaderboard_data(model_type):
    """Get leaderboard data for a specific model type."""
    model_type_value = model_type.value if isinstance(model_type, ModelType) else model_type
    query = Model.query.filter_by(model_type=model_type_value, is_active=True)
    models = query.order_by(Model.current_elo.desc()).all()
    
    leaderboard = []
    for model in models:
        leaderboard.append({
            'id': model.id,
            'name': model.name,
            'elo': round(model.current_elo, 1),
            'win_count': model.win_count,
            'match_count': model.match_count,
            'win_rate': round(model.win_rate, 1),
            'is_open': model.is_open,
            'model_url': model.model_url
        })
    
    return leaderboard


def get_user_leaderboard(user_id, model_type):
    """Get user's personal leaderboard data."""
    from models.vote import Vote
    
    # Get votes by this user for this model type
    model_type_value = model_type.value if isinstance(model_type, ModelType) else model_type
    user_votes = Vote.query.filter_by(user_id=user_id, model_type=model_type_value).all()
    
    if not user_votes:
        return None
    
    # Count votes for each model
    model_votes = {}
    for vote in user_votes:
        chosen = vote.model_chosen
        rejected = vote.model_rejected
        
        if chosen not in model_votes:
            model_votes[chosen] = {'chosen': 0, 'rejected': 0}
        if rejected not in model_votes:
            model_votes[rejected] = {'chosen': 0, 'rejected': 0}
            
        model_votes[chosen]['chosen'] += 1
        model_votes[rejected]['rejected'] += 1
    
    # Calculate user's personal ratings for each model
    user_leaderboard = []
    for model_id, votes in model_votes.items():
        model = Model.query.get(model_id)
        if model and model.is_active:
            total_votes = votes['chosen'] + votes['rejected']
            win_rate = (votes['chosen'] / total_votes * 100) if total_votes > 0 else 0
            
            user_leaderboard.append({
                'id': model.id,
                'name': model.name,
                'user_wins': votes['chosen'],
                'user_total': total_votes,
                'user_win_rate': round(win_rate, 1),
                'global_elo': round(model.current_elo, 1)
            })
    
    # Sort by user win rate descending
    user_leaderboard.sort(key=lambda x: x['user_win_rate'], reverse=True)
    return user_leaderboard


def get_historical_leaderboard_data(model_type, target_date=None):
    """Get historical leaderboard data for a specific date."""
    from models.vote import EloHistory
    
    if target_date is None:
        target_date = datetime.utcnow()
    
    # Find the closest historical data for each model
    model_type_value = model_type.value if isinstance(model_type, ModelType) else model_type
    subquery = db.session.query(
        EloHistory.model_id,
        func.max(EloHistory.timestamp).label('latest_timestamp')
    ).filter(
        EloHistory.model_type == model_type_value,
        EloHistory.timestamp <= target_date
    ).group_by(EloHistory.model_id).subquery()
    
    historical_elos = db.session.query(EloHistory).join(
        subquery,
        (EloHistory.model_id == subquery.c.model_id) &
        (EloHistory.timestamp == subquery.c.latest_timestamp)
    ).all()
    
    # Convert to leaderboard format
    leaderboard = []
    for elo_history in historical_elos:
        model = db.session.get(Model, elo_history.model_id)
        if model and model.is_active:
            leaderboard.append({
                'id': model.id,
                'name': model.name,
                'elo': round(elo_history.elo_score, 1),
                'timestamp': elo_history.timestamp,
                'is_open': model.is_open,
                'model_url': model.model_url
            })
    
    # Sort by ELO descending
    leaderboard.sort(key=lambda x: x['elo'], reverse=True)
    return leaderboard


def get_key_historical_dates(model_type):
    """Get key dates where significant ELO changes occurred."""
    from models.vote import EloHistory
    
    # Get all unique timestamps for this model type
    model_type_value = model_type.value if isinstance(model_type, ModelType) else model_type
    timestamps = db.session.query(
        func.date(EloHistory.timestamp).label('date')
    ).filter(
        EloHistory.model_type == model_type_value
    ).distinct().order_by(
        func.date(EloHistory.timestamp).desc()
    ).all()
    
    # Convert to datetime objects and return first day of each month
    dates = []
    seen_months = set()
    
    for timestamp_tuple in timestamps:
        date = datetime.strptime(str(timestamp_tuple[0]), '%Y-%m-%d')
        month_key = (date.year, date.month)
        
        if month_key not in seen_months:
            # Add first day of the month
            first_day = datetime(date.year, date.month, 1)
            dates.append(first_day)
            seen_months.add(month_key)
    
    return dates


# Model initialization moved to services/initialization.py
# Use: from services.initialization import insert_initial_models


def get_top_voters(limit=10):
    """Get top voters by vote count."""
    from models.vote import Vote
    from models.user import User
    
    # Get users who have show_in_leaderboard = True and count their votes
    top_voters_query = db.session.query(
        User.username,
        func.count(Vote.id).label('vote_count')
    ).join(Vote, User.id == Vote.user_id).filter(
        User.show_in_leaderboard == True
    ).group_by(User.id, User.username).order_by(
        func.count(Vote.id).desc()
    ).limit(limit)
    
    top_voters = []
    for username, vote_count in top_voters_query:
        top_voters.append({
            'username': username,
            'vote_count': vote_count
        })
    
    return top_voters


def toggle_user_leaderboard_visibility(user_id):
    """Toggle a user's leaderboard visibility setting."""
    from models.user import User
    
    user = db.session.get(User, user_id)
    if user:
        user.show_in_leaderboard = not user.show_in_leaderboard
        try:
            db.session.commit()
            return user.show_in_leaderboard
        except Exception as e:
            db.session.rollback()
            logging.error(f"Error toggling leaderboard visibility for user {user_id}: {str(e)}")
            return None
    return None