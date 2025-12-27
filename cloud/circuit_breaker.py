#!/usr/bin/env python3
"""
Circuit breaker pattern for resilient service calls.
Prevents cascading failures by failing fast when services are unavailable.
"""

from datetime import datetime, timedelta
from enum import Enum
import time


class CircuitState(Enum):
    CLOSED = "closed"       # Normal operation
    OPEN = "open"           # Failing fast
    HALF_OPEN = "half_open" # Testing recovery


class CircuitBreaker:
    """Circuit breaker that prevents repeated calls to failing services."""
    
    def __init__(self, failure_threshold=3, timeout_seconds=60):
        self.failure_threshold = failure_threshold
        self.timeout = timedelta(seconds=timeout_seconds)
        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitState.CLOSED
        
        print(f"Circuit breaker initialized: threshold={failure_threshold}, timeout={timeout_seconds}s")
    
    def call(self, func, *args, **kwargs):
        """Execute function with circuit breaker protection."""
        # Check if we should try again
        if self.state == CircuitState.OPEN:
            if datetime.now() - self.last_failure_time > self.timeout:
                print("Circuit breaker: HALF_OPEN, testing...")
                self.state = CircuitState.HALF_OPEN
            else:
                raise Exception("Circuit breaker is OPEN - failing fast")
        
        try:
            result = func(*args, **kwargs)
            
            # Success! Reset if we were testing
            if self.state == CircuitState.HALF_OPEN:
                print("Circuit breaker: CLOSED, recovered!")
                self.state = CircuitState.CLOSED
                self.failure_count = 0
            
            return result
        
        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = datetime.now()
            
            if self.failure_count >= self.failure_threshold:
                print(f"Circuit breaker: OPEN after {self.failure_count} failures")
                self.state = CircuitState.OPEN
            
            raise


def retry_with_backoff(func, max_attempts=3, base_delay=1):
    """Retry function with exponential backoff."""
    for attempt in range(max_attempts):
        try:
            return func()
        except Exception as e:
            if attempt == max_attempts - 1:
                print(f"All {max_attempts} attempts failed")
                raise
            
            delay = base_delay * (2 ** attempt)  # 1s, 2s, 4s
            print(f"Attempt {attempt + 1} failed: {e}")
            print(f"Retrying in {delay}s...")
            time.sleep(delay)


if __name__ == "__main__":
    print("=" * 50)
    print("Testing Circuit Breaker")
    print("=" * 50)
    
    cb = CircuitBreaker(failure_threshold=3, timeout_seconds=5)
    
    def failing_func():
        raise Exception("Service down")
    
    # Test state transitions
    for i in range(5):
        try:
            cb.call(failing_func)
        except Exception as e:
            print(f"Call {i + 1} failed: {e}")
        print(f"State: {cb.state.value}")
        print()
    
    print("=" * 50)
    print("Testing Retry with Backoff")
    print("=" * 50)
    
    attempt_count = 0
    
    def sometimes_fails():
        global attempt_count
        attempt_count += 1
        if attempt_count < 3:
            raise Exception("Not ready yet")
        return "Success!"
    
    result = retry_with_backoff(sometimes_fails, max_attempts=3, base_delay=1)
    print(f"Result: {result}")
