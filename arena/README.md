# TTS Arena - Local Development

A simplified Text-to-Speech comparison arena for local development.

## Features

- **Anonymous TTS Arena**: Compare TTS models without authentication
- **Admin Interface**: Manage models, view statistics, and monitor votes
- **Leaderboard**: View model rankings based on ELO ratings

## Quick Start

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Create a .env file**:
   ```bash
   cp .env.example .env
   ```

3. **Run the application**:
   ```bash
   python app.py
   ```

4. **Access the application**:
   - Main Arena: http://localhost:5000
   - Leaderboard: http://localhost:5000/leaderboard 
   - Admin Panel: http://localhost:5000/admin (requires password login)

## Files Structure

### Core Files
- `app.py` - Main Flask application
- `models.py` - Database models and utilities
- `tts.py` - TTS provider integration
- `admin.py` - Admin interface
- `security.py` - Security and anti-abuse measures

### Templates
- `templates/arena.html` - Main TTS comparison interface
- `templates/leaderboard.html` - Model rankings
- `templates/admin/` - Admin interface templates

### Data
- `data/sentences.txt` - Standard test sentences
- `data/emotional_sentences.txt` - Emotional test sentences

### Configuration
- `requirements.txt` - Python dependencies
- `.env.example` - Environment configuration template

## Notes

- **Authentication disabled**: All access is anonymous for the main arena
- **Admin access**: Protected by password authentication (default: `admin123`)
- **Database**: SQLite database created automatically in `instance/`
- **Sentences**: Random sentences from `data/sentences.txt` and `data/emotional_sentences.txt`

## Admin Panel

The admin panel is protected by password authentication:
- **Default password**: `admin123` (change this in your `.env` file)
- **Login URL**: http://localhost:5000/admin/login
- **Features**: Model management, user analytics, vote monitoring, security tools

## Local Development Only

This version is simplified for local development and testing. For production deployment, additional security measures and authentication would be required.
