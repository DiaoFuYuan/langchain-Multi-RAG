"""
智能体API模式定义
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum

class AgentCategoryEnum(str, Enum):
    """智能体分类枚举"""
    CUSTOMER_SERVICE = "customer_service"
    ANALYSIS = "analysis"
    WRITING = "writing"
    CODING = "coding"
    TRANSLATION = "translation"
    OTHER = "other"

class AgentStatusEnum(str, Enum):
    """智能体状态枚举"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"

class AgentTemplateEnum(str, Enum):
    """智能体模板枚举"""
    SIMPLE = "simple"
    MULTI_AGENT = "multi-agent"
    CHAT_GUIDE = "chat-guide"
    KNOWLEDGE_TIME = "knowledge-time"

class AgentCreate(BaseModel):
    """创建智能体内部模型"""
    name: str = Field(..., min_length=1, max_length=100, description="智能体名称")
    description: Optional[str] = Field(None, description="智能体描述")
    problem_description: Optional[str] = Field(None, description="问题描述")
    answer_description: Optional[str] = Field(None, description="回答描述")
    category: Optional[AgentCategoryEnum] = Field(AgentCategoryEnum.OTHER, description="智能体分类")
    template: Optional[AgentTemplateEnum] = Field(AgentTemplateEnum.SIMPLE, description="模板类型")
    system_prompt: Optional[str] = Field(None, description="系统提示词")
    is_public: Optional[bool] = Field(False, description="是否公开")

class AgentCreateRequest(BaseModel):
    """创建智能体请求模型"""
    name: str = Field(..., min_length=1, max_length=100, description="智能体名称")
    description: Optional[str] = Field(None, description="智能体描述")
    problem_description: Optional[str] = Field(None, description="问题描述")
    answer_description: Optional[str] = Field(None, description="回答描述")
    category: Optional[AgentCategoryEnum] = Field(AgentCategoryEnum.OTHER, description="智能体分类")
    template: Optional[AgentTemplateEnum] = Field(AgentTemplateEnum.SIMPLE, description="模板类型")
    system_prompt: Optional[str] = Field(None, description="系统提示词")
    is_public: Optional[bool] = Field(False, description="是否公开")
    
    class Config:
        schema_extra = {
            "example": {
                "name": "客服助手",
                "description": "智能客服机器人，能够回答常见问题并提供帮助",
                "problem_description": "用户需要快速获得客服支持和问题解答",
                "answer_description": "以友好、专业的方式回答用户问题，提供准确的解决方案",
                "category": "customer_service",
                "template": "simple",
                "system_prompt": "你是一个专业的客服助手...",
                "is_public": False
            }
        }

class AgentUpdate(BaseModel):
    """更新智能体内部模型"""
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="智能体名称")
    description: Optional[str] = Field(None, description="智能体描述")
    problem_description: Optional[str] = Field(None, description="问题描述")
    answer_description: Optional[str] = Field(None, description="回答描述")
    category: Optional[AgentCategoryEnum] = Field(None, description="智能体分类")
    template: Optional[AgentTemplateEnum] = Field(None, description="模板类型")
    system_prompt: Optional[str] = Field(None, description="系统提示词")
    is_public: Optional[bool] = Field(None, description="是否公开")
    status: Optional[AgentStatusEnum] = Field(None, description="智能体状态")

class AgentUpdateRequest(BaseModel):
    """更新智能体请求模型"""
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="智能体名称")
    description: Optional[str] = Field(None, description="智能体描述")
    problem_description: Optional[str] = Field(None, description="问题描述")
    answer_description: Optional[str] = Field(None, description="回答描述")
    category: Optional[AgentCategoryEnum] = Field(None, description="智能体分类")
    template: Optional[AgentTemplateEnum] = Field(None, description="模板类型")
    system_prompt: Optional[str] = Field(None, description="系统提示词")
    is_public: Optional[bool] = Field(None, description="是否公开")
    status: Optional[AgentStatusEnum] = Field(None, description="智能体状态")

class AgentResponse(BaseModel):
    """智能体响应模型"""
    id: int = Field(..., description="智能体ID")
    name: str = Field(..., description="智能体名称")
    description: Optional[str] = Field(None, description="智能体描述")
    problem_description: Optional[str] = Field(None, description="问题描述")
    answer_description: Optional[str] = Field(None, description="回答描述")
    category: Optional[str] = Field(None, description="智能体分类")
    status: Optional[str] = Field(None, description="智能体状态")
    template: Optional[str] = Field(None, description="模板类型")
    system_prompt: Optional[str] = Field(None, description="系统提示词")
    is_public: bool = Field(..., description="是否公开")
    creator_id: Optional[int] = Field(None, description="创建者ID")
    creator_name: Optional[str] = Field(None, description="创建者名称")
    created_at: Optional[datetime] = Field(None, description="创建时间")
    updated_at: Optional[datetime] = Field(None, description="更新时间")
    usage_count: int = Field(0, description="使用次数")
    
    # 显示名称字段
    category_display: Optional[str] = Field(None, description="分类显示名称")
    status_display: Optional[str] = Field(None, description="状态显示名称")
    template_display: Optional[str] = Field(None, description="模板显示名称")
    
    class Config:
        from_attributes = True

class AgentListResponse(BaseModel):
    """智能体列表响应模型"""
    agents: List[AgentResponse] = Field(..., description="智能体列表")
    total: int = Field(..., description="总数量")
    page: int = Field(..., description="当前页码")
    page_size: int = Field(..., description="每页数量")
    pages: int = Field(..., description="总页数")

class AgentQueryParams(BaseModel):
    """智能体查询参数"""
    page: int = Field(1, ge=1, description="页码")
    page_size: int = Field(10, ge=1, le=100, description="每页数量")
    search: Optional[str] = Field(None, description="搜索关键词")
    category: Optional[AgentCategoryEnum] = Field(None, description="分类筛选")
    status: Optional[AgentStatusEnum] = Field(None, description="状态筛选")
    is_public: Optional[bool] = Field(None, description="是否公开筛选")
    creator_id: Optional[int] = Field(None, description="创建者筛选")

class AgentDeleteResponse(BaseModel):
    """删除智能体响应模型"""
    success: bool = Field(..., description="是否成功")
    message: str = Field(..., description="响应消息")
    deleted_id: int = Field(..., description="被删除的智能体ID")

class AgentCopyResponse(BaseModel):
    """复制智能体响应模型"""
    success: bool = Field(..., description="是否成功")
    message: str = Field(..., description="响应消息")
    original_id: int = Field(..., description="原智能体ID")
    new_agent: AgentResponse = Field(..., description="新创建的智能体") 