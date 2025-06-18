"""
智能体数据模型
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, Enum
from sqlalchemy.sql import func
from app.database import Base
import enum

class AgentCategory(enum.Enum):
    """智能体分类枚举"""
    CUSTOMER_SERVICE = "customer_service"  # 客服
    ANALYSIS = "analysis"                  # 分析
    WRITING = "writing"                    # 写作
    CODING = "coding"                      # 编程
    TRANSLATION = "translation"           # 翻译
    OTHER = "other"                        # 其他

class AgentStatus(enum.Enum):
    """智能体状态枚举"""
    ACTIVE = "active"      # 活跃
    INACTIVE = "inactive"  # 未激活
    ERROR = "error"        # 错误

class AgentTemplate(enum.Enum):
    """智能体模板类型枚举"""
    SIMPLE = "simple"                      # 简易机器人
    MULTI_AGENT = "multi-agent"           # 多智能体自主协同
    CHAT_GUIDE = "chat-guide"             # 对话引导 + 变量
    KNOWLEDGE_TIME = "knowledge-time"     # 知道时间的机器人

class Agent(Base):
    """智能体数据模型"""
    __tablename__ = "agents"
    
    # 主键
    id = Column(Integer, primary_key=True, index=True, comment="智能体ID")
    
    # 基本信息
    name = Column(String(100), nullable=False, comment="智能体名称")
    description = Column(Text, comment="智能体描述")
    
    # 问题和回答描述
    problem_description = Column(Text, comment="问题描述")
    answer_description = Column(Text, comment="回答描述")
    
    # 分类和状态
    category = Column(Enum(AgentCategory), default=AgentCategory.OTHER, comment="智能体分类")
    status = Column(Enum(AgentStatus), default=AgentStatus.ACTIVE, comment="智能体状态")
    template = Column(Enum(AgentTemplate), default=AgentTemplate.SIMPLE, comment="模板类型")
    
    # 系统提示词
    system_prompt = Column(Text, comment="系统提示词")
    
    # 权限设置
    is_public = Column(Boolean, default=False, comment="是否公开")
    
    # 创建者信息
    creator_id = Column(Integer, comment="创建者ID")
    creator_name = Column(String(50), comment="创建者名称")
    
    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="更新时间")
    
    # 使用统计
    usage_count = Column(Integer, default=0, comment="使用次数")
    
    def __repr__(self):
        return f"<Agent(id={self.id}, name='{self.name}', category='{self.category}')>"
    
    def to_dict(self):
        """转换为字典格式，便于JSON序列化"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "problem_description": self.problem_description,
            "answer_description": self.answer_description,
            "category": self.category.value if self.category else None,
            "status": self.status.value if self.status else None,
            "template": self.template.value if self.template else None,
            "system_prompt": self.system_prompt,
            "is_public": self.is_public,
            "creator_id": self.creator_id,
            "creator_name": self.creator_name,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "usage_count": self.usage_count
        }
    
    @classmethod
    def get_category_display_name(cls, category):
        """获取分类显示名称"""
        category_names = {
            AgentCategory.CUSTOMER_SERVICE: "客服",
            AgentCategory.ANALYSIS: "分析", 
            AgentCategory.WRITING: "写作",
            AgentCategory.CODING: "编程",
            AgentCategory.TRANSLATION: "翻译",
            AgentCategory.OTHER: "其他"
        }
        return category_names.get(category, "未知")
    
    @classmethod
    def get_status_display_name(cls, status):
        """获取状态显示名称"""
        status_names = {
            AgentStatus.ACTIVE: "活跃",
            AgentStatus.INACTIVE: "未激活",
            AgentStatus.ERROR: "错误"
        }
        return status_names.get(status, "未知")
    
    @classmethod
    def get_template_display_name(cls, template):
        """获取模板显示名称"""
        template_names = {
            AgentTemplate.SIMPLE: "简易机器人",
            AgentTemplate.MULTI_AGENT: "多智能体自主协同",
            AgentTemplate.CHAT_GUIDE: "对话引导 + 变量",
            AgentTemplate.KNOWLEDGE_TIME: "知道时间的机器人"
        }
        return template_names.get(template, "未知") 