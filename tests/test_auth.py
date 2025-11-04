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
    credentials = HTTPBasicCredentials(username="admin", password="password")
    result = get_admin_user(credentials)
    assert result == "admin"


def test_admin_auth_wrong_username():
    """Test admin authentication with wrong username."""
    credentials = HTTPBasicCredentials(username="wrong", password="password")
    with pytest.raises(HTTPException) as exc_info:
        get_admin_user(credentials)
    assert exc_info.value.status_code == 401


def test_admin_auth_wrong_password():
    """Test admin authentication with wrong password."""
    credentials = HTTPBasicCredentials(username="admin", password="wrong")
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
    credentials = HTTPBasicCredentials(username="Admin", password="password")
    with pytest.raises(HTTPException) as exc_info:
        get_admin_user(credentials)
    assert exc_info.value.status_code == 401


def test_admin_auth_case_sensitive_password():
    """Test that password is case-sensitive."""
    credentials = HTTPBasicCredentials(username="admin", password="Password")
    with pytest.raises(HTTPException) as exc_info:
        get_admin_user(credentials)
    assert exc_info.value.status_code == 401
