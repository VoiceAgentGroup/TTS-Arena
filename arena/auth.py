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
        if not current_user.is_authenticated:
            flash("Authentication is currently disabled", "error")
            return redirect(url_for("arena"))
        
        if not is_admin(current_user):
            flash("You do not have permission to access this page", "error")
            return redirect(url_for("arena"))
            
        return f(*args, **kwargs)
    return decorated_function


@auth.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out", "info")
    return redirect(url_for("arena"))
