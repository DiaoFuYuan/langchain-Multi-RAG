"""
身份验证依赖项模块
用于替代中间件的身份验证方案
"""

from fastapi import Request, HTTPException, status
from fastapi.responses import RedirectResponse
from jose import jwt, JWTError
import logging

logger = logging.getLogger(__name__)

# 导入安全配置
try:
    from app.core.security import SECRET_KEY, ALGORITHM
except ImportError:
    SECRET_KEY = '09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7'
    ALGORITHM = 'HS256'

def require_auth_redirect(request: Request):
    """
    身份验证依赖项，失败时重定向到登录页面
    用于页面路由
    """
    try:
        # 尝试从cookie中获取token
        token = request.cookies.get("access_token")
        
        if not token:
            logger.info(f"用户未登录，重定向到登录页面: {request.url.path}")
            raise HTTPException(
                status_code=status.HTTP_307_TEMPORARY_REDIRECT,
                detail="未登录",
                headers={"Location": "/auth/login"}
            )
        
        # 验证token
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            username = payload.get("sub")
            if not username:
                raise JWTError("Invalid token")
            
            logger.info(f"用户 {username} 已通过身份验证")
            return username
            
        except JWTError:
            logger.info(f"Token无效，重定向到登录页面: {request.url.path}")
            raise HTTPException(
                status_code=status.HTTP_307_TEMPORARY_REDIRECT,
                detail="Token无效",
                headers={"Location": "/auth/login"}
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"身份验证检查出错: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_307_TEMPORARY_REDIRECT,
            detail="身份验证服务出错",
            headers={"Location": "/auth/login"}
        )

def require_auth_api(request: Request):
    """
    身份验证依赖项，失败时返回401错误
    用于API路由
    """
    try:
        # 尝试从cookie中获取token
        token = request.cookies.get("access_token")
        
        if not token:
            logger.info(f"API请求未提供token: {request.url.path}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="未登录或登录已过期"
            )
        
        # 验证token
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            username = payload.get("sub")
            if not username:
                raise JWTError("Invalid token")
            
            logger.info(f"API用户 {username} 已通过身份验证")
            return username
            
        except JWTError:
            logger.info(f"API请求token无效: {request.url.path}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token无效，请重新登录"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"API身份验证检查出错: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="身份验证服务出错"
        ) 