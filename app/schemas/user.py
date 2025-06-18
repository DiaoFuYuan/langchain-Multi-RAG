"""
用户模式模块，定义用户相关的Pydantic模型
"""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime

# 用户基础模式
class UserBase(BaseModel):
    username: str
    email: Optional[EmailStr] = None

# 创建用户请求
class UserCreate(UserBase):
    password: str = Field(..., min_length=6, max_length=100)

# 登录请求
class UserLogin(BaseModel):
    username: str
    password: str

# 用户信息响应
class UserResponse(UserBase):
    id: int
    is_active: bool
    is_admin: bool
    last_login: Optional[datetime] = None
    login_count: int
    created_at: datetime
    
    model_config = {
        "from_attributes": True
    }

# 令牌模式
class Token(BaseModel):
    access_token: str
    token_type: str

# 令牌数据
class TokenData(BaseModel):
    username: Optional[str] = None 