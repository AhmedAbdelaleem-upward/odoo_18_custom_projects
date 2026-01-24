# -*- coding: utf-8 -*-

from typing import Optional
from pydantic import BaseModel, EmailStr, Field, field_validator


# ============ Login Schemas ============

class LoginRequest(BaseModel):
    """Schema for login request"""
    login: str = Field(..., min_length=1, description="User's login (email or username)")
    password: str = Field(..., min_length=1, description="User's password")


class UserSchema(BaseModel):
    """Schema for user data in responses"""
    id: int = Field(..., description="User ID")
    email: str = Field(..., description="User's email")
    name: str = Field(..., description="User's name")
    phone: Optional[str] = Field(None, description="User's phone number")

    @field_validator('phone', mode='before')
    @classmethod
    def convert_false_to_none(cls, v):
        """Convert Odoo's False to None"""
        if v is False:
            return None
        return v


class TokenData(BaseModel):
    """Schema for token data in login response"""
    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    expires_in: int = Field(..., description="Access token expiry in seconds")
    token_type: str = Field(default="Bearer", description="Token type")
    user: UserSchema = Field(..., description="User information")


class LoginResponse(BaseModel):
    """Schema for login response"""
    success: bool = Field(..., description="Whether login was successful")
    data: Optional[TokenData] = Field(None, description="Token data if successful")
    message: Optional[str] = Field(None, description="Error message if failed")


# ============ Refresh Token Schemas ============

class RefreshTokenRequest(BaseModel):
    """Schema for refresh token request"""
    refresh_token: str = Field(..., description="JWT refresh token")


class RefreshTokenData(BaseModel):
    """Schema for refresh token response data"""
    access_token: str = Field(..., description="New JWT access token")
    refresh_token: str = Field(..., description="New JWT refresh token")
    expires_in: int = Field(..., description="Access token expiry in seconds")
    token_type: str = Field(default="Bearer", description="Token type")


class RefreshTokenResponse(BaseModel):
    """Schema for refresh token response"""
    success: bool = Field(..., description="Whether refresh was successful")
    data: Optional[RefreshTokenData] = Field(None, description="New token data")
    message: Optional[str] = Field(None, description="Error message if failed")
