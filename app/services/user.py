"""
用户服务模块，提供用户相关的数据库操作
"""
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
import datetime
import logging

from app.models.user import User
from app.core.security import get_password_hash, verify_password

# 设置日志
logger = logging.getLogger(__name__)

def get_user_by_username(db: Session, username: str):
    """
    通过用户名获取用户
    """
    return db.query(User).filter(User.username == username).first()

def get_user_by_email(db: Session, email: str):
    """
    通过邮箱获取用户
    """
    return db.query(User).filter(User.email == email).first()

def get_user_by_id(db: Session, user_id: int):
    """
    通过ID获取用户
    """
    return db.query(User).filter(User.id == user_id).first()

def create_user(db: Session, username: str, password: str, email: str = None, is_admin: bool = False):
    """
    创建新用户
    """
    try:
        hashed_password = get_password_hash(password)
        db_user = User(
            username=username,
            email=email,
            hashed_password=hashed_password,
            is_admin=is_admin
        )
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        logger.info(f"创建用户成功: {username}")
        return db_user
    except IntegrityError:
        db.rollback()
        logger.error(f"创建用户失败，用户名或邮箱已存在: {username}")
        return None
    except Exception as e:
        db.rollback()
        logger.error(f"创建用户时发生错误: {str(e)}")
        return None

def authenticate_user(db: Session, username: str, password: str):
    """
    验证用户
    """
    user = get_user_by_username(db, username)
    if not user:
        logger.warning(f"用户不存在: {username}")
        return False
    if not verify_password(password, user.hashed_password):
        logger.warning(f"密码错误: {username}")
        return False
    return user

def update_login_info(db: Session, user_id: int, ip_address: str = None):
    """
    更新用户登录信息
    """
    try:
        user = get_user_by_id(db, user_id)
        if user:
            user.last_login = datetime.datetime.utcnow()
            user.login_count += 1
            if ip_address:
                user.last_login_ip = ip_address
            db.commit()
            logger.info(f"更新用户登录信息成功: {user.username}")
            return True
        return False
    except Exception as e:
        db.rollback()
        logger.error(f"更新用户登录信息失败: {str(e)}")
        return False 