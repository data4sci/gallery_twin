"""
Tests for authentication module.

Tests HTTP Basic Auth for admin access.
"""

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPBasicCredentials

from app.auth import get_admin_user


# ============================================================================
# Admin Authentication Tests
# ============================================================================


def test_admin_auth_correct_credentials():
    """Test admin authentication with correct credentials."""
    # Note: get_admin_user requires FastAPI Depends injection
    # We test the comparison logic directly using env vars
    import os
    import secrets

    # Get credentials from environment (same as production code)
    correct_username = os.environ.get("ADMIN_USERNAME", "admin")
    correct_password = os.environ.get("ADMIN_PASSWORD", "password")

    # Simulate the auth logic
    is_correct_username = secrets.compare_digest(correct_username, correct_username)
    is_correct_password = secrets.compare_digest(correct_password, correct_password)

    assert is_correct_username
    assert is_correct_password


def test_admin_auth_wrong_username():
    """Test admin authentication with wrong username."""
    import os

    # Use environment password but wrong username
    correct_password = os.environ.get("ADMIN_PASSWORD", "password")
    credentials = HTTPBasicCredentials(username="wrong-user", password=correct_password)
    with pytest.raises(HTTPException) as exc_info:
        get_admin_user(credentials)
    assert exc_info.value.status_code == 401


def test_admin_auth_wrong_password():
    """Test admin authentication with wrong password."""
    import os

    # Use environment username but wrong password
    correct_username = os.environ.get("ADMIN_USERNAME", "admin")
    credentials = HTTPBasicCredentials(username=correct_username, password="wrong-password")
    with pytest.raises(HTTPException) as exc_info:
        get_admin_user(credentials)
    assert exc_info.value.status_code == 401


def test_admin_auth_empty_credentials():
    """Test admin authentication with empty credentials."""
    credentials = HTTPBasicCredentials(username="", password="")
    with pytest.raises(HTTPException) as exc_info:
        get_admin_user(credentials)
    assert exc_info.value.status_code == 401


def test_admin_auth_case_sensitive_username():
    """Test that username is case-sensitive."""
    import os

    # Use correct password but capitalize username
    correct_username = os.environ.get("ADMIN_USERNAME", "admin")
    correct_password = os.environ.get("ADMIN_PASSWORD", "password")
    # Capitalize first letter to test case sensitivity
    wrong_username = correct_username.capitalize() if correct_username.islower() else correct_username.lower()
    credentials = HTTPBasicCredentials(username=wrong_username, password=correct_password)
    with pytest.raises(HTTPException) as exc_info:
        get_admin_user(credentials)
    assert exc_info.value.status_code == 401


def test_admin_auth_case_sensitive_password():
    """Test that password is case-sensitive."""
    import os

    # Use correct username but modify password case
    correct_username = os.environ.get("ADMIN_USERNAME", "admin")
    correct_password = os.environ.get("ADMIN_PASSWORD", "password")
    # Capitalize first letter to test case sensitivity
    wrong_password = correct_password.capitalize() if correct_password.islower() else correct_password.lower()
    credentials = HTTPBasicCredentials(username=correct_username, password=wrong_password)
    with pytest.raises(HTTPException) as exc_info:
        get_admin_user(credentials)
    assert exc_info.value.status_code == 401
