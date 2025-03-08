import os
import json
from typing import Dict, Any
from .session import Session


class SessionStore:
    """Manages persistent storage of API sessions."""
    
    def __init__(self, sessions_file: str = "~/.restbook/sessions.json"):
        self.sessions_file = os.path.expanduser(sessions_file)
        os.makedirs(os.path.dirname(self.sessions_file), exist_ok=True)
        self.sessions: Dict[str, Session] = {}
        self._load_sessions()

    def get_session(self, name: str) -> Session:
        """
        Get a session by name.
        
        Args:
            name: Name of the session
            
        Returns:
            Session: The requested session
            
        Raises:
            ValueError: If the session does not exist
        """
        if name not in self.sessions:
            raise ValueError(f"Session '{name}' not found")
        return self.sessions[name]

    def upsert_session(self, name: str, session_data: str, overwrite: bool = False) -> Session:
        """
        Create a new session and persist it.
        
        Args:
            name: Name of the session
            session_data: JSON string containing session data (base_url, auth config)
            overwrite: Whether to overwrite an existing session
        Returns:
            Session: The created session
            
        Raises:
            ValueError: If a session with the given name already exists
        """
        if not overwrite and name in self.sessions:
            raise ValueError(f"Session '{name}' already exists")
            
        # Parse session data
        data = json.loads(session_data)
        session = Session.from_dict(name, data)
        
        # Store and persist
        self.sessions[name] = session
        self._save_sessions()
        return session

    def list_sessions(self) -> Dict[str, Session]:
        """Get all available sessions."""
        return self.sessions

    def delete_session(self, name: str) -> None:
        """
        Delete a session.
        
        Args:
            name: Name of the session to delete
            
        Raises:
            ValueError: If the session does not exist
        """
        if name not in self.sessions:
            raise ValueError(f"Session '{name}' not found")
            
        del self.sessions[name]
        self._save_sessions()

    def _load_sessions(self) -> None:
        """Load sessions from disk."""
        if not os.path.exists(self.sessions_file):
            return
            
        try:
            with open(self.sessions_file, 'r') as f:
                data = json.load(f)
                for name, session_data in data.items():
                    self.sessions[name] = Session.from_dict(name, session_data)
        except Exception as e:
            # If file is corrupted, start with empty sessions
            self.sessions = {}

    def _save_sessions(self) -> None:
        """Save sessions to disk."""
        data = {
            name: session.to_dict()
            for name, session in self.sessions.items()
        }
        
        with open(self.sessions_file, 'w') as f:
            json.dump(data, f, indent=2)