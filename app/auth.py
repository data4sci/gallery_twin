import os
import secrets

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

security = HTTPBasic()


def get_admin_user(credentials: HTTPBasicCredentials = Depends(security)):
    """Simple HTTP Basic auth for admin routes."""
    correct_username = os.environ.get("ADMIN_USERNAME", "admin")
    correct_password = os.environ.get("ADMIN_PASSWORD", "password")

    is_correct_username = secrets.compare_digest(
        credentials.username, correct_username
    )
    is_correct_password = secrets.compare_digest(
        credentials.password, correct_password
    )

    if not (is_correct_username and is_correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username
