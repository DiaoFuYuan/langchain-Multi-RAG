from fastapi import FastAPI, Request, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from app.middleware.form_size_middleware import FormSizeMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text
import os
import datetime
import logging
from jose import jwt, JWTError

# 导入数据库
from app.database import db, get_db
# from app.core.config import settings  # 注释掉这个导入以避免ModuleNotFoundError

# 在模块级别导入安全相关常量
try:
    from app.core.security import SECRET_KEY, ALGORITHM
    security_imported = True
except ImportError as e:
    logging.error(f"无法导入安全模块: {e}")
    SECRET_KEY = '09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7'
    ALGORITHM = 'HS256'
    security_imported = False

# 设置日志
logger = logging.getLogger(__name__)

# 创建FastAPI应用实例
app = FastAPI(
    title="智能体平台",
    description="基于FastAPI的模块化网站",
    version="0.1.0",
)

# 设置静态文件目录 - 使用绝对路径
import os
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

app.mount("/static", StaticFiles(directory=os.path.join(base_dir, "app", "static")), name="static")

# 添加Font Awesome图标库静态文件挂载点
app.mount("/fontawesome", StaticFiles(directory=os.path.join(base_dir, "fontawesome")), name="fontawesome")

# 添加数据目录作为静态文件目录
app.mount("/data", StaticFiles(directory=os.path.join(base_dir, "data")), name="data")

# 设置模板目录
templates = Jinja2Templates(directory=os.path.join(base_dir, "templates"))

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有来源
    allow_credentials=True,
    allow_methods=["*"],  # 允许所有方法
    allow_headers=["*"],  # 允许所有头
)

# 添加表单大小限制中间件
app.add_middleware(
    FormSizeMiddleware,
    max_part_size=1024 * 1024 * 1024  # 1GB
)

# 添加身份验证中间件
@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    """身份验证中间件"""
    
    # 定义不需要身份验证的路径
    public_paths = [
        "/",
        "/auth/login",
        "/auth/logout", 
        "/auth/register",
        "/auth/token",
        "/static",
        "/fontawesome",
        "/data",
        "/health", 
        "/health/db",
        "/docs",
        "/redoc", 
        "/openapi.json"
    ]
    
    # 检查请求路径是否为公开路径
    request_path = request.url.path
    is_public = any(request_path.startswith(path) for path in public_paths)
    
    logger.info(f"中间件: 路径={request_path}, 是否公开={is_public}")
    
    # 如果是公开路径，直接处理请求
    if is_public:
        logger.info(f"中间件: 公开路径，直接处理")
        response = await call_next(request)
        return response
    
    # 对于需要身份验证的路径，检查token
    try:
        logger.info(f"中间件检查路径: {request_path}")
        
        # 尝试从cookie中获取token
        token = request.cookies.get("access_token")
        logger.info(f"中间件: token存在={bool(token)}")
        
        if not token:
            logger.info(f"中间件: 没有token，重定向到登录页面")
            # 如果是API路径，返回401错误
            if request_path.startswith("/api/") or request_path.startswith("/chat/api/"):
                return JSONResponse(
                    status_code=401,
                    content={"detail": "未登录或登录已过期"}
                )
            # 如果是页面路径，重定向到登录页面
            else:
                return RedirectResponse(url="/auth/login")
        
        # 验证token
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            username = payload.get("sub")
            if not username:
                raise JWTError("Invalid token")
        except JWTError:
            # Token无效
            if request_path.startswith("/api/") or request_path.startswith("/chat/api/"):
                return JSONResponse(
                    status_code=401,
                    content={"detail": "Token无效，请重新登录"}
                )
            else:
                # 重定向到登录页面并清除无效cookie
                response = RedirectResponse(url="/auth/login")
                response.delete_cookie(key="access_token")
                return response
        
        # Token有效，继续处理请求
        response = await call_next(request)
        return response
        
    except Exception as e:
        logger.error(f"身份验证中间件出错: {str(e)}")
        # 出现错误时，重定向到登录页面
        if request_path.startswith("/api/") or request_path.startswith("/chat/api/"):
            return JSONResponse(
                status_code=500,
                content={"detail": "身份验证服务出错"}
            )
        else:
            return RedirectResponse(url="/auth/login")

# 延迟导入路由，避免一次性加载所有依赖
# 注意：延迟导入可以避免启动时的大量依赖加载，提高启动速度
@app.on_event("startup")
async def load_routers():
    """应用启动时动态导入和注册路由"""
    try:
        # 认证路由 - 现在已经修复了依赖问题
        from app.routers import auth
        app.include_router(auth.router)
        logger.info("已加载认证路由")
        
        # 主页路由
        from app.routers import home
        app.include_router(home.router)
        logger.info("已加载主页路由")
        
        # 仪表盘路由 - 已修复依赖问题
        from app.routers import dashboard
        app.include_router(dashboard.router)
        logger.info("已加载仪表盘路由")
        
        # 聊天路由
        from app.routers import chat
        app.include_router(chat.router)
        logger.info("已加载聊天路由")
        
        # 知识库路由 - 负责文件管理功能的UI
        from app.routers import knowledge
        app.include_router(knowledge.router)
        logger.info("已加载知识库路由")
        
        # 智能体路由
        from app.routers import agent
        app.include_router(agent.router)
        logger.info("已加载智能体路由")
        
        # 配置管理路由
        from app.routers import config
        app.include_router(config.router)
        logger.info("已加载配置管理路由")
        
        # RAG聊天路由
        try:
            from app.routers import rag_chat
            app.include_router(rag_chat.router)
            logger.info("已加载RAG聊天路由")
        except Exception as e:
            logger.error(f"无法加载RAG聊天路由: {str(e)}")
            logger.warning("RAG聊天功能将不可用")
        
        # 文档上传路由 - 使用新的支持向量化的版本
        try:
            from app.routers import document_upload_new
            app.include_router(document_upload_new.router)
            logger.info("已加载文档上传路由（支持向量化）")
        except Exception as e:
            logger.error(f"无法加载文档上传路由: {str(e)}")
            logger.warning("文档上传功能将不可用")
        
        # 联网搜索路由
        try:
            from app.routers import network_search
            app.include_router(network_search.router)
            logger.info("已加载联网搜索路由")
        except Exception as e:
            logger.error(f"无法加载联网搜索路由: {str(e)}")
            logger.warning("联网搜索功能将不可用")
    
    except Exception as e:
        logger.error(f"加载路由时出错: {str(e)}")
        logger.warning("部分功能可能不可用")

# 根路由 - 根据用户登录状态进行重定向
@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """根路由，根据登录状态重定向"""
    try:
        from jose import jwt, JWTError
        from app.core.config import settings
        
        # 尝试从cookie中获取token
        token = request.cookies.get("access_token")
        
        # 如果有token，检查token是否有效
        if token:
            try:
                # 解析token
                payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
                username = payload.get("sub")
                
                # 如果token有效且包含用户名，重定向到通用对话页面
                if username:
                    logger.info(f"用户 {username} 已登录，重定向到通用对话页面")
                    return RedirectResponse(url="/chat/home")
            except JWTError:
                # token无效，重定向到登录页面
                logger.info("Token无效，重定向到登录页面")
                pass
        
        # 默认重定向到登录页面
        return RedirectResponse(url="/auth/login")
    except Exception as e:
        # 如果出现任何错误，直接重定向到聊天页面（临时方案）
        logger.warning(f"根路由处理出错: {e}，直接重定向到聊天页面")
        return RedirectResponse(url="/chat/home")

# 基本健康检查端点
@app.get("/health")
async def health_check():
    return {"status": "ok", "timestamp": datetime.datetime.now().isoformat()}

# 数据库健康检查端点
@app.get("/health/db")
async def db_health_check(db_session: Session = Depends(get_db)):
    try:
        # 检查数据库连接
        result = db_session.execute(text("SELECT 1")).scalar()
        if result == 1:
            # 获取数据库版本信息
            db_version = db_session.execute(text("SELECT VERSION()")).scalar()
            # 获取当前数据库名称
            current_db = db_session.execute(text("SELECT DATABASE()")).scalar()
            # 获取当前时间
            current_time = db_session.execute(text("SELECT NOW()")).scalar()
            
            return {
                "status": "ok",
                "database": {
                    "name": current_db,
                    "version": db_version,
                    "server_time": current_time.isoformat() if current_time else None,
                    "connection": f"{db.db_host}:{db.db_port}",
                },
                "timestamp": datetime.datetime.now().isoformat()
            }
    except Exception as e:
        logger.error(f"数据库健康检查失败: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "message": f"数据库连接失败: {str(e)}",
                "timestamp": datetime.datetime.now().isoformat()
            }
        )

# 应用启动事件
@app.on_event("startup")
async def startup_event():
    logger.info("=" * 50)
    logger.info("智能体平台应用启动")
    logger.info(f"数据库连接: {db.db_host}:{db.db_port}/{db.db_name}")
    
    # 创建数据库表
    try:
        # 导入所有模型以确保它们被注册到Base
        from app.models import user, agent, model_config
        
        # 创建所有表
        db.create_all_tables()
        logger.info("数据库表创建/检查完成")
    except Exception as e:
        logger.error(f"创建数据库表失败: {str(e)}")
        logger.warning("数据库表可能不完整，某些功能可能不可用")
    
    # 初始化环境
    try:
        # 注释掉不需要的工具导入
        # 导入文件处理相关工具函数
        # from app.tools.rag_tools.document_loaders.utils import create_nltk_data_dir, suppress_openpyxl_warnings
        
        # 创建NLTK数据目录 - 这是文件处理所需
        # nltk_data_dir = create_nltk_data_dir()
        # logger.info(f"已初始化NLTK数据目录: {nltk_data_dir}")
        
        # 抑制openpyxl警告 - 处理Excel文件所需
        # suppress_openpyxl_warnings()
        # logger.info("已抑制openpyxl警告")
        
        # logger.info("已初始化文件处理功能，但不使用RAG功能")
        
        # 创建NLTK数据目录
        nltk_data_dir = os.path.join(os.getcwd(), "data", "nltk_data")
        os.makedirs(nltk_data_dir, exist_ok=True)
        os.environ["NLTK_DATA"] = nltk_data_dir
        
        # 创建常用的NLTK资源目录结构
        for resource_dir in [
            os.path.join(nltk_data_dir, "tokenizers", "punkt"),
            os.path.join(nltk_data_dir, "taggers", "averaged_perceptron_tagger"),
            os.path.join(nltk_data_dir, "tokenizers", "punkt_tab"),
        ]:
            os.makedirs(resource_dir, exist_ok=True)
        
        # 抑制openpyxl警告
        import warnings
        warnings.filterwarnings("ignore", category=UserWarning, module="openpyxl")
        
        logger.info(f"已初始化NLTK数据目录: {nltk_data_dir}")
        logger.info("已抑制openpyxl警告")
    except Exception as e:
        logger.warning(f"初始化环境时出错: {str(e)}")
        
    logger.info("=" * 50)

# 应用关闭事件
@app.on_event("shutdown")
async def shutdown_event():
    logger.info("智能体平台应用关闭")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)