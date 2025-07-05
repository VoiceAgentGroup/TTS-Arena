"""
Vote and ELO-related models and functionality.
"""

import math
import logging
from datetime import datetime
from . import db


class Vote(db.Model):
    """Vote model for tracking user preferences between models."""
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    text = db.Column(db.String(1000), nullable=False)
    vote_date = db.Column(db.DateTime, default=datetime.utcnow)
    model_chosen = db.Column(db.String(100), db.ForeignKey("model.id"), nullable=False)
    model_rejected = db.Column(
        db.String(100), db.ForeignKey("model.id"), nullable=False
    )
    model_type = db.Column(db.String(20), nullable=False)  # 'tts' or 'conversational'
    
    # New analytics columns - added with temporary checks for migration
    session_duration_seconds = db.Column(db.Float, nullable=True)  # Time from generation to vote
    ip_address_partial = db.Column(db.String(20), nullable=True)  # IP with last digits removed
    user_agent = db.Column(db.String(500), nullable=True)  # Browser/device info
    generation_date = db.Column(db.DateTime, nullable=True)  # When audio was generated
    cache_hit = db.Column(db.Boolean, nullable=True)  # Whether generation was from cache

    chosen = db.relationship(
        "Model",
        foreign_keys=[model_chosen],
        backref=db.backref("chosen_votes", lazy=True),
    )
    rejected = db.relationship(
        "Model",
        foreign_keys=[model_rejected],
        backref=db.backref("rejected_votes", lazy=True),
    )

    def __repr__(self):
        return f"<Vote {self.id}: {self.model_chosen} over {self.model_rejected} ({self.model_type})>"


class EloHistory(db.Model):
    """Track ELO rating changes over time."""
    
    id = db.Column(db.Integer, primary_key=True)
    model_id = db.Column(db.String(100), db.ForeignKey("model.id"), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    elo_score = db.Column(db.Float, nullable=False)
    vote_id = db.Column(db.Integer, db.ForeignKey("vote.id"), nullable=True)
    model_type = db.Column(db.String(20), nullable=False)  # 'tts' or 'conversational'

    model = db.relationship("Model", backref=db.backref("elo_history", lazy=True))
    vote = db.relationship("Vote", backref=db.backref("elo_changes", lazy=True))

    def __repr__(self):
        return f"<EloHistory {self.model_id}: {self.elo_score} at {self.timestamp} ({self.model_type})>"


def calculate_elo_change(winner_elo, loser_elo, k_factor=32):
    """Calculate Elo rating changes for a match."""
    expected_winner = 1 / (1 + math.pow(10, (loser_elo - winner_elo) / 400))
    expected_loser = 1 / (1 + math.pow(10, (winner_elo - loser_elo) / 400))

    winner_new_elo = winner_elo + k_factor * (1 - expected_winner)
    loser_new_elo = loser_elo + k_factor * (0 - expected_loser)

    return winner_new_elo, loser_new_elo


def calculate_elo_tie(elo_a, elo_b, k_factor=32):
    """Calculate Elo rating changes for a tie."""
    expected_a = 1 / (1 + math.pow(10, (elo_b - elo_a) / 400))
    expected_b = 1 / (1 + math.pow(10, (elo_a - elo_b) / 400))
    new_elo_a = elo_a + k_factor * (0.5 - expected_a)
    new_elo_b = elo_b + k_factor * (0.5 - expected_b)
    return new_elo_a, new_elo_b


def record_vote(user_id, text, chosen_model_id, rejected_model_id, model_type, 
                session_duration=None, ip_address=None, user_agent=None, 
                generation_date=None, cache_hit=None):
    """Record a vote and update ELO ratings. Supports ties if chosen_model_id or rejected_model_id is 'tie'."""
    from models.model import Model
    from models.utils import anonymize_ip_address
    
    try:
        # Tie logic: if either model id is 'tie', treat as a tie
        is_tie = (chosen_model_id == 'tie' or rejected_model_id == 'tie')
        if is_tie:
            # For a tie, both model IDs must be provided (not 'tie')
            # Assume text contains both model IDs in a tuple if tie
            if isinstance(text, dict) and 'model_a' in text and 'model_b' in text:
                model_a_id = text['model_a']
                model_b_id = text['model_b']
            else:
                # Fallback: treat chosen_model_id and rejected_model_id as the two models
                model_a_id = chosen_model_id if chosen_model_id != 'tie' else rejected_model_id
                model_b_id = rejected_model_id if rejected_model_id != 'tie' else chosen_model_id
            model_a = db.session.get(Model, model_a_id)
            model_b = db.session.get(Model, model_b_id)
            if not model_a or not model_b:
                raise ValueError("Invalid model IDs for tie")
            new_elo_a, new_elo_b = calculate_elo_tie(model_a.current_elo, model_b.current_elo)
            model_a.current_elo = new_elo_a
            model_b.current_elo = new_elo_b
            model_a.match_count += 1
            model_b.match_count += 1
            # Record ELO history
            vote = Vote(
                user_id=user_id,
                text=str(text),
                model_chosen=model_a_id,
                model_rejected=model_b_id,
                model_type=model_type,
                session_duration_seconds=session_duration,
                ip_address_partial=anonymize_ip_address(ip_address),
                user_agent=user_agent,
                generation_date=generation_date,
                cache_hit=cache_hit
            )
            db.session.add(vote)
            db.session.flush()
            elo_history_a = EloHistory(
                model_id=model_a_id,
                elo_score=new_elo_a,
                vote_id=vote.id,
                model_type=model_type
            )
            elo_history_b = EloHistory(
                model_id=model_b_id,
                elo_score=new_elo_b,
                vote_id=vote.id,
                model_type=model_type
            )
            db.session.add(elo_history_a)
            db.session.add(elo_history_b)
            db.session.commit()
            logging.info(f"Vote recorded: Tie between {model_a_id} (Elo: {new_elo_a:.1f}) and {model_b_id} (Elo: {new_elo_b:.1f})")
            return {
                "success": True,
                "vote_id": vote.id,
                "chosen_model_new_elo": new_elo_a,
                "rejected_model_new_elo": new_elo_b
            }
        # Create the vote record
        vote = Vote(
            user_id=user_id,
            text=text,
            model_chosen=chosen_model_id,
            model_rejected=rejected_model_id,
            model_type=model_type,
            session_duration_seconds=session_duration,
            ip_address_partial=anonymize_ip_address(ip_address),
            user_agent=user_agent,
            generation_date=generation_date,
            cache_hit=cache_hit
        )
        db.session.add(vote)
        db.session.flush()  # Get the vote ID

        # Get the models and update their stats
        chosen_model = db.session.get(Model, chosen_model_id)
        rejected_model = db.session.get(Model, rejected_model_id)

        if not chosen_model or not rejected_model:
            raise ValueError("Invalid model IDs")

        # Calculate new ELO ratings
        new_chosen_elo, new_rejected_elo = calculate_elo_change(
            chosen_model.current_elo, rejected_model.current_elo
        )

        # Update model stats
        chosen_model.current_elo = new_chosen_elo
        chosen_model.win_count += 1
        chosen_model.match_count += 1

        rejected_model.current_elo = new_rejected_elo
        rejected_model.match_count += 1

        # Record ELO history
        chosen_elo_history = EloHistory(
            model_id=chosen_model_id,
            elo_score=new_chosen_elo,
            vote_id=vote.id,
            model_type=model_type
        )
        rejected_elo_history = EloHistory(
            model_id=rejected_model_id,
            elo_score=new_rejected_elo,
            vote_id=vote.id,
            model_type=model_type
        )

        db.session.add(chosen_elo_history)
        db.session.add(rejected_elo_history)
        db.session.commit()

        logging.info(f"Vote recorded: {chosen_model_id} (Elo: {new_chosen_elo:.1f}) beat {rejected_model_id} (Elo: {new_rejected_elo:.1f})")
        
        return {
            "success": True,
            "vote_id": vote.id,
            "chosen_model_new_elo": new_chosen_elo,
            "rejected_model_new_elo": new_rejected_elo
        }

    except Exception as e:
        db.session.rollback()
        logging.error(f"Error recording vote: {str(e)}")
        return {"success": False, "error": str(e)} 