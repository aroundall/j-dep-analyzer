"""Pytest configuration and fixtures for j-dep-analyzer tests."""
from __future__ import annotations

import os
import pytest

# Force SQLite for all tests
os.environ["JDEP_DB_TYPE"] = "sqlite"


@pytest.fixture(autouse=True)
def reset_cached_engine():
    """Reset the cached database engine before and after each test.
    
    This ensures test isolation when tests modify the database config.
    """
    import main
    
    # Reset before test
    main._cached_engine = None
    
    yield
    
    # Reset after test
    main._cached_engine = None
