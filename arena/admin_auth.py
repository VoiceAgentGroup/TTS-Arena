"""
Simple authentication for admin panel
"""
import os
import hashlib
from functools import wraps
from flask import session, request, redirect, url_for, flash

def hash_password(password):
    """Hash password with salt"""
    salt = os.getenv("ADMIN_SALT", "tts_arena_admin_salt_2024")
    return hashlib.sha256((password + salt).encode()).hexdigest()

def verify_admin_password(password):
    """Verify admin password against environment variable"""
    admin_password = os.getenv("ADMIN_PASSWORD", "admin123")  # Default for dev
    return hash_password(password) == hash_password(admin_password)

def is_admin_logged_in():
    """Check if admin is logged in"""
    return session.get("admin_authenticated", False)

def login_admin():
    """Mark admin as logged in"""
    session["admin_authenticated"] = True
    session.permanent = True

def logout_admin():
    """Log out admin"""
    session.pop("admin_authenticated", None)

def require_admin_auth(f):
    """Decorator to require admin authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not is_admin_logged_in():
            # Store the original URL to redirect back after login
            session["next_url"] = request.url
            flash("Please login to access the admin panel", "info")
            return redirect(url_for("admin.login"))
        return f(*args, **kwargs)
    return decorated_function 