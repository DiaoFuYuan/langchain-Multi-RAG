"""
用户模型模块
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime
import datetime
from sqlalchemy.sql import func

from app.database import Base

class User(Base):
    """用户模型"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=True)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    
    # 记录用户登录信息
    last_login = Column(DateTime, nullable=True)
    login_count = Column(Integer, default=0)
    last_login_ip = Column(String(50), nullable=True)
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    def __repr__(self):
        return f"<User {self.username}>" 