from typing import Dict, Optional, Any

from src.modules.session.session_store import SessionStore
from src.modules.session.session import Session
from src.modules.session.session_provider import SessionProvider
from src.modules.logging import BaseLogger
from src.modules.playbook.config import SessionConfig
from .config_renderer import ConfigRenderer

class SessionManager(SessionProvider):
    """Manages HTTP sessions for playbook execution."""
    
    def __init__(self, config_renderer: ConfigRenderer, logger: BaseLogger, session_store: SessionStore):
        """
        Initialize the session manager.
        
        Args:
            config_renderer: Renders configuration with variables
            logger: Logger instance for logging
        """
        self.config_renderer = config_renderer
        self.logger = logger
        self.session_store = session_store
        self.temp_sessions: Dict[str, Session] = {}
    
    def get_session(self, session_name: str) -> Session:
        """Get a session by name.
        
        Args:
            session_name: Name of the session to retrieve
            
        Returns:
            Session: The requested session
            
        Raises:
            ValueError: If the session doesn't exist
        """
        # First check temp sessions
        if session_name in self.temp_sessions:
            return self.temp_sessions[session_name]
            
        # Then check session store
        try:
            return self.session_store.get_session(session_name)
        except ValueError:
            raise ValueError(f"Session '{session_name}' not found in session store or temp sessions")
    
    def initialize_temp_sessions(self, sessions: Optional[Dict[str, SessionConfig]] = None) -> None:
        """Initialize temporary sessions from configuration."""
        if not sessions:
            return
            
        for name, config in sessions.items():
            try:
                session = Session.from_dict(name, config.model_dump())
                self.temp_sessions[name] = session
                self.logger.log_info(f"Initialized temporary session: {name}")
            except Exception as e:
                self.logger.log_error(f"Failed to initialize temporary session {name}: {str(e)}")
    
    def clear_temp_sessions(self) -> None:
        """Clear all temporary sessions."""
        self.temp_sessions.clear()
        self.logger.log_info("Cleared all temporary sessions") 