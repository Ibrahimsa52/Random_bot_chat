"""
Configuration file for the Telegram Random Chat Bot
"""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Bot Configuration
BOT_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_IDS = [int(id.strip()) for id in os.getenv('ADMIN_IDS', '').split(',') if id.strip()]
FIREBASE_CRED_PATH = os.getenv('FIREBASE_CRED_PATH', 'serviceAccountKey.json')

# Rate Limiting
MAX_MESSAGES_PER_MINUTE = 20
COMMAND_COOLDOWN_SECONDS = 3

# Validation
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN is not set in .env file")

if not ADMIN_IDS:
    print("Warning: No ADMIN_IDS set. Admin commands will not work.")
