import subprocess
import pytest
import time
import os


@pytest.mark.critical
def test_ai_response_time(model_name, sample_prompt):
    """AI queries must complete within 30 seconds"""
    start = time.time()
    result = subprocess.run(
        ['ollama', 'run', model_name, sample_prompt],
        capture_output=True,
        text=True,
        timeout=45
    )
    duration = time.time() - start
    
    print(f"Query completed in {duration:.1f}s")
    assert result.returncode == 0, f"Query failed: {result.stderr}"
    assert duration < 30, f"Query took {duration:.1f}s, exceeds 30s threshold"


@pytest.mark.advisory
def test_ai_response_time_warning(model_name, sample_prompt):
    """Warn if AI query takes longer than optimal 15 seconds"""
    start = time.time()
    result = subprocess.run(
        ['ollama', 'run', model_name, sample_prompt],
        capture_output=True,
        text=True,
        timeout=45
    )
    duration = time.time() - start
    
    print(f"Query completed in {duration:.1f}s")
    assert result.returncode == 0, f"Query failed: {result.stderr}"
    if duration > 15:
        pytest.warns(UserWarning, match="Performance below optimal")
    assert duration < 15, f"Query took {duration:.1f}s, exceeds optimal 15s threshold"


@pytest.mark.critical
def test_model_load_time(model_name):
    """Cold start query must complete within 45 seconds"""
    prompt = "Say hello"
    start = time.time()
    result = subprocess.run(
        ['ollama', 'run', model_name, prompt],
        capture_output=True,
        text=True,
        timeout=60
    )
    duration = time.time() - start
    
    print(f"Cold start completed in {duration:.1f}s")
    assert result.returncode == 0, f"Cold start failed: {result.stderr}"
    assert duration < 45, f"Cold start took {duration:.1f}s, exceeds 45s threshold"


@pytest.mark.advisory
def test_cache_improves_performance(model_name, sample_prompt):
    """Second query should be faster than first query"""
    # First query (potentially cold)
    start1 = time.time()
    subprocess.run(
        ['ollama', 'run', model_name, sample_prompt],
        capture_output=True,
        text=True,
        timeout=45
    )
    duration1 = time.time() - start1
    
    # Second query (should be warmed up)
    start2 = time.time()
    subprocess.run(
        ['ollama', 'run', model_name, sample_prompt],
        capture_output=True,
        text=True,
        timeout=45
    )
    duration2 = time.time() - start2
    
    print(f"First query: {duration1:.1f}s, Second query: {duration2:.1f}s")
    improvement = ((duration1 - duration2) / duration1) * 100 if duration1 > 0 else 0
    print(f"Performance improvement: {improvement:.1f}%")
    
    # Advisory: warn if no improvement, but don't fail
    if duration2 >= duration1:
        print("WARNING: No performance improvement detected from caching")


@pytest.mark.critical
def test_response_not_empty(model_name, sample_prompt):
    """AI response must contain actual content"""
    result = subprocess.run(
        ['ollama', 'run', model_name, sample_prompt],
        capture_output=True,
        text=True,
        timeout=45
    )
    
    assert result.returncode == 0, f"Query failed: {result.stderr}"
    response = result.stdout.strip()
    assert len(response) > 0, "Response is empty"
    assert len(response.split()) >= 1, "Response contains no words"
    print(f"Response length: {len(response)} characters, {len(response.split())} words")


@pytest.fixture
def timing_report(test_output_dir):
    """Create a timing report file for artifact upload"""
    report_path = test_output_dir / "timing_report.txt"
    
    # Initialize report
    with open(report_path, 'w') as f:
        f.write("Performance Timing Report\n")
        f.write("=" * 40 + "\n")
        f.write(f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
    
    yield report_path
    
    # Report is available for upload after tests complete
    print(f"Timing report saved to: {report_path}")
