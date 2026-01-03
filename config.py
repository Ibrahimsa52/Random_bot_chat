"""
Configuration file for the Telegram Random Chat Bot
"""
import os
import json
from pathlib import Path

# Try to load .env if exists (for local development)
try:
    from dotenv import load_dotenv
    if Path('.env').exists():
        load_dotenv()
except ImportError:
    pass  # dotenv not installed or not needed

# Bot Configuration
BOT_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_IDS = [int(id.strip()) for id in os.getenv('ADMIN_IDS', '').split(',') if id.strip()]

# Firebase Configuration
# Check if Firebase credentials are in environment variable
firebase_creds_env = os.getenv('FIREBASE_CREDENTIALS')
if firebase_creds_env:
    # Write credentials to file from environment variable
    with open('serviceAccountKey.json', 'w') as f:
        f.write(firebase_creds_env)
    FIREBASE_CRED_PATH = 'serviceAccountKey.json'
else:
    FIREBASE_CRED_PATH = os.getenv('FIREBASE_CRED_PATH', 'serviceAccountKey.json')

# Rate Limiting
MAX_MESSAGES_PER_MINUTE = 20
COMMAND_COOLDOWN_SECONDS = 3

# Validation
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN is not set. Please add it to environment variables.")

if not ADMIN_IDS:
    print("Warning: No ADMIN_IDS set. Admin commands will not work.")
