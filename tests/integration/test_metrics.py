import json
import os
import pytest
from datetime import datetime
from typing import Dict, Any, List

from src.modules.playbook.playbook import Playbook
from src.modules.session.session_store import SessionStore
from src.modules.logging.base import BaseLogger
from tests.utils.test_logger import create_test_logger

@pytest.fixture
def test_logger() -> BaseLogger:
    """Create a test logger instance."""
    return create_test_logger()

def load_metrics_output(output_file: str) -> Dict[str, Any]:
    """Load and parse the metrics output file."""
    with open(output_file, 'r') as f:
        return json.load(f)

def validate_metrics_structure(metrics: Dict[str, Any]) -> None:
    """Validate the basic structure of the metrics output."""
    assert "requests" in metrics, "Missing requests section"
    assert "steps" in metrics, "Missing steps section"
    assert "phases" in metrics, "Missing phases section"
    assert "playbook" in metrics, "Missing playbook section"

def validate_request_metrics(request: Dict[str, Any]) -> None:
    """Validate a single request's metrics."""
    # Required fields
    assert "method" in request, "Request missing method"
    assert "endpoint" in request, "Request missing endpoint"
    assert "start_time" in request, "Request missing start_time"
    assert "end_time" in request, "Request missing end_time"
    assert "status_code" in request, "Request missing status_code"
    assert "duration_ms" in request, "Request missing duration_ms"
    assert "success" in request, "Request missing success"
    
    # Validate types and constraints
    assert isinstance(request["duration_ms"], (int, float)), "duration_ms should be numeric"
    assert request["duration_ms"] >= 0, "duration_ms should be non-negative"
    
    # Memory usage should be non-negative
    if request["memory_usage_bytes"] is not None:
        assert request["memory_usage_bytes"] >= 0, "memory_usage_bytes should be non-negative"
    
    # CPU usage should be non-negative
    if request["cpu_percent"] is not None:
        assert request["cpu_percent"] >= 0, "cpu_percent should be non-negative"
    
    # Request size should be non-negative or null
    if request["request_size_bytes"] is not None:
        assert request["request_size_bytes"] >= 0, "request_size_bytes should be non-negative"
    
    # Response size should be non-negative or null
    if request["response_size_bytes"] is not None:
        assert request["response_size_bytes"] >= 0, "response_size_bytes should be non-negative"

def validate_phase_metrics(phase: Dict[str, Any]) -> None:
    """Validate a single phase's metrics."""
    # Required fields
    assert "name" in phase, "Phase missing name"
    assert "start_time" in phase, "Phase missing start_time"
    assert "end_time" in phase, "Phase missing end_time"
    assert "duration_ms" in phase, "Phase missing duration_ms"
    assert "parallel" in phase, "Phase missing parallel"
    
    # Validate types and constraints
    assert isinstance(phase["duration_ms"], (int, float)), "duration_ms should be numeric"
    assert phase["duration_ms"] >= 0, "duration_ms should be non-negative"
    
    # Memory usage should be non-negative
    if phase["memory_usage_bytes"] is not None:
        assert phase["memory_usage_bytes"] >= 0, "memory_usage_bytes should be non-negative"
    
    # CPU usage should be non-negative
    if phase["cpu_percent"] is not None:
        assert phase["cpu_percent"] >= 0, "cpu_percent should be non-negative"

def validate_playbook_metrics(playbook: Dict[str, Any]) -> None:
    """Validate the playbook's overall metrics."""
    # Required fields
    assert "start_time" in playbook, "Playbook missing start_time"
    assert "end_time" in playbook, "Playbook missing end_time"
    assert "duration_ms" in playbook, "Playbook missing duration_ms"
    assert "total_requests" in playbook, "Playbook missing total_requests"
    assert "successful_requests" in playbook, "Playbook missing successful_requests"
    assert "failed_requests" in playbook, "Playbook missing failed_requests"
    
    # Validate types and constraints
    assert isinstance(playbook["duration_ms"], (int, float)), "duration_ms should be numeric"
    assert playbook["duration_ms"] >= 0, "duration_ms should be non-negative"
    assert playbook["total_requests"] >= 0, "total_requests should be non-negative"
    assert playbook["successful_requests"] >= 0, "successful_requests should be non-negative"
    assert playbook["failed_requests"] >= 0, "failed_requests should be non-negative"
    
    # Memory usage should be non-negative
    if playbook["peak_memory_usage_bytes"] is not None:
        assert playbook["peak_memory_usage_bytes"] >= 0, "peak_memory_usage_bytes should be non-negative"
    
    # CPU usage should be non-negative
    if playbook["average_cpu_percent"] is not None:
        assert playbook["average_cpu_percent"] >= 0, "average_cpu_percent should be non-negative"

@pytest.mark.integration
async def test_metrics_collection(test_logger):
    """Integration test for metrics collection."""
    # Setup
    playbook_path = "examples/example-metrics-playbook.yml"
    output_file = "metrics_output.json"
    session_store = SessionStore()  # Create a new session store
    
    # Clean up previous output if it exists
    if os.path.exists(output_file):
        os.remove(output_file)
    
    # Load and execute the playbook
    with open(playbook_path, 'r') as f:
        playbook_content = f.read()
    
    playbook = Playbook.from_yaml(playbook_content, test_logger)
    await playbook.execute(session_store)  # Pass the session store to execute
    
    # Load and validate metrics
    assert os.path.exists(output_file), "Metrics output file not created"
    metrics = load_metrics_output(output_file)
    
    # Validate structure
    validate_metrics_structure(metrics)
    
    # Validate all requests
    for request in metrics["requests"]:
        validate_request_metrics(request)
    
    # Validate all phases
    for phase in metrics["phases"]:
        validate_phase_metrics(phase)
    
    # Validate playbook metrics
    validate_playbook_metrics(metrics["playbook"])
    
    # Additional validation for the example playbook
    assert len(metrics["requests"]) == 24, "Expected 24 requests"
    assert metrics["playbook"]["total_requests"] == 24, "Expected 24 total requests"
    assert metrics["playbook"]["successful_requests"] == 23, "Expected 23 successful requests"
    assert metrics["playbook"]["failed_requests"] == 1, "Expected 1 failed request"
    
    # Check for specific phases
    phase_names = {phase["name"] for phase in metrics["phases"]}
    expected_phases = {
        "Initialization",
        "Fetch User Details",
        "Create Posts",
        "Simulate Errors",
        "Large Data Processing",
        "CPU Intensive Operation"
    }
    assert phase_names == expected_phases, "Missing expected phases" 