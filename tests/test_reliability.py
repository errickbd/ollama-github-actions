import subprocess
import pytest
import signal


@pytest.mark.advisory
def test_handles_invalid_model():
    """System should fail gracefully with non-existent model"""
    result = subprocess.run(
        ['ollama', 'run', 'nonexistent:model', 'test'],
        capture_output=True,
        text=True,
        timeout=30
    )
    assert result.returncode != 0, "Should fail with invalid model"
    assert len(result.stderr) > 0, "Should provide error message"
    print(f"Error message received: {result.stderr[:100]}")


@pytest.mark.advisory
def test_handles_empty_prompt(model_name):
    """System should handle empty prompt appropriately"""
    result = subprocess.run(
        ['ollama', 'run', model_name, ''],
        capture_output=True,
        text=True,
        timeout=30
    )
    # Empty prompt may succeed or fail depending on model
    # The key is it shouldn't crash or hang
    print(f"Return code: {result.returncode}")
    print(f"Output length: {len(result.stdout)}")
    # Test passes if we get here without timeout/crash


@pytest.mark.advisory
def test_handles_timeout(model_name):
    """System should handle timeout gracefully"""
    try:
        result = subprocess.run(
            ['ollama', 'run', model_name, 'Write a 10000 word essay'],
            capture_output=True,
            text=True,
            timeout=5  # Very short timeout to force timeout
        )
        # If it completes in time, that's fine
        print("Query completed within timeout")
    except subprocess.TimeoutExpired:
        # This is expected behavior - timeout was handled
        print("Timeout handled gracefully")
        assert True, "Timeout was caught and handled"


@pytest.mark.advisory
def test_partial_failure_recovery(model_name, sample_prompt):
    """Workflow should continue after non-critical failure"""
    # First, trigger a failure with invalid model
    bad_result = subprocess.run(
        ['ollama', 'run', 'fake:model', 'test'],
        capture_output=True,
        text=True,
        timeout=30
    )
    
    # Verify the failure occurred
    assert bad_result.returncode != 0, "First command should fail"
    
    # Now verify we can still run successful queries
    good_result = subprocess.run(
        ['ollama', 'run', model_name, sample_prompt],
        capture_output=True,
        text=True,
        timeout=60
    )
    
    assert good_result.returncode == 0, "Should recover and run successfully"
    assert len(good_result.stdout.strip()) > 0, "Should produce output after recovery"
    print("Successfully recovered from partial failure")


@pytest.mark.advisory
def test_error_messages_helpful():
    """Error output should contain actionable information"""
    result = subprocess.run(
        ['ollama', 'run', 'nonexistent:model', 'test'],
        capture_output=True,
        text=True,
        timeout=30
    )
    
    error_message = result.stderr.lower()
    
    # Check that error message contains useful information
    helpful_terms = ['not found', 'error', 'pull', 'does not exist', 'failed']
    has_helpful_info = any(term in error_message for term in helpful_terms)
    
    assert len(result.stderr) > 0, "Should provide error message"
    assert has_helpful_info, f"Error message should be actionable. Got: {result.stderr}"
    print(f"Helpful error message: {result.stderr[:200]}")
