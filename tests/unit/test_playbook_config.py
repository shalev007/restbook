from src.models.playbook.config import PlaybookConfig, PlaybookStep


def test_playbook_step_creation():
    """Test creating a PlaybookStep with minimal required fields."""
    step = PlaybookStep(
        method="GET",
        endpoint="/users"
    )
    assert step.method == "GET"
    assert step.endpoint == "/users"
    assert step.headers is None
    assert step.data is None


def test_playbook_step_creation_with_all_fields():
    """Test creating a PlaybookStep with all fields."""
    headers = {"Content-Type": "application/json"}
    data = {"name": "John"}
    
    step = PlaybookStep(
        method="POST",
        endpoint="/users",
        headers=headers,
        data=data
    )
    
    assert step.method == "POST"
    assert step.endpoint == "/users"
    assert step.headers == headers
    assert step.data == data


def test_playbook_config_creation():
    """Test creating a PlaybookConfig."""
    step = PlaybookStep(method="GET", endpoint="/users")
    config = PlaybookConfig(
        session_name="test-session",
        steps=[step]
    )
    
    assert config.session_name == "test-session"
    assert len(config.steps) == 1
    assert config.steps[0] == step


def test_playbook_config_create_step_from_dict():
    """Test creating a PlaybookStep from a dictionary using the factory method."""
    step_dict = {
        "method": "POST",
        "endpoint": "/users",
        "headers": {"Content-Type": "application/json"},
        "data": {"name": "John"}
    }
    
    step = PlaybookConfig.create_step(step_dict)
    
    assert step.method == "POST"
    assert step.endpoint == "/users"
    assert step.headers == step_dict["headers"]
    assert step.data == step_dict["data"]


def test_playbook_config_create_step_minimal_dict():
    """Test creating a PlaybookStep from a minimal dictionary."""
    step_dict = {
        "method": "GET",
        "endpoint": "/users"
    }
    
    step = PlaybookConfig.create_step(step_dict)
    
    assert step.method == "GET"
    assert step.endpoint == "/users"
    assert step.headers is None
    assert step.data is None 