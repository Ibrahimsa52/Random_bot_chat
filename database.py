"""
Database layer using Firebase Firestore
"""
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime
from typing import Optional, Dict, List
import config

# Initialize Firebase
cred = credentials.Certificate(config.FIREBASE_CRED_PATH)
firebase_admin.initialize_app(cred)
db = firestore.client()

# Collections
USERS_COLLECTION = 'users'
ACTIVE_CHATS_COLLECTION = 'active_chats'
REPORTS_COLLECTION = 'reports'
WAITING_QUEUE_COLLECTION = 'waiting_queue'


class Database:
    """Firestore database operations"""
    
    @staticmethod
    async def create_user(user_id: int) -> None:
        """Create a new user in the database"""
        user_ref = db.collection(USERS_COLLECTION).document(str(user_id))
        user_ref.set({
            'user_id': user_id,
            'joined_at': datetime.now(),
            'blocked': False,
            'current_chat_with': None,
            'total_chats': 0,
            'reports_count': 0
        })
    
    @staticmethod
    async def get_user(user_id: int) -> Optional[Dict]:
        """Get user data"""
        user_ref = db.collection(USERS_COLLECTION).document(str(user_id))
        doc = user_ref.get()
        if doc.exists:
            return doc.to_dict()
        return None
    
    @staticmethod
    async def user_exists(user_id: int) -> bool:
        """Check if user exists"""
        user = await Database.get_user(user_id)
        return user is not None
    
    @staticmethod
    async def is_blocked(user_id: int) -> bool:
        """Check if user is blocked"""
        user = await Database.get_user(user_id)
        if user:
            return user.get('blocked', False)
        return False
    
    @staticmethod
    async def block_user(user_id: int) -> None:
        """Block a user"""
        user_ref = db.collection(USERS_COLLECTION).document(str(user_id))
        user_ref.update({'blocked': True})
    
    @staticmethod
    async def unblock_user(user_id: int) -> None:
        """Unblock a user"""
        user_ref = db.collection(USERS_COLLECTION).document(str(user_id))
        user_ref.update({'blocked': False})
    
    @staticmethod
    async def get_current_chat(user_id: int) -> Optional[int]:
        """Get the ID of the user's current chat partner"""
        user = await Database.get_user(user_id)
        if user:
            return user.get('current_chat_with')
        return None
    
    @staticmethod
    async def is_in_chat(user_id: int) -> bool:
        """Check if user is currently in a chat"""
        partner = await Database.get_current_chat(user_id)
        return partner is not None
    
    @staticmethod
    async def create_chat(user1_id: int, user2_id: int) -> str:
        """Create a new chat between two users"""
        # Create chat document
        chat_ref = db.collection(ACTIVE_CHATS_COLLECTION).document()
        chat_ref.set({
            'user1_id': user1_id,
            'user2_id': user2_id,
            'started_at': datetime.now()
        })
        
        # Update both users
        db.collection(USERS_COLLECTION).document(str(user1_id)).update({
            'current_chat_with': user2_id,
            'total_chats': firestore.Increment(1)
        })
        db.collection(USERS_COLLECTION).document(str(user2_id)).update({
            'current_chat_with': user1_id,
            'total_chats': firestore.Increment(1)
        })
        
        return chat_ref.id
    
    @staticmethod
    async def end_chat(user_id: int) -> Optional[int]:
        """End user's current chat and return partner ID"""
        partner_id = await Database.get_current_chat(user_id)
        if not partner_id:
            return None
        
        # Update both users
        db.collection(USERS_COLLECTION).document(str(user_id)).update({
            'current_chat_with': None
        })
        db.collection(USERS_COLLECTION).document(str(partner_id)).update({
            'current_chat_with': None
        })
        
        # Delete chat document
        chats = db.collection(ACTIVE_CHATS_COLLECTION).where(
            filter=firestore.FieldFilter('user1_id', '==', user_id)
        ).get()
        
        for chat in chats:
            chat.reference.delete()
        
        chats = db.collection(ACTIVE_CHATS_COLLECTION).where(
            filter=firestore.FieldFilter('user2_id', '==', user_id)
        ).get()
        
        for chat in chats:
            chat.reference.delete()
        
        return partner_id
    
    @staticmethod
    async def add_to_queue(user_id: int) -> None:
        """Add user to waiting queue"""
        queue_ref = db.collection(WAITING_QUEUE_COLLECTION).document(str(user_id))
        queue_ref.set({
            'user_id': user_id,
            'added_at': datetime.now()
        })
    
    @staticmethod
    async def remove_from_queue(user_id: int) -> None:
        """Remove user from waiting queue"""
        queue_ref = db.collection(WAITING_QUEUE_COLLECTION).document(str(user_id))
        queue_ref.delete()
    
    @staticmethod
    async def is_in_queue(user_id: int) -> bool:
        """Check if user is in waiting queue"""
        queue_ref = db.collection(WAITING_QUEUE_COLLECTION).document(str(user_id))
        doc = queue_ref.get()
        return doc.exists
    
    @staticmethod
    async def get_next_from_queue() -> Optional[int]:
        """Get next user from queue (oldest first)"""
        queue = db.collection(WAITING_QUEUE_COLLECTION).order_by(
            'added_at'
        ).limit(1).get()
        
        if queue:
            doc = queue[0]
            return doc.to_dict()['user_id']
        return None
    
    @staticmethod
    async def get_queue_count() -> int:
        """Get number of users in queue"""
        queue = db.collection(WAITING_QUEUE_COLLECTION).get()
        return len(queue)
    
    @staticmethod
    async def create_report(reporter_id: int, reported_id: int, reason: str) -> None:
        """Create a new report"""
        report_ref = db.collection(REPORTS_COLLECTION).document()
        report_ref.set({
            'reporter_id': reporter_id,
            'reported_id': reported_id,
            'reason': reason,
            'timestamp': datetime.now(),
            'resolved': False
        })
        
        # Increment reports count for reported user
        db.collection(USERS_COLLECTION).document(str(reported_id)).update({
            'reports_count': firestore.Increment(1)
        })
    
    @staticmethod
    async def get_all_reports() -> List[Dict]:
        """Get all unresolved reports"""
        reports = db.collection(REPORTS_COLLECTION).where(
            filter=firestore.FieldFilter('resolved', '==', False)
        ).order_by('timestamp', direction=firestore.Query.DESCENDING).get()
        
        return [doc.to_dict() for doc in reports]
    
    @staticmethod
    async def get_stats() -> Dict:
        """Get bot statistics"""
        total_users = len(db.collection(USERS_COLLECTION).get())
        active_chats = len(db.collection(ACTIVE_CHATS_COLLECTION).get())
        waiting_users = len(db.collection(WAITING_QUEUE_COLLECTION).get())
        
        # Count blocked users
        blocked_users = len(db.collection(USERS_COLLECTION).where(
            filter=firestore.FieldFilter('blocked', '==', True)
        ).get())
        
        # Count unresolved reports
        pending_reports = len(db.collection(REPORTS_COLLECTION).where(
            filter=firestore.FieldFilter('resolved', '==', False)
        ).get())
        
        return {
            'total_users': total_users,
            'active_chats': active_chats,
            'waiting_users': waiting_users,
            'blocked_users': blocked_users,
            'pending_reports': pending_reports
        }
    
    @staticmethod
    async def get_all_user_ids() -> List[int]:
        """Get all user IDs for broadcasting"""
        users = db.collection(USERS_COLLECTION).where(
            filter=firestore.FieldFilter('blocked', '==', False)
        ).get()
        
        return [doc.to_dict()['user_id'] for doc in users]
