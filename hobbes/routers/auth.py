import logging
import os
from ast import literal_eval
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from hobbes.core.service_iam import LDAPAuth, create_access_token, Token

logger = logging.getLogger(__name__)

access_token_expire_minutes = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "180"))

# Auth API router
auth_router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
    responses={404: {"description": "Not found"}},
)


@auth_router.post("/token", operation_id="authenticate")
async def login(form_data: Annotated[OAuth2PasswordRequestForm, Depends()]) -> Token:
    """
    Login API in form data (not JSON) format

    Args:
        form_data (Annotated[OAuth2PasswordRequestForm, Depends): Oauth form data

    Raises:
        HTTPException: failure to authenticate

    Returns:
        Token: JWT token
    """
    auth_scopes = LDAPAuth.authenticate(form_data.username, form_data.password)
    if not auth_scopes:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=access_token_expire_minutes)
    access_token = await create_access_token(
        data={"sub": form_data.username, "scope": auth_scopes},
        expires_delta=access_token_expires,
    )
    return Token(access_token=access_token, token_type="bearer")
