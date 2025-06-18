"""
模型配置数据库模型
用于存储AI模型的配置信息
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean
from sqlalchemy.sql import func
from app.database import Base


class ModelConfig(Base):
    """模型配置表"""
    __tablename__ = "model_configs"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    provider = Column(String(50), nullable=False, comment="供应商名称")
    provider_name = Column(String(100), nullable=False, comment="供应商显示名称")
    model_name = Column(String(200), nullable=False, comment="模型名称")
    model_type = Column(String(50), nullable=True, comment="模型类型: llm, embedding, rerank, speech2text, tts")
    api_key = Column(Text, nullable=False, comment="API密钥")
    endpoint = Column(String(500), nullable=True, comment="API端点")
    organization = Column(String(200), nullable=True, comment="组织ID")
    context_length = Column(Integer, nullable=True, comment="上下文长度")
    max_tokens = Column(Integer, nullable=True, comment="最大token数")
    test_status = Column(String(20), default="pending", comment="测试状态: success, failed, pending")
    test_message = Column(Text, nullable=True, comment="测试结果消息")
    is_active = Column(Boolean, default=True, comment="是否激活")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="更新时间")
    
    def __repr__(self):
        return f"<ModelConfig(id={self.id}, provider={self.provider}, model_name={self.model_name}, model_type={self.model_type})>"
    
    def to_dict(self):
        """转换为字典格式"""
        return {
            "id": self.id,
            "provider": self.provider,
            "provider_name": self.provider_name,
            "model_name": self.model_name,
            "model_type": self.model_type,
            "api_key": self.api_key,
            "endpoint": self.endpoint,
            "organization": self.organization,
            "context_length": self.context_length,
            "max_tokens": self.max_tokens,
            "test_status": self.test_status,
            "test_message": self.test_message,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
    
    def to_safe_dict(self):
        """转换为安全的字典格式（隐藏敏感信息）"""
        return {
            "id": self.id,
            "provider": self.provider,
            "provider_name": self.provider_name,
            "model_name": self.model_name,
            "model_type": self.model_type,
            "api_key": self.mask_api_key(),
            "endpoint": self.endpoint,
            "organization": self.organization,
            "context_length": self.context_length,
            "max_tokens": self.max_tokens,
            "test_status": self.test_status,
            "test_message": self.test_message,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
    
    def mask_api_key(self):
        """掩码API Key"""
        if not self.api_key or len(self.api_key) < 8:
            return "***"
        return self.api_key[:4] + "***" + self.api_key[-4:] 