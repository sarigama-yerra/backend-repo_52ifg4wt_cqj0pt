"""
Database Schemas

Define your MongoDB collection schemas here using Pydantic models.
These schemas are used for data validation in your application.

Each Pydantic model represents a collection in your database.
Model name is converted to lowercase for the collection name:
- User -> "user" collection
- Product -> "product" collection
- BlogPost -> "blogs" collection
"""

from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List
from datetime import datetime

class FlashSale(BaseModel):
    discount_percent: int = Field(..., ge=1, le=95, description="Discount percentage for the sale")
    ends_at: datetime = Field(..., description="When the flash sale ends (UTC)")

class User(BaseModel):
    """
    Users collection schema
    Collection name: "user" (lowercase of class name)
    """
    name: str = Field(..., description="Full name")
    email: EmailStr = Field(..., description="Email address")
    password_hash: str = Field(..., description="BCrypt password hash")
    avatar_url: Optional[str] = Field(None, description="Avatar image URL")
    is_active: bool = Field(True, description="Whether user is active")

class Product(BaseModel):
    """
    Products collection schema
    Collection name: "product" (lowercase of class name)
    """
    title: str = Field(..., description="Product title")
    description: Optional[str] = Field(None, description="Product description")
    price: float = Field(..., ge=0, description="Price in dollars")
    category: str = Field(..., description="Product category")
    images: List[str] = Field(default_factory=list, description="Image URLs")
    seller_id: Optional[str] = Field(None, description="Owner user id")
    flash_sale: Optional[FlashSale] = None
    in_stock: bool = Field(True, description="Whether product is in stock")

class CartItem(BaseModel):
    user_id: str = Field(..., description="User ID owning this cart")
    product_id: str = Field(..., description="Product ID")
    quantity: int = Field(1, ge=1, le=10)

# Public/Request models (not collections)
class RegisterRequest(BaseModel):
    name: str
    email: EmailStr
    password: str

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class ProductCreate(BaseModel):
    title: str
    description: Optional[str] = None
    price: float
    category: str
    images: List[str] = []
    flash_sale: Optional[FlashSale] = None
    in_stock: bool = True

class ProductOut(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    price: float
    category: str
    images: List[str] = []
    seller_id: Optional[str] = None
    flash_sale: Optional[FlashSale] = None
    in_stock: bool = True

class CartItemOut(BaseModel):
    id: str
    product_id: str
    quantity: int

# Note: The Flames database viewer will automatically:
# 1. Read these schemas from GET /schema endpoint
# 2. Use them for document validation when creating/editing
# 3. Handle all database operations (CRUD) directly
# 4. You don't need to create any database endpoints!
