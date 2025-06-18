"""
应用配置模块
"""
import os
import yaml
from typing import Optional
import logging

logger = logging.getLogger(__name__)

class Settings:
    """应用配置类"""
    
    def __init__(self):
        # 从config.yaml加载配置
        config = self.load_config()
        
        # 安全配置
        if config and 'security' in config:
            security_config = config['security']
            self.SECRET_KEY = security_config.get('secret_key', '09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7')
            self.ALGORITHM = security_config.get('algorithm', 'HS256')
            self.ACCESS_TOKEN_EXPIRE_MINUTES = security_config.get('access_token_expire_minutes', 30)
        else:
            # 默认配置
            self.SECRET_KEY = '09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7'
            self.ALGORITHM = 'HS256'
            self.ACCESS_TOKEN_EXPIRE_MINUTES = 30
        
        # 项目信息
        self.PROJECT_NAME = "智能体平台"
        self.VERSION = "1.0.0"
        self.DESCRIPTION = "基于FastAPI的智能体平台"
        
        # API配置
        self.API_V1_STR = "/api/v1"
        
        # 数据库配置（如果需要的话）
        self.DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/agents.db")
        
        # 其他配置
        self.DEBUG = os.getenv("DEBUG", "False").lower() == "true"
    
    def load_config(self) -> Optional[dict]:
        """从config.yaml加载配置"""
        try:
            # 获取项目根目录
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            config_path = os.path.join(project_root, "config.yaml")
            
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as file:
                    return yaml.safe_load(file)
            else:
                logger.warning(f"配置文件不存在: {config_path}")
                return None
        except Exception as e:
            logger.error(f"加载配置文件失败: {e}")
            return None

# 创建全局配置实例
settings = Settings() 