from typing import Dict, Optional
from ..config import SessionConfig, RetryConfig
from ...session.session import Session
from ...session.session_store import SessionStore
from ...logging import BaseLogger
from .config_renderer import ConfigRenderer

class SessionManager:
    """Manages session creation, configuration, and retrieval."""
    
    def __init__(self, config_renderer: ConfigRenderer, logger: BaseLogger, session_store: SessionStore):
        """
        Initialize the session manager.
        
        Args:
            config_renderer: Config renderer for handling session configuration
            logger: Logger instance for logging
            session_store: Store for managing HTTP sessions
        """
        self.config_renderer = config_renderer
        self.logger = logger
        self.session_store = session_store
        self._temp_sessions: Dict[str, Session] = {}

    def initialize_temp_sessions(self, sessions_config: Optional[Dict[str, SessionConfig]] = None) -> None:
        """
        Initialize temporary sessions from configuration.
        
        Args:
            sessions_config: Dictionary of session configurations
        """
        if not sessions_config:
            return
            
        for session_name, session_config in sessions_config.items():
            rendered_config = self.config_renderer.render_session_config(session_config)
            self._temp_sessions[session_name] = Session.from_dict(session_name, rendered_config.model_dump())

    def get_session(self, session_name: str) -> Session:
        """
        Get a session by name, checking both temporary and persistent stores.
        
        Args:
            session_name: Name of the session to retrieve
            
        Returns:
            Session: The requested session
            
        Raises:
            ValueError: If the session does not exist
        """
        if session_name in self._temp_sessions:
            return self._temp_sessions[session_name]
        return self.session_store.get_session(session_name)

    def clear_temp_sessions(self) -> None:
        """Clear all temporary sessions."""
        self._temp_sessions.clear() 