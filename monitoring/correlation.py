#!/usr/bin/env python3
"""
Correlation ID module for request tracing across logs.
"""

import uuid
import os

_correlation_id = None


def generate_correlation_id():
    """Generate new correlation ID for workflow run."""
    global _correlation_id
    _correlation_id = str(uuid.uuid4())[:8]  # Short ID for readability
    os.environ['CORRELATION_ID'] = _correlation_id
    print(f"Generated correlation ID: {_correlation_id}")
    return _correlation_id


def get_correlation_id():
    """Get current correlation ID."""
    return _correlation_id or os.environ.get('CORRELATION_ID', 'unknown')


def set_correlation_id(corr_id):
    """Set correlation ID from external source (e.g., environment)."""
    global _correlation_id
    _correlation_id = corr_id
    os.environ['CORRELATION_ID'] = corr_id


if __name__ == "__main__":
    cid = generate_correlation_id()
    print(f"Generated: {cid}")
    print(f"Retrieved: {get_correlation_id()}")
