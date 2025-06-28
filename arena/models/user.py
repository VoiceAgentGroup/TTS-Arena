"""
User model and related functionality.
"""

from flask_login import UserMixin
from datetime import datetime
from . import db


class User(db.Model, UserMixin):
    """User model for authentication and tracking."""
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    hf_id = db.Column(db.String(100), unique=True, nullable=False)
    join_date = db.Column(db.DateTime, default=datetime.utcnow)
    hf_account_created = db.Column(db.DateTime, nullable=True)  # HF account creation date
    votes = db.relationship("Vote", backref="user", lazy=True)
    show_in_leaderboard = db.Column(db.Boolean, default=True)

    def __repr__(self):
        return f"<User {self.username}>" 