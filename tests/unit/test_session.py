import pytest
from src.models.session.session import Session


def test_session_creation():
    """Test creating a Session with minimal required fields."""
    session = Session(
        name="test-session",
        base_url="http://api.example.com",
        token=None
    )
    
    assert session.name == "test-session"
    assert session.base_url == "http://api.example.com"
    assert session.token is None
    assert session.id is not None  # UUID should be generated


def test_session_creation_with_token():
    """Test creating a Session with a token."""
    session = Session(
        name="test-session",
        base_url="http://api.example.com",
        token="test-token"
    )
    
    assert session.name == "test-session"
    assert session.base_url == "http://api.example.com"
    assert session.token == "test-token"
    assert session.id is not None