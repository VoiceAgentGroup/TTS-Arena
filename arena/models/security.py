"""
Security-related models and functionality.
"""

import logging
from datetime import datetime, timedelta
from models import db


class CoordinatedVotingCampaign(db.Model):
    """Log detected coordinated voting campaigns"""
    id = db.Column(db.Integer, primary_key=True)
    model_id = db.Column(db.String(100), db.ForeignKey("model.id"), nullable=False)
    model_type = db.Column(db.String(20), nullable=False)
    detected_at = db.Column(db.DateTime, default=datetime.utcnow)
    time_window_hours = db.Column(db.Integer, nullable=False)  # Detection window (e.g., 6 hours)
    vote_count = db.Column(db.Integer, nullable=False)  # Total votes in the campaign
    user_count = db.Column(db.Integer, nullable=False)  # Number of users involved
    confidence_score = db.Column(db.Float, nullable=False)  # 0-1 confidence level
    status = db.Column(db.String(20), default='active')  # active, resolved, false_positive
    admin_notes = db.Column(db.Text, nullable=True)
    resolved_by = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    resolved_at = db.Column(db.DateTime, nullable=True)
    
    model = db.relationship("Model", backref=db.backref("coordinated_campaigns", lazy=True))
    resolver = db.relationship("User", backref=db.backref("resolved_campaigns", lazy=True))
    
    def __repr__(self):
        return f"<CoordinatedVotingCampaign {self.id}: {self.model_id} ({self.vote_count} votes, {self.user_count} users)>"


class CampaignParticipant(db.Model):
    """Track users involved in coordinated voting campaigns"""
    id = db.Column(db.Integer, primary_key=True)
    campaign_id = db.Column(db.Integer, db.ForeignKey("coordinated_voting_campaign.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    votes_in_campaign = db.Column(db.Integer, nullable=False)
    first_vote_at = db.Column(db.DateTime, nullable=False)
    last_vote_at = db.Column(db.DateTime, nullable=False)
    suspicion_level = db.Column(db.String(20), nullable=False)  # low, medium, high
    
    campaign = db.relationship("CoordinatedVotingCampaign", backref=db.backref("participants", lazy=True))
    user = db.relationship("User", backref=db.backref("campaign_participations", lazy=True))
    
    def __repr__(self):
        return f"<CampaignParticipant {self.user_id} in campaign {self.campaign_id} ({self.votes_in_campaign} votes)>"


class UserTimeout(db.Model):
    """Track user timeouts/bans for suspicious activity"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    reason = db.Column(db.String(500), nullable=False)  # Reason for timeout
    timeout_type = db.Column(db.String(50), nullable=False)  # coordinated_voting, rapid_voting, manual, etc.
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)  # Admin who created timeout
    is_active = db.Column(db.Boolean, default=True)
    cancelled_at = db.Column(db.DateTime, nullable=True)
    cancelled_by = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    cancel_reason = db.Column(db.String(500), nullable=True)
    
    # Related campaign if timeout was due to coordinated voting
    related_campaign_id = db.Column(db.Integer, db.ForeignKey("coordinated_voting_campaign.id"), nullable=True)
    
    user = db.relationship("User", foreign_keys=[user_id], backref=db.backref("timeouts", lazy=True))
    creator = db.relationship("User", foreign_keys=[created_by], backref=db.backref("created_timeouts", lazy=True))
    canceller = db.relationship("User", foreign_keys=[cancelled_by], backref=db.backref("cancelled_timeouts", lazy=True))
    related_campaign = db.relationship("CoordinatedVotingCampaign", backref=db.backref("resulting_timeouts", lazy=True))
    
    def is_currently_active(self):
        """Check if timeout is currently active"""
        if not self.is_active:
            return False
        return datetime.utcnow() < self.expires_at
    
    def __repr__(self):
        return f"<UserTimeout {self.user_id}: {self.timeout_type} until {self.expires_at}>"


def check_user_timeout(user_id):
    """Check if a user currently has an active timeout."""
    if not user_id:
        return None
    
    active_timeout = UserTimeout.query.filter_by(
        user_id=user_id,
        is_active=True
    ).filter(
        UserTimeout.expires_at > datetime.utcnow()
    ).first()
    
    return active_timeout


def create_user_timeout(user_id, reason, timeout_type, duration_days, created_by=None, related_campaign_id=None):
    """Create a new user timeout."""
    try:
        expires_at = datetime.utcnow() + timedelta(days=duration_days)
        
        timeout = UserTimeout(
            user_id=user_id,
            reason=reason,
            timeout_type=timeout_type,
            expires_at=expires_at,
            created_by=created_by,
            related_campaign_id=related_campaign_id
        )
        
        db.session.add(timeout)
        db.session.commit()
        
        logging.info(f"Created timeout for user {user_id}: {timeout_type} for {duration_days} days")
        return timeout
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error creating user timeout: {str(e)}")
        return None


def cancel_user_timeout(timeout_id, cancelled_by, cancel_reason):
    """Cancel an active user timeout."""
    try:
        timeout = db.session.get(UserTimeout, timeout_id)
        if not timeout:
            return False
        
        timeout.is_active = False
        timeout.cancelled_at = datetime.utcnow()
        timeout.cancelled_by = cancelled_by
        timeout.cancel_reason = cancel_reason
        
        db.session.commit()
        
        logging.info(f"Cancelled timeout {timeout_id} by user {cancelled_by}")
        return True
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error cancelling timeout: {str(e)}")
        return False


def log_coordinated_campaign(model_id, model_type, vote_count, user_count, 
                           time_window_hours, confidence_score, participants_data):
    """Log a detected coordinated voting campaign."""
    try:
        campaign = CoordinatedVotingCampaign(
            model_id=model_id,
            model_type=model_type,
            vote_count=vote_count,
            user_count=user_count,
            time_window_hours=time_window_hours,
            confidence_score=confidence_score
        )
        
        db.session.add(campaign)
        db.session.flush()  # Get the campaign ID
        
        # Add participants
        for participant_data in participants_data:
            participant = CampaignParticipant(
                campaign_id=campaign.id,
                user_id=participant_data['user_id'],
                votes_in_campaign=participant_data['votes_in_campaign'],
                first_vote_at=participant_data['first_vote_at'],
                last_vote_at=participant_data['last_vote_at'],
                suspicion_level=participant_data['suspicion_level']
            )
            db.session.add(participant)
        
        db.session.commit()
        
        logging.warning(f"Logged coordinated campaign for model {model_id}: {vote_count} votes from {user_count} users")
        return campaign
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error logging coordinated campaign: {str(e)}")
        return None


def get_user_timeouts(user_id=None, active_only=True, limit=50):
    """Get user timeouts with optional filtering."""
    query = UserTimeout.query
    
    if user_id:
        query = query.filter_by(user_id=user_id)
    
    if active_only:
        query = query.filter(
            UserTimeout.is_active == True,
            UserTimeout.expires_at > datetime.utcnow()
        )
    
    return query.order_by(UserTimeout.created_at.desc()).limit(limit).all()


def get_coordinated_campaigns(status=None, limit=50):
    """Get coordinated voting campaigns with optional status filtering."""
    query = CoordinatedVotingCampaign.query
    
    if status:
        query = query.filter_by(status=status)
    
    return query.order_by(CoordinatedVotingCampaign.detected_at.desc()).limit(limit).all()


def resolve_campaign(campaign_id, resolved_by, status, admin_notes=None):
    """Resolve a coordinated voting campaign."""
    try:
        campaign = db.session.get(CoordinatedVotingCampaign, campaign_id)
        if not campaign:
            return False
        
        campaign.status = status
        campaign.resolved_by = resolved_by
        campaign.resolved_at = datetime.utcnow()
        if admin_notes:
            campaign.admin_notes = admin_notes
        
        db.session.commit()
        
        logging.info(f"Resolved campaign {campaign_id} as {status} by user {resolved_by}")
        return True
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error resolving campaign: {str(e)}")
        return False


