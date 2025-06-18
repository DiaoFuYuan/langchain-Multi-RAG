"""
模型配置服务
处理模型配置的数据库操作
"""
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_
from app.models.model_config import ModelConfig
from app.database import get_db
import logging

logger = logging.getLogger(__name__)


class ModelConfigService:
    """模型配置服务类"""
    
    @staticmethod
    def create_model_config(
        db: Session,
        provider: str,
        provider_name: str,
        model_name: str,
        api_key: str,
        endpoint: Optional[str] = None,
        organization: Optional[str] = None,
        model_type: Optional[str] = None,
        context_length: Optional[int] = None,
        max_tokens: Optional[int] = None,
        test_status: str = "pending",
        test_message: Optional[str] = None
    ) -> ModelConfig:
        """创建模型配置"""
        try:
            # 检查是否已存在相同的配置
            existing_config = db.query(ModelConfig).filter(
                and_(
                    ModelConfig.provider == provider,
                    ModelConfig.model_name == model_name,
                    ModelConfig.endpoint == endpoint,
                    ModelConfig.is_active == True
                )
            ).first()
            
            if existing_config:
                # 更新现有配置
                existing_config.provider_name = provider_name
                existing_config.api_key = api_key
                existing_config.organization = organization
                existing_config.model_type = model_type
                existing_config.context_length = context_length
                existing_config.max_tokens = max_tokens
                existing_config.test_status = test_status
                existing_config.test_message = test_message
                db.commit()
                db.refresh(existing_config)
                logger.info(f"更新模型配置: {provider} - {model_name}")
                return existing_config
            else:
                # 创建新配置
                model_config = ModelConfig(
                    provider=provider,
                    provider_name=provider_name,
                    model_name=model_name,
                    api_key=api_key,
                    endpoint=endpoint,
                    organization=organization,
                    model_type=model_type,
                    context_length=context_length,
                    max_tokens=max_tokens,
                    test_status=test_status,
                    test_message=test_message
                )
                db.add(model_config)
                db.commit()
                db.refresh(model_config)
                logger.info(f"创建模型配置: {provider} - {model_name}")
                return model_config
        except Exception as e:
            db.rollback()
            logger.error(f"创建/更新模型配置失败: {e}")
            raise
    
    @staticmethod
    def get_all_model_configs(db: Session, include_inactive: bool = False) -> List[ModelConfig]:
        """获取所有模型配置"""
        try:
            query = db.query(ModelConfig)
            if not include_inactive:
                query = query.filter(ModelConfig.is_active == True)
            return query.order_by(ModelConfig.created_at.desc()).all()
        except Exception as e:
            logger.error(f"获取模型配置列表失败: {e}")
            return []
    
    @staticmethod
    def get_model_config_by_id(db: Session, config_id: int) -> Optional[ModelConfig]:
        """根据ID获取模型配置"""
        try:
            return db.query(ModelConfig).filter(
                and_(
                    ModelConfig.id == config_id,
                    ModelConfig.is_active == True
                )
            ).first()
        except Exception as e:
            logger.error(f"获取模型配置失败: {e}")
            return None
    
    @staticmethod
    def get_model_configs_by_provider(db: Session, provider: str) -> List[ModelConfig]:
        """根据供应商获取模型配置"""
        try:
            return db.query(ModelConfig).filter(
                and_(
                    ModelConfig.provider == provider,
                    ModelConfig.is_active == True
                )
            ).order_by(ModelConfig.created_at.desc()).all()
        except Exception as e:
            logger.error(f"获取供应商模型配置失败: {e}")
            return []
    
    @staticmethod
    def update_model_config(
        db: Session,
        config_id: int,
        **kwargs
    ) -> Optional[ModelConfig]:
        """更新模型配置"""
        try:
            model_config = db.query(ModelConfig).filter(
                and_(
                    ModelConfig.id == config_id,
                    ModelConfig.is_active == True
                )
            ).first()
            
            if not model_config:
                return None
            
            # 更新字段
            for key, value in kwargs.items():
                if hasattr(model_config, key) and value is not None:
                    setattr(model_config, key, value)
            
            db.commit()
            db.refresh(model_config)
            logger.info(f"更新模型配置: {config_id}")
            return model_config
        except Exception as e:
            db.rollback()
            logger.error(f"更新模型配置失败: {e}")
            return None
    
    @staticmethod
    def delete_model_config(db: Session, config_id: int) -> bool:
        """删除模型配置（软删除）"""
        try:
            model_config = db.query(ModelConfig).filter(
                and_(
                    ModelConfig.id == config_id,
                    ModelConfig.is_active == True
                )
            ).first()
            
            if not model_config:
                return False
            
            model_config.is_active = False
            db.commit()
            logger.info(f"删除模型配置: {config_id}")
            return True
        except Exception as e:
            db.rollback()
            logger.error(f"删除模型配置失败: {e}")
            return False
    
    @staticmethod
    def update_test_status(
        db: Session,
        config_id: int,
        test_status: str,
        test_message: Optional[str] = None
    ) -> Optional[ModelConfig]:
        """更新测试状态"""
        try:
            model_config = db.query(ModelConfig).filter(
                and_(
                    ModelConfig.id == config_id,
                    ModelConfig.is_active == True
                )
            ).first()
            
            if not model_config:
                return None
            
            model_config.test_status = test_status
            if test_message is not None:
                model_config.test_message = test_message
            
            db.commit()
            db.refresh(model_config)
            logger.info(f"更新测试状态: {config_id} - {test_status}")
            return model_config
        except Exception as e:
            db.rollback()
            logger.error(f"更新测试状态失败: {e}")
            return None
    
    @staticmethod
    def permanent_delete_model_config(db: Session, config_id: int) -> bool:
        """永久删除模型配置（物理删除）"""
        try:
            model_config = db.query(ModelConfig).filter(
                ModelConfig.id == config_id
            ).first()
            
            if not model_config:
                return False
            
            db.delete(model_config)
            db.commit()
            logger.info(f"永久删除模型配置: {config_id}")
            return True
        except Exception as e:
            db.rollback()
            logger.error(f"永久删除模型配置失败: {e}")
            return False 