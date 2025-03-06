import pytest
import os
import yaml
from src.models.session.session_store import SessionStore
from src.models.session.session import Session


@pytest.fixture
def temp_session_file(tmp_path):
    """Create a temporary session file."""
    return str(tmp_path / "test_sessions.yml")


@pytest.fixture
def session_store(temp_session_file):
    """Create a SessionStore instance with a temporary file."""
    return SessionStore(file_path=temp_session_file)


def test_create_session(session_store):
    """Test creating a new session."""
    session = session_store.create_session(
        name="test-session",
        base_url="http://api.example.com",
        token="test-token"
    )
    
    assert session.name == "test-session"
    assert session.base_url == "http://api.example.com"
    assert session.token == "test-token"
    
    # Verify session was stored
    assert session.id in session_store.sessions
    assert "test-session" in session_store.name_to_id


def test_create_duplicate_session(session_store):
    """Test that creating a session with a duplicate name raises ValueError."""
    session_store.create_session("test-session", "http://api.example.com")
    
    with pytest.raises(ValueError, match="Session 'test-session' already exists"):
        session_store.create_session("test-session", "http://other.example.com")


def test_list_sessions(session_store):
    """Test listing sessions."""
    # Create some test sessions
    session1 = session_store.create_session("session1", "http://api1.example.com")
    session2 = session_store.create_session("session2", "http://api2.example.com")
    
    sessions = session_store.list_sessions()
    
    assert len(sessions) == 2
    assert sessions["session1"].base_url == "http://api1.example.com"
    assert sessions["session2"].base_url == "http://api2.example.com"


def test_update_session(session_store):
    """Test updating a session."""
    session = session_store.create_session("test-session", "http://api.example.com")
    
    updated = session_store.update_session(
        "test-session",
        base_url="http://new.example.com",
        token="new-token"
    )
    
    assert updated.base_url == "http://new.example.com"
    assert updated.token == "new-token"
    assert updated.id == session.id  # ID should remain the same


def test_update_nonexistent_session(session_store):
    """Test that updating a nonexistent session raises ValueError."""
    with pytest.raises(ValueError, match="Session 'nonexistent' does not exist"):
        session_store.update_session("nonexistent", base_url="http://api.example.com")


def test_delete_session(session_store):
    """Test deleting a session."""
    session = session_store.create_session("test-session", "http://api.example.com")
    
    session_store.delete_session("test-session")
    
    assert session.id not in session_store.sessions
    assert "test-session" not in session_store.name_to_id


def test_delete_nonexistent_session(session_store):
    """Test that deleting a nonexistent session raises ValueError."""
    with pytest.raises(ValueError, match="Session 'nonexistent' does not exist"):
        session_store.delete_session("nonexistent")

def test_empty_file_handling(temp_session_file):
    """Test handling of empty or nonexistent session file."""
    # Create empty file
    with open(temp_session_file, "w") as f:
        f.write("")
    
    store = SessionStore(temp_session_file)
    assert len(store.sessions) == 0


def test_file_creation(temp_session_file):
    """Test that the sessions file is created if it doesn't exist."""
    # Ensure file doesn't exist
    if os.path.exists(temp_session_file):
        os.remove(temp_session_file)
    
    store = SessionStore(temp_session_file)
    store.create_session("test-session", "http://api.example.com")
    
    assert os.path.exists(temp_session_file)
    with open(temp_session_file, "r") as f:
        data = yaml.safe_load(f)
        assert isinstance(data, dict)
        assert len(data) == 1 