from fastapi import APIRouter, Depends, HTTPException, status, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
import random
import string
import os
import logging
from datetime import timedelta

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 导入数据库和用户相关模块
from app.database import get_db
from app.core.config import settings
from app.core.security import create_access_token
from app.services.user import authenticate_user, update_login_info, create_user, get_user_by_username
from app.schemas.user import Token, UserCreate, UserLogin

# 创建路由
router = APIRouter(
    prefix="/auth",
    tags=["认证"],
    responses={404: {"description": "Not found"}},
)

# 模板目录
templates = Jinja2Templates(directory="templates")

# 模拟验证码存储
verification_codes = {}

# OAuth2 密码流
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")

# 获取随机验证码图片
def get_random_captcha_image():
    """
    从captcha文件夹中随机获取一个验证码图片，并返回图片名称（不含扩展名）作为验证码
    """
    try:
        captcha_dir = os.path.join("app", "static", "images", "captcha")
        
        # 确保目录存在
        if not os.path.exists(captcha_dir):
            logger.warning(f"验证码目录不存在: {captcha_dir}")
            os.makedirs(captcha_dir, exist_ok=True)
            return None, None
        
        # 获取所有png图片
        captcha_files = [f for f in os.listdir(captcha_dir) if f.endswith('.png')]
        
        if not captcha_files:
            logger.warning("验证码目录中没有PNG图片")
            return None, None
        
        # 随机选择一个图片
        selected_file = random.choice(captcha_files)
        
        # 使用文件名（不含.png扩展名）作为验证码
        captcha_code = os.path.splitext(selected_file)[0]
        
        # 构建图片相对路径，直接返回完整的静态文件URL
        image_path = f"/static/images/captcha/{selected_file}"
        
        logger.info(f"已选择验证码图片: {selected_file}, 路径: {image_path}")
        return captcha_code, image_path
    except Exception as e:
        logger.error(f"获取验证码图片时出错: {str(e)}")
        return None, None

# 生成随机验证码
def generate_verification_code():
    """生成随机5位验证码"""
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=5))

# 登录页面路由
@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """返回登录页面"""
    try:
        # 获取随机验证码图片
        captcha_code, captcha_image_path = get_random_captcha_image()
        
        # 如果没有获取到验证码图片，则使用生成的验证码
        if not captcha_code:
            captcha_code = generate_verification_code()
            captcha_image_path = "/static/images/captcha-placeholder.png"
            logger.warning(f"使用生成的验证码: {captcha_code}")
        
        # 存储验证码 (实际应用中应该与会话关联)
        verification_codes[request.client.host] = captcha_code
        
        logger.info(f"用户 {request.client.host} 的验证码: {captcha_code}")
        
        return templates.TemplateResponse(
            "login.html", 
            {
                "request": request, 
                "verification_code": captcha_code,
                "captcha_image_path": captcha_image_path
            }
        )
    except Exception as e:
        logger.error(f"生成登录页面时出错: {str(e)}")
        # 返回一个简单的错误页面
        return HTMLResponse(
            content=f"""
            <html>
                <head><title>Error</title></head>
                <body>
                    <h1>出错了</h1>
                    <p>加载登录页面时发生错误，请稍后再试。</p>
                    <p>错误详情: {str(e)}</p>
                </body>
            </html>
            """,
            status_code=500
        )

# 登录处理路由
@router.post("/login")
async def login(
    username: str = Form(...),
    password: str = Form(...),
    verification_code: str = Form(...),
    request: Request = None,
    db: Session = Depends(get_db)
):
    """处理登录请求"""
    try:
        # 检查验证码
        stored_code = verification_codes.get(request.client.host)
        logger.info(f"验证码比较: 输入={verification_code}, 存储={stored_code}")
        
        if not stored_code or stored_code.lower() != verification_code.lower():
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"detail": "验证码错误"}
            )
        
        # 验证用户
        user = authenticate_user(db, username, password)
        if not user:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "用户名或密码错误"}
            )
        
        # 更新用户登录信息
        client_host = request.client.host if request else None
        update_login_info(db, user.id, client_host)
        
        # 创建访问令牌
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            subject=user.username, expires_delta=access_token_expires
        )
        
        logger.info(f"用户 {username} 登录成功")
        
        # 创建响应并设置Cookie
        response = JSONResponse(content={
            "detail": "登录成功",
            "access_token": access_token,
            "token_type": "bearer",
            "username": user.username
        })
        
        # 将token设置到cookie中
        response.set_cookie(
            key="access_token",
            value=access_token,
            max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,  # 转换为秒
            httponly=True,  # 防止XSS攻击
            secure=False,   # 在HTTPS环境中应设置为True
            samesite="lax"  # CSRF保护
        )
        
        return response
    except Exception as e:
        logger.error(f"登录处理过程中出错: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": f"服务器错误: {str(e)}"}
        )

# OAuth2 token路由，用于其他客户端获取令牌
@router.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """获取访问令牌"""
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 更新用户登录信息
    update_login_info(db, user.id)
    
    # 创建访问令牌
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        subject=user.username, expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}

# 注册路由
@router.post("/register")
async def register(
    user_create: UserCreate,
    db: Session = Depends(get_db)
):
    """用户注册"""
    # 检查用户是否已存在
    db_user = get_user_by_username(db, username=user_create.username)
    if db_user:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"detail": "用户名已存在"}
        )
    
    # 创建新用户
    user = create_user(
        db=db,
        username=user_create.username,
        password=user_create.password,
        email=user_create.email
    )
    
    if not user:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "创建用户失败"}
        )
    
    # 返回成功消息
    return JSONResponse(
        content={"detail": "注册成功", "username": user.username}
    )

# 登出路由
@router.get("/logout")
async def logout():
    """处理登出请求"""
    response = RedirectResponse(url="/auth/login")
    # 清除access_token cookie
    response.delete_cookie(key="access_token")
    return response 