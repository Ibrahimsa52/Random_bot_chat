"""
Spam protection and rate limiting
"""
from typing import Dict
from datetime import datetime, timedelta
import config

class SpamProtection:
    """Handle rate limiting and spam detection"""
    
    def __init__(self):
        # user_id -> list of message timestamps
        self.message_history: Dict[int, list] = {}
        # user_id -> last command timestamp
        self.command_history: Dict[int, datetime] = {}
    
    def check_message_rate(self, user_id: int) -> bool:
        """
        Check if user is sending too many messages
        Returns True if allowed, False if rate limit exceeded
        """
        now = datetime.now()
        one_minute_ago = now - timedelta(minutes=1)
        
        # Get user's message history
        if user_id not in self.message_history:
            self.message_history[user_id] = []
        
        # Remove old messages (older than 1 minute)
        self.message_history[user_id] = [
            ts for ts in self.message_history[user_id] 
            if ts > one_minute_ago
        ]
        
        # Check if exceeds limit
        if len(self.message_history[user_id]) >= config.MAX_MESSAGES_PER_MINUTE:
            return False
        
        # Add current message
        self.message_history[user_id].append(now)
        return True
    
    def check_command_cooldown(self, user_id: int) -> bool:
        """
        Check if user can execute a command (cooldown check)
        Returns True if allowed, False if in cooldown
        """
        now = datetime.now()
        
        if user_id in self.command_history:
            last_command = self.command_history[user_id]
            cooldown_end = last_command + timedelta(seconds=config.COMMAND_COOLDOWN_SECONDS)
            
            if now < cooldown_end:
                return False
        
        # Update last command time
        self.command_history[user_id] = now
        return True
    
    def reset_user(self, user_id: int) -> None:
        """Reset spam tracking for a user"""
        if user_id in self.message_history:
            del self.message_history[user_id]
        if user_id in self.command_history:
            del self.command_history[user_id]

# Global instance
spam_protection = SpamProtection()
