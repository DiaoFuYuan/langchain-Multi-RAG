from fastapi import APIRouter, Request, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import Optional
import logging
import math
import json

# 导入数据库
from app.database import get_db

# 导入模型和服务
from app.services.agent_service import AgentService
from app.schemas.agent import (
    AgentCreateRequest, 
    AgentUpdateRequest, 
    AgentResponse,
    AgentListResponse,
    AgentQueryParams,
    AgentDeleteResponse,
    AgentCopyResponse,
    AgentCreate
)
from app.models.agent import Agent

# 设置日志
logger = logging.getLogger(__name__)

# 创建路由器
router = APIRouter(prefix="/agent", tags=["agent"])

# 设置模板目录
templates = Jinja2Templates(directory="templates")

# ============= 页面路由 =============

@router.get("/quick", response_class=HTMLResponse)
async def agent_quick_page(request: Request):
    """快捷智能体管理页面"""
    return templates.TemplateResponse("agent/agent_quick.html", {"request": request})

@router.get("/workflow", response_class=HTMLResponse)
async def agent_workflow_page(request: Request):
    """工作流智能体页面"""
    return templates.TemplateResponse("agent/agent_workflow.html", {"request": request})

@router.get("/config/{agent_id}", response_class=HTMLResponse)
async def agent_config_page(request: Request, agent_id: int, db: Session = Depends(get_db)):
    """智能体配置页面"""
    try:
        agent_service = AgentService(db)
        agent = agent_service.get_agent(agent_id)
        return templates.TemplateResponse("agent/agent_config.html", {
            "request": request, 
            "agent": agent
        })
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

# ============= API 端点 =============

@router.get("/api/agents", response_model=AgentListResponse)
async def get_agents(
    page: int = 1,
    page_size: int = 10,
    search: Optional[str] = None,
    is_public: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    """获取智能体列表"""
    agent_service = AgentService(db)
    
    # 构建过滤条件
    filters = {}
    if search:
        filters['search'] = search
    if is_public is not None:
        filters['is_public'] = is_public
    
    result = agent_service.get_agents(
        page=page, 
        page_size=page_size, 
        **filters
    )
    
    return result

@router.post("/api/agents", response_model=AgentResponse)
async def create_agent(
    agent_data: AgentCreate,
    db: Session = Depends(get_db)
):
    """创建新智能体"""
    agent_service = AgentService(db)
    
    try:
        agent = agent_service.create_agent(agent_data)
        return agent
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="创建智能体失败")

@router.get("/api/agents/{agent_id}", response_model=AgentResponse)
async def get_agent(
    agent_id: int,
    db: Session = Depends(get_db)
):
    """获取单个智能体详情"""
    agent_service = AgentService(db)
    
    try:
        agent = agent_service.get_agent(agent_id)
        return agent
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.put("/api/agents/{agent_id}", response_model=AgentResponse)
async def update_agent(
    agent_id: int,
    update_data: AgentUpdateRequest,
    db: Session = Depends(get_db)
):
    """更新智能体"""
    try:
        agent_service = AgentService(db)
        db_agent = agent_service.update_agent(agent_id, update_data)
        
        if not db_agent:
            raise HTTPException(status_code=404, detail="智能体不存在")
        
        response_data = db_agent.to_dict()
        response_data.update({
            "category_display": Agent.get_category_display_name(db_agent.category),
            "status_display": Agent.get_status_display_name(db_agent.status),
            "template_display": Agent.get_template_display_name(db_agent.template)
        })
        
        logger.info(f"成功更新智能体: {db_agent.name}")
        return AgentResponse(**response_data)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新智能体失败: {e}")
        raise HTTPException(status_code=500, detail=f"更新智能体失败: {str(e)}")

@router.delete("/api/agents/{agent_id}")
async def delete_agent(
    agent_id: int,
    db: Session = Depends(get_db)
):
    """删除智能体"""
    agent_service = AgentService(db)
    
    try:
        deleted_agent = agent_service.delete_agent(agent_id)
        return {"message": f"智能体 '{deleted_agent.name}' 已删除", "success": True, "deleted_id": agent_id}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="删除智能体失败")

@router.post("/api/agents/{agent_id}/copy")
async def copy_agent(
    agent_id: int,
    db: Session = Depends(get_db)
):
    """复制智能体"""
    agent_service = AgentService(db)
    
    try:
        copied_agent = agent_service.copy_agent(agent_id)
        return {"message": f"智能体 '{copied_agent.name}' 复制成功", "success": True, "original_id": agent_id, "new_agent": copied_agent}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="复制智能体失败")

@router.post("/api/agents/{agent_id}/use")
async def use_agent(agent_id: int, db: Session = Depends(get_db)):
    """使用智能体（增加使用次数）"""
    try:
        agent_service = AgentService(db)
        success = agent_service.increment_usage_count(agent_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="智能体不存在")
        
        return {"success": True, "message": "使用次数已更新"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新使用次数失败: {e}")
        raise HTTPException(status_code=500, detail=f"更新使用次数失败: {str(e)}")

@router.get("/api/agents/statistics/category")
async def get_category_statistics(db: Session = Depends(get_db)):
    """获取分类统计信息"""
    try:
        agent_service = AgentService(db)
        stats = agent_service.get_category_statistics()
        
        return {"success": True, "data": stats}
        
    except Exception as e:
        logger.error(f"获取分类统计失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取分类统计失败: {str(e)}") 