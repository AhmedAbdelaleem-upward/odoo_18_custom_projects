from typing import List
from pydantic import BaseModel, Field


class ProductItem(BaseModel):
    """Schema for product in list"""
    id: int = Field(..., description="Product ID")
    name: str = Field(..., description="Product name")


class ProductListResponse(BaseModel):
    """Response schema for product list"""
    success: bool = True
    data: List[ProductItem]
    count: int


class ProductDetail(BaseModel):
    """Schema for single product"""
    id: int
    name: str


class ProductResponse(BaseModel):
    """Response schema for single product"""
    success: bool = True
    data: ProductDetail


class ProductCreateRequest(BaseModel):
    """Schema for creating product"""
    name: str = Field(..., min_length=1, description="Product name")
