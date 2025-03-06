import pytest
from src.models.playbook.playbook import Playbook
from src.models.playbook.config import PlaybookConfig, PlaybookStep


def test_playbook_creation_from_config():
    """Test creating a Playbook from a PlaybookConfig."""
    step = PlaybookStep(method="GET", endpoint="/users")
    config = PlaybookConfig(session_name="test-session", steps=[step])
    
    playbook = Playbook(config)
    
    assert playbook.session_name == "test-session"
    assert len(playbook.steps) == 1
    assert playbook.steps[0] == step


def test_playbook_from_yaml():
    """Test creating a Playbook from YAML content."""
    yaml_content = """
    session: test-session
    steps:
      - method: GET
        endpoint: /users
    """
    
    playbook = Playbook.from_yaml(yaml_content)
    
    assert playbook.session_name == "test-session"
    assert len(playbook.steps) == 1
    assert playbook.steps[0].method == "GET"
    assert playbook.steps[0].endpoint == "/users"


def test_playbook_to_dict():
    """Test converting a Playbook to a dictionary."""
    step = PlaybookStep(
        method="POST",
        endpoint="/users",
        headers={"Content-Type": "application/json"},
        data={"name": "John"}
    )
    config = PlaybookConfig(session_name="test-session", steps=[step])
    playbook = Playbook(config)
    
    result = playbook.to_dict()
    
    assert result == {
        "session": "test-session",
        "steps": [
            {
                "method": "POST",
                "endpoint": "/users",
                "headers": {"Content-Type": "application/json"},
                "data": {"name": "John"}
            }
        ]
    }


def test_playbook_to_dict_minimal():
    """Test converting a minimal Playbook to a dictionary."""
    step = PlaybookStep(method="GET", endpoint="/users")
    config = PlaybookConfig(session_name="test-session", steps=[step])
    playbook = Playbook(config)
    
    result = playbook.to_dict()
    
    assert result == {
        "session": "test-session",
        "steps": [
            {
                "method": "GET",
                "endpoint": "/users"
            }
        ]
    }


def test_invalid_yaml():
    """Test that invalid YAML raises ValueError."""
    yaml_content = "invalid: yaml: content: -"
    
    with pytest.raises(ValueError):
        Playbook.from_yaml(yaml_content) 