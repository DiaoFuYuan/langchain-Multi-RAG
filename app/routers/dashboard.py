"""
仪表盘相关路由
"""
from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
import logging

# 导入身份验证依赖项
from ..core.auth_dependency import require_auth_redirect

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 创建路由
router = APIRouter(
    prefix="/dashboard",
    tags=["仪表盘"],
    responses={404: {"description": "Not found"}},
)

# 模板目录
templates = Jinja2Templates(directory="templates")

# 仪表盘首页 - 直接重定向到通用对话页面
@router.get("/", response_class=HTMLResponse)
async def dashboard_page(request: Request, current_user: str = Depends(require_auth_redirect)):
    """重定向到通用对话页面，确保用户登录后默认进入通用对话界面"""
    logger.info("访问 /dashboard/ 路径，重定向到通用对话页面")
    return RedirectResponse(url="/chat/home")

# 主页路由 - 显示智能体平台主页
@router.get("/home", response_class=HTMLResponse)
async def home_page(request: Request, current_user: str = Depends(require_auth_redirect)):
    """返回智能体平台主页，显示智能体商店内容"""
    try:
        logger.info("加载智能体商店页面")
        return templates.TemplateResponse(
            "home/index.html", 
            {"request": request, "current_user": current_user}
        )
    except Exception as e:
        logger.error(f"加载主页时出错: {str(e)}")
        return HTMLResponse(
            content=f"""
            <html>
                <head><title>Error</title></head>
                <body>
                    <h1>出错了</h1>
                    <p>加载主页时发生错误，请稍后再试。</p>
                    <p>错误详情: {str(e)}</p>
                </body>
            </html>
            """,
            status_code=500
        ) 