import pytest
import os
import json
from src.modules.session.session_store import SessionStore
from src.modules.session.session import Session
from src.modules.session.auth import AuthConfig


class TestSessionStore:
    """Test cases for SessionStore class."""

    @pytest.fixture
    def temp_session_file(self, tmp_path):
        """Create a temporary session file."""
        session_file = tmp_path / "sessions.json"
        return str(session_file)

    @pytest.fixture
    def session_store(self, temp_session_file):
        """Create a SessionStore instance with a temporary file."""
        return SessionStore(sessions_file=temp_session_file)

    @pytest.fixture
    def basic_session_data(self):
        """Basic session data without auth."""
        return {
            "base_url": "https://api.example.com",
            "auth": None
        }

    @pytest.fixture
    def auth_session_data(self):
        """Session data with bearer auth."""
        return {
            "base_url": "https://api.example.com",
            "auth": {
                "type": "bearer",
                "credentials": {"token": "test-token"}
            }
        }

    def test_init(self, temp_session_file):
        """Test SessionStore initialization."""
        store = SessionStore(sessions_file=temp_session_file)
        assert os.path.exists(os.path.dirname(temp_session_file))
        assert store.sessions == {}

    def test_upsert_new_session(self, session_store, auth_session_data):
        """Test creating a new session."""
        session = session_store.upsert_session("test", json.dumps(auth_session_data))
        assert session.name == "test"
        assert session.base_url == "https://api.example.com"
        assert session.auth_config is not None
        assert session.auth_config.type == "bearer"
        assert session.auth_config.credentials == {"token": "test-token"}

    def test_upsert_existing_session(self, session_store, basic_session_data, auth_session_data):
        """Test updating an existing session."""
        # Create initial session
        session_store.upsert_session("test", json.dumps(basic_session_data))
        
        # Should raise error without overwrite flag
        with pytest.raises(ValueError, match="Session 'test' already exists"):
            session_store.upsert_session("test", json.dumps(auth_session_data))
        
        # Should succeed with overwrite flag
        session = session_store.upsert_session("test", json.dumps(auth_session_data), overwrite=True)
        assert session.base_url == "https://api.example.com"
        assert session.auth_config is not None
        assert session.auth_config.credentials == {"token": "test-token"}

    def test_get_session(self, session_store, basic_session_data):
        """Test getting a session."""
        # Create a session
        session_store.upsert_session("test", json.dumps(basic_session_data))
        
        # Get the session
        session = session_store.get_session("test")
        assert session.name == "test"
        assert session.base_url == "https://api.example.com"
        
        # Try to get non-existent session
        with pytest.raises(ValueError, match="Session 'nonexistent' not found"):
            session_store.get_session("nonexistent")

    def test_list_sessions(self, session_store):
        """Test listing all sessions."""
        # Create some sessions
        sessions_data = {
            "test1": {
                "base_url": "https://api1.example.com",
                "auth": None
            },
            "test2": {
                "base_url": "https://api2.example.com",
                "auth": {
                    "type": "bearer",
                    "credentials": {"token": "test-token"}
                }
            }
        }
        
        for name, data in sessions_data.items():
            session_store.upsert_session(name, json.dumps(data))
        
        sessions = session_store.list_sessions()
        assert len(sessions) == 2
        assert "test1" in sessions
        assert "test2" in sessions
        assert sessions["test1"].base_url == "https://api1.example.com"
        assert sessions["test2"].auth_config is not None

    def test_delete_session(self, session_store, basic_session_data):
        """Test deleting a session."""
        # Create a session
        session_store.upsert_session("test", json.dumps(basic_session_data))
        
        # Delete the session
        session_store.delete_session("test")
        assert "test" not in session_store.sessions
        
        # Try to delete non-existent session
        with pytest.raises(ValueError, match="Session 'nonexistent' not found"):
            session_store.delete_session("nonexistent")

    def test_persistence(self, temp_session_file, basic_session_data):
        """Test that sessions persist to disk."""
        # Create a store and add a session
        store1 = SessionStore(sessions_file=temp_session_file)
        store1.upsert_session("test", json.dumps(basic_session_data))
        
        # Create a new store instance with the same file
        store2 = SessionStore(sessions_file=temp_session_file)
        assert "test" in store2.sessions
        assert store2.sessions["test"].base_url == "https://api.example.com"

    def test_corrupted_file(self, temp_session_file):
        """Test handling of corrupted session file."""
        # Write invalid JSON to the file
        with open(temp_session_file, 'w') as f:
            f.write("invalid json")
        
        # Should start with empty sessions when file is corrupted
        store = SessionStore(sessions_file=temp_session_file)
        assert store.sessions == {} 