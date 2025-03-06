import pytest
from src.models.playbook.validator import PlaybookYamlValidator
from src.models.playbook.config import PlaybookConfig, PlaybookStep


def test_validate_minimal_valid_yaml():
    """Test validating a minimal valid YAML playbook."""
    yaml_content = """
    session: test-session
    steps:
      - method: GET
        endpoint: /users
    """
    
    config = PlaybookYamlValidator.validate_and_load(yaml_content)
    
    assert isinstance(config, PlaybookConfig)
    assert config.session_name == "test-session"
    assert len(config.steps) == 1
    assert config.steps[0].method == "GET"
    assert config.steps[0].endpoint == "/users"


def test_validate_complete_valid_yaml():
    """Test validating a complete valid YAML playbook with all fields."""
    yaml_content = """
    session: test-session
    steps:
      - method: POST
        endpoint: /users
        headers:
          Content-Type: application/json
          X-Custom-Header: value
        data:
          name: John
          email: john@example.com
    """
    
    config = PlaybookYamlValidator.validate_and_load(yaml_content)
    
    assert config.session_name == "test-session"
    assert len(config.steps) == 1
    step = config.steps[0]
    assert step.method == "POST"
    assert step.endpoint == "/users"
    assert step.headers["Content-Type"] == "application/json"
    assert step.headers["X-Custom-Header"] == "value"
    assert step.data["name"] == "John"
    assert step.data["email"] == "john@example.com"


def test_validate_multiple_steps():
    """Test validating a playbook with multiple steps."""
    yaml_content = """
    session: test-session
    steps:
      - method: GET
        endpoint: /users
      - method: POST
        endpoint: /users
        data:
          name: John
    """
    
    config = PlaybookYamlValidator.validate_and_load(yaml_content)
    
    assert len(config.steps) == 2
    assert config.steps[0].method == "GET"
    assert config.steps[1].method == "POST"
    assert config.steps[1].data == {"name": "John"}


def test_invalid_yaml_format():
    """Test that invalid YAML format raises ValueError."""
    yaml_content = """
    session: test-session
    steps:
      - method: GET
        endpoint: /users
      invalid yaml content
    """
    
    with pytest.raises(ValueError, match="Invalid YAML format"):
        PlaybookYamlValidator.validate_and_load(yaml_content)


def test_missing_required_fields():
    """Test that missing required fields raise ValueError."""
    yaml_content = """
    steps:
      - method: GET
        endpoint: /users
    """
    
    with pytest.raises(ValueError, match="Missing required fields: session"):
        PlaybookYamlValidator.validate_and_load(yaml_content)


def test_invalid_step_format():
    """Test that invalid step format raises ValueError."""
    yaml_content = """
    session: test-session
    steps:
      - method: GET
    """
    
    with pytest.raises(ValueError, match="Step 1 missing required fields: endpoint"):
        PlaybookYamlValidator.validate_and_load(yaml_content)


def test_invalid_method():
    """Test that invalid HTTP method raises ValueError."""
    yaml_content = """
    session: test-session
    steps:
      - method: INVALID
        endpoint: /users
    """
    
    with pytest.raises(ValueError, match="Step 1 has invalid method"):
        PlaybookYamlValidator.validate_and_load(yaml_content)


def test_method_case_normalization():
    """Test that HTTP methods are normalized to uppercase."""
    yaml_content = """
    session: test-session
    steps:
      - method: get
        endpoint: /users
    """
    
    config = PlaybookYamlValidator.validate_and_load(yaml_content)
    assert config.steps[0].method == "GET" 