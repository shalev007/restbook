from typing import Protocol
from .session import Session

class SessionProvider(Protocol):
    """Interface for providing session access."""
    
    def get_session(self, session_name: str) -> Session:
        """Get a session by name.
        
        Args:
            session_name: Name of the session to retrieve
            
        Returns:
            Session: The requested session
            
        Raises:
            ValueError: If the session doesn't exist
        """
        ... 