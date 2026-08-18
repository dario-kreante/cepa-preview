from pydantic import BaseModel


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class AccessTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class CanjearCodigoRequest(BaseModel):
    """Canje del código de un solo uso emitido por el ACS SAML."""

    code: str
