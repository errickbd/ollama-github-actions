#!/usr/bin/env python3
"""
Test runner module for Ollama workflow validation.
Provides quick standalone validation complementing the pytest suite in tests/.
Use this for fast smoke tests; use pytest for comprehensive testing.
"""

import subprocess
import sys
from pathlib import Path


def run_command(command, timeout=30):
    """Execute command and return result."""
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return 1, "", "Command timed out"
    except Exception as e:
        return 1, "", str(e)
    
def test_ollama_service_health():
    """Verify Ollama service is responsive."""
    print("Testing Ollama service health...")
    exit_code, stdout, stderr = run_command(['ollama', '--version'])
    
    if exit_code == 0 and 'ollama version' in stdout.lower():
        print("✅ Ollama service health check passed")
        return True
    else:
        print(f"❌ Ollama service health check failed: {stderr}")
        return False
    
def test_model_availability():
    """Verify required model is available."""
    print("Testing model availability...")
    exit_code, stdout, stderr = run_command(['ollama', 'list'])
    
    if exit_code == 0 and 'llama3.2:1b' in stdout:
        print("✅ Model availability check passed")
        return True
    else:
        print(f"❌ Model availability check failed: {stderr}")
        return False
    
def test_basic_ai_functionality():
    """Test basic AI query and response."""
    print("Testing basic AI functionality...")
    exit_code, stdout, stderr = run_command([
        'ollama', 'run', 'llama3.2:1b',
        'Respond with exactly: TEST_PASSED'
    ], timeout=60)
    
    if exit_code == 0 and len(stdout.strip()) > 0:
        print("✅ AI functionality test passed")
        return True
    else:
        print(f"❌ AI functionality test failed: {stderr}")
        return False
    
def test_cache_directory_exists():
    """Verify cache directory was created."""
    print("Testing cache directory...")
    cache_dir = Path.home() / '.ollama'
    
    if cache_dir.exists():
        print(f"✅ Cache directory exists: {cache_dir}")
        return True
    else:
        print(f"❌ Cache directory missing: {cache_dir}")
        return False
    
def run_all_tests():
    """Run all workflow validation tests."""
    tests = [
        test_ollama_service_health,
        test_model_availability,
        test_basic_ai_functionality,
        test_cache_directory_exists
    ]
    
    print("=" * 50)
    print("OLLAMA WORKFLOW VALIDATION TESTS")
    print("=" * 50)
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()
    
    print("=" * 50)
    print(f"RESULTS: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed!")
        return True
    else:
        print(f"💥 {total - passed} tests failed!")
        return False

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)

