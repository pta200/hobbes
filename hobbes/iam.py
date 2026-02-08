import logging
import os
from ast import literal_eval
from datetime import datetime, timedelta, timezone
from typing import Annotated

import jwt
import ldap3
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import (
    OAuth2PasswordBearer,
    OAuth2PasswordRequestForm,
    SecurityScopes,
)
from jwt.exceptions import InvalidTokenError
from ldap3.core.exceptions import LDAPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)

testing_mode = int(os.getenv("TESTING_MODE", "0"))
jwt_key = os.getenv("JWT_KEY", "abc123Test")
jwt_alg = os.getenv("JWT_ALG", "HS256")
auth_domain = os.getenv("LDAP_AUTH_DOMAIN")
ldap_urls = literal_eval(os.getenv("LDAP_URLS", "[]"))
receive_timeout = int(os.getenv("LDAP_RECEIVE_TIMEOUT", "45"))
time_limit = int(os.getenv("LDAP_TIME_LIMIT", "45"))
connect_timeout = int(os.getenv("LDAP_CONNECT_TIMEOUT", "10"))
access_token_expire_minutes = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "180"))


class LDAPAuthException(Exception):
    """exceptions generated from LDAPHandler class"""


class LDAPAuth:
    """
    Class authenticate against LDAP and return user permission scope list e.g. read|write
    """

    @staticmethod
    def authenticate(username: str, password: str):
        """
        Bind to AD with username and password. Append auth domain to username

        Args:
            username (str): client username
            password (str): client password

        Returns:
            list[str]: list of permissions default to ["read", "write"] for now
        """
        connection = None
        try:
            if testing_mode == 1:
                logger.debug("testing so return")
                return ["read", "write"]

            servers = []
            for url in ldap_urls:
                servers.append(ldap3.Server(host=url, connect_timeout=connect_timeout))

            pool = ldap3.ServerPool(servers, pool_strategy=ldap3.FIRST, active=True, exhaust=True)

            connection = ldap3.Connection(
                server=pool,
                user=f"{username}@{auth_domain}",
                password=password,
                auto_bind=True,
                raise_exceptions=True,
                receive_timeout=receive_timeout,
                client_strategy=ldap3.SAFE_SYNC,
            )
            logger.debug("ldap auth success.....")

            return ["read", "write"]

        except (LDAPException, Exception) as error:
            logger.exception(error)
            return None

        finally:
            if connection:
                connection.unbind()


class Token(BaseModel):
    """Bearer Token to send to client"""

    access_token: str
    token_type: str


class TokenData(BaseModel):
    """Internal Token object"""

    username: str
    scopes: list[str] = []


# Token scheme for use with Security configuration
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="auth/token",
    scopes={"read": "consume read API", "write": "consume write API"},
)


async def validate_token(security_scopes: SecurityScopes, token: Annotated[str, Depends(oauth2_scheme)]) -> TokenData:
    """
    Validate oauth bearer token sent in client request authorization header

    Args:
        security_scopes (SecurityScopes): permissions required for consuming the APIs e.g. read|write
        token (Annotated[str, Depends): client token

    Raises:
        credentials_exception: token validation failure

    Returns:
        TokenData: username and scope
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="invalid token",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, jwt_key, algorithms=[jwt_alg])
        # validate username in JWT subject claim
        username = payload.get("sub")
        if username is None:
            raise credentials_exception

        # validate permissions in JWT scope claim
        token_scopes = payload.get("scope", [])
        for scope in security_scopes.scopes:
            if scope not in token_scopes:
                raise credentials_exception

        return TokenData(scopes=token_scopes, username=username)

    except InvalidTokenError:
        raise credentials_exception


async def create_access_token(data: dict, expires_delta: timedelta) -> str:
    """
    create JWT token

    Args:
        data (dict): claims to add to token e.g. sub|scope
        expires_delta (timedelta): token expiration delta

    Returns:
        str: token
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + expires_delta
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, jwt_key, algorithm="HS256")
    return encoded_jwt


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
        data={"sub": form_data.username, "scope": auth_scopes}, expires_delta=access_token_expires
    )
    return Token(access_token=access_token, token_type="bearer")
