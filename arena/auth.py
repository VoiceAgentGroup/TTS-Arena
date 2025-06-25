from flask import Blueprint, redirect, url_for, flash
from flask_login import logout_user, current_user, login_required
import os
from functools import wraps

auth = Blueprint("auth", __name__)


def is_admin(user):
    """Check if a user is in the ADMIN_USERS environment variable"""
    if not user or not user.is_authenticated:
        return False
    
    admin_users = os.getenv("ADMIN_USERS", "").split(",")
    return user.username in [username.strip() for username in admin_users]


def admin_required(f):
    """Decorator to require admin access for a route"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Simple environment variable check - no session redirect loops
        admin_access = os.getenv("ADMIN_ACCESS_ENABLED", "false").lower() == "true"
        
        if not admin_access:
            # Return a simple error page instead of redirect
            return """
            <html>
            <head><title>Admin Access Disabled</title></head>
            <body style="font-family: Arial, sans-serif; margin: 50px; text-align: center;">
                <h2>Admin Access Disabled</h2>
                <p>Set environment variable: <code>ADMIN_ACCESS_ENABLED=true</code></p>
                <p>Then restart the application.</p>
                <a href="/" style="color: #007cba;">← Back to TTS Arena</a>
            </body>
            </html>
            """, 403
            
        return f(*args, **kwargs)
    return decorated_function


@auth.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out", "info")
    return redirect(url_for("arena"))
