import uuid
from datetime import datetime, timedelta
from typing import Dict, Optional
import threading
from chatbot.main_chatbot import MainChatbot


class SessionManager:
    """Manages chat sessions and chatbot instances"""
    
    def __init__(self, api_key: str, session_timeout_minutes: int = 30):
        self.api_key = api_key
        self.session_timeout = timedelta(minutes=session_timeout_minutes)
        self.sessions: Dict[str, Dict] = {}
        self.lock = threading.Lock()
    
    def create_session(self) -> str:
        """Create a new chat session"""
        session_id = str(uuid.uuid4())
        
        with self.lock:
            # Create new chatbot instance for this session
            chatbot = MainChatbot(self.api_key, "documents")
            
            self.sessions[session_id] = {
                "chatbot": chatbot,
                "created_at": datetime.now(),
                "last_activity": datetime.now(),
                "message_count": 0
            }
        
        return session_id
    
    def get_chatbot(self, session_id: str) -> Optional[MainChatbot]:
        """Get chatbot instance for a session"""
        with self.lock:
            session = self.sessions.get(session_id)
            if session:
                # Update last activity
                session["last_activity"] = datetime.now()
                return session["chatbot"]
            return None
    
    def increment_message_count(self, session_id: str):
        """Increment message count for a session"""
        with self.lock:
            session = self.sessions.get(session_id)
            if session:
                session["message_count"] += 1
    
    def get_session_info(self, session_id: str) -> Optional[Dict]:
        """Get session information"""
        with self.lock:
            session = self.sessions.get(session_id)
            if session:
                return {
                    "session_id": session_id,
                    "created_at": session["created_at"].isoformat(),
                    "last_activity": session["last_activity"].isoformat(),
                    "message_count": session["message_count"],
                    "form_active": session["chatbot"].get_appointment_status()["active"]
                }
            return None
    
    def cleanup_expired_sessions(self):
        """Remove expired sessions"""
        now = datetime.now()
        expired_sessions = []
        
        with self.lock:
            for session_id, session in self.sessions.items():
                if now - session["last_activity"] > self.session_timeout:
                    expired_sessions.append(session_id)
            
            for session_id in expired_sessions:
                del self.sessions[session_id]
        
        return len(expired_sessions)
    
    def reset_session_form(self, session_id: str) -> bool:
        """Reset appointment form for a session"""
        with self.lock:
            session = self.sessions.get(session_id)
            if session:
                session["chatbot"].reset_appointment_form()
                return True
            return False
    
    def clear_session_memory(self, session_id: str) -> bool:
        """Clear conversation memory for a session"""
        with self.lock:
            session = self.sessions.get(session_id)
            if session:
                session["chatbot"].clear_memory()
                session["message_count"] = 0
                return True
            return False
    
    def get_active_session_count(self) -> int:
        """Get count of active sessions"""
        with self.lock:
            return len(self.sessions)
    
    def delete_session(self, session_id: str) -> bool:
        """Delete a specific session"""
        with self.lock:
            if session_id in self.sessions:
                del self.sessions[session_id]
                return True
            return False