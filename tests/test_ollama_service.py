import subprocess
import pytest
import os


@pytest.mark.critical
def test_ollama_installed():
    """Verify Ollama CLI is installed and accessible"""
    result = subprocess.run(
        ['ollama', '--version'],
        capture_output=True,
        text=True
    )
    assert result.returncode == 0, "Ollama not installed or not in PATH"
    assert 'ollama version' in result.stdout.lower(), "Unexpected version output"


@pytest.mark.critical
def test_ollama_service_responding(ollama_available):
    """Verify Ollama service responds to requests"""
    assert ollama_available, "Ollama service is not responding. Is 'ollama serve' running?"


@pytest.mark.critical
def test_model_available(model_name):
    """Verify required model is available in Ollama"""
    result = subprocess.run(
        ['ollama', 'list'],
        capture_output=True,
        text=True
    )
    assert result.returncode == 0, "Failed to list models"
    assert model_name in result.stdout, f"Model {model_name} not found. Run 'ollama pull {model_name}'"


@pytest.mark.critical
def test_model_loads_successfully(model_name, sample_prompt):
    """Verify model can process a simple prompt"""
    result = subprocess.run(
        ['ollama', 'run', model_name, sample_prompt],
        capture_output=True,
        text=True,
        timeout=60
    )
    assert result.returncode == 0, f"Model failed to run: {result.stderr}"
    assert len(result.stdout.strip()) > 0, "Model returned empty response"


@pytest.mark.advisory
def test_cache_directory_exists():
    """Verify Ollama cache directory exists"""
    cache_dir = os.path.expanduser('~/.ollama')
    assert os.path.exists(cache_dir), f"Cache directory {cache_dir} does not exist"
    assert os.path.isdir(cache_dir), f"{cache_dir} is not a directory"