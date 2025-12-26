import pytest
import subprocess
import tempfile
import os


def pytest_configure(config):
    """Register custom markers for test categorization"""
    config.addinivalue_line("markers", "critical: mark test as critical (must pass)")
    config.addinivalue_line("markers", "advisory: mark test as advisory (can warn)")


@pytest.fixture
def ollama_available():
    """Check if Ollama service is responding"""
    result = subprocess.run(
        ['ollama', 'list'],
        capture_output=True,
        text=True,
        timeout=10
    )
    return result.returncode == 0


@pytest.fixture
def model_name():
    """Default model for testing"""
    return "llama3.2:1b"


@pytest.fixture
def sample_prompt():
    """Standard prompt for consistent testing"""
    return "Respond with exactly: TEST_PASSED"


@pytest.fixture
def test_output_dir():
    """Temporary directory for test outputs"""
    output_dir = tempfile.mkdtemp()
    return output_dir