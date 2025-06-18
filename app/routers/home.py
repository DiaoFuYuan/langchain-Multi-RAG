from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
import os
from pathlib import Path

# 导入身份验证依赖项
from ..core.auth_dependency import require_auth_redirect

# 创建路由
router = APIRouter(
    prefix="/home",
    tags=["home"],
    responses={404: {"description": "Not found"}},
)

# 获取模板目录的绝对路径
BASE_DIR = Path(__file__).resolve().parent.parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

@router.get("/knowledge_base", response_class=HTMLResponse)
async def get_knowledge_base(request: Request, current_user: str = Depends(require_auth_redirect)):
    """
    获取知识库管理页面
    """
    return templates.TemplateResponse(
        "home/knowledge_base.html", 
        {"request": request, "current_user": current_user}
    )

# 通知组件演示页面
@router.get("/notification", response_class=HTMLResponse)
async def get_notification_demo(request: Request, current_user: str = Depends(require_auth_redirect)):
    """
    获取通知组件演示页面
    """
    return templates.TemplateResponse(
        "home/notification.html", 
        {"request": request, "current_user": current_user}
    )

# 图表页面
@router.get("/charts", response_class=HTMLResponse) 
async def get_charts_page(request: Request, current_user: str = Depends(require_auth_redirect)):
    """
    获取图表页面
    """
    return templates.TemplateResponse(
        "home/charts.html", 
        {"request": request, "current_user": current_user}
    )

# 此处可以添加更多与知识库相关的API路由
# 例如：创建知识库、获取知识库列表、更新知识库等功能

@router.get("/api/knowledge_bases", response_class=JSONResponse)
async def get_knowledge_bases():
    """
    获取知识库列表的API
    """
    # 这里只是一个示例，实际应用中应该从数据库中获取数据
    knowledge_bases = []
    
    return JSONResponse(content={
        "data": knowledge_bases,
        "total": len(knowledge_bases),
        "success": True
    })

@router.post("/api/knowledge_bases", response_class=JSONResponse)
async def create_knowledge_base():
    """
    创建新知识库的API
    """
    # 示例实现，实际应用中应该将数据保存到数据库
    return JSONResponse(content={
        "success": True,
        "message": "知识库创建成功"
    }) 