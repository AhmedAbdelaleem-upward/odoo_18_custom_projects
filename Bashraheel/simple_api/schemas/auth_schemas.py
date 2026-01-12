from typing import Optional
from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    """Schema for login request"""
    email: EmailStr = Field(..., description="User's email", example="user@example.com")
    password: str = Field(..., min_length=1, description="User's password")

    class Config:
        json_schema_extra = {
            "example": {
                "email": "admin@example.com",
                "password": "admin"
            }
        }


class UserSchema(BaseModel):
    """Schema for user information"""
    id: int = Field(..., description="Partner ID")
    email: str = Field(..., description="User email")
    name: str = Field(..., description="Full name")
    phone: Optional[str] = Field(None, description="Phone number")


class TokenData(BaseModel):
    """Schema for token data in login response"""
    access_token: str = Field(..., description="JWT Access Token")
    refresh_token: str = Field(..., description="JWT Refresh Token")
    expires_in: int = Field(..., description="Token expiry in seconds")
    user: UserSchema = Field(..., description="User information")


class LoginResponse(BaseModel):
    """Schema for successful login response"""
    success: bool = Field(default=True)
    data: TokenData


class RefreshTokenRequest(BaseModel):
    """Schema for refresh token request"""
    refresh_token: str = Field(..., description="Valid refresh token")


class RefreshTokenData(BaseModel):
    """Schema for refresh token response data"""
    access_token: str = Field(..., description="New JWT Access Token")
    refresh_token: str = Field(..., description="JWT Refresh Token")
    expires_in: int = Field(..., description="Token expiry in seconds")


class RefreshTokenResponse(BaseModel):
    """Schema for successful refresh response"""
    success: bool = Field(default=True)
    data: RefreshTokenData
