"""
数据库核心模块
负责数据库连接、会话创建和所有数据库操作的基础功能
"""
from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import logging
from contextlib import contextmanager
from typing import Generator, Any
import yaml
import os

# from app.core.config import settings  # 注释掉这个导入以避免ModuleNotFoundError

# 设置日志
logger = logging.getLogger(__name__)

# 加载YAML配置
def load_config():
    """从config.yaml加载配置"""
    try:
        # 获取当前文件所在目录的父目录，即项目根目录
        current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        config_path = os.path.join(current_dir, "config.yaml")
        with open(config_path, 'r', encoding='utf-8') as file:
            return yaml.safe_load(file)
    except Exception as e:
        logger.error(f"加载配置文件失败: {e}")
        return None

class Database:
    """数据库管理类"""
    
    def __init__(self, yaml_config=None):
        """
        初始化数据库连接
        
        Args:
            yaml_config: YAML配置文件中的数据库配置部分
        """
        # 加载配置
        config = load_config()
        if config and 'database' in config:
            db_config = config['database']
            # 使用SQLite配置
            if db_config.get('type') == 'sqlite':
                db_path = db_config.get('path', 'data/agents.db')
                # 确保数据目录存在
                os.makedirs(os.path.dirname(db_path), exist_ok=True)
                self.database_url = f"sqlite:///{db_path}"
                self.db_host = "localhost"
                self.db_port = "N/A"
                self.db_name = db_path
                self.db_user = "N/A"
                self.db_password = "N/A"
            else:
                # 如果不是SQLite，使用默认的SQLite配置
                self.database_url = "sqlite:///data/agents.db"
                self.db_host = "localhost"
                self.db_port = "N/A"
                self.db_name = "data/agents.db"
                self.db_user = "N/A"
                self.db_password = "N/A"
        else:
            # 默认使用SQLite
            self.database_url = "sqlite:///data/agents.db"
            self.db_host = "localhost"
            self.db_port = "N/A"
            self.db_name = "data/agents.db"
            self.db_user = "N/A"
            self.db_password = "N/A"
        
        # 打印数据库连接信息
        logger.info("=" * 50)
        logger.info(f"数据库配置信息: {self.db_host}:{self.db_port}/{self.db_name}")
        logger.info(f"数据库用户: {self.db_user}")
        logger.info(f"数据库URL: {self.database_url}")
        logger.info("=" * 50)
        
        # 初始化数据库引擎和会话
        self._initialize_database()
    
    def _initialize_database(self):
        """初始化数据库引擎和会话"""
        try:
            # 创建数据库引擎 - SQLite特定配置
            if self.database_url.startswith("sqlite"):
                self.engine = create_engine(
                    self.database_url,
                    pool_pre_ping=True,  # 检查连接是否有效
                    echo=False,          # 是否打印SQL语句
                    connect_args={
                        "check_same_thread": False  # SQLite特定配置
                    }
                )
            else:
                self.engine = create_engine(
                    self.database_url,
                    pool_pre_ping=True,  # 检查连接是否有效
                    pool_recycle=3600,   # 连接池回收时间
                    echo=False,          # 是否打印SQL语句
                    connect_args={
                        "connect_timeout": 5  # 连接超时时间
                    }
                )
            
            # 测试连接
            self._test_connection()
            
            # 创建会话类
            self.SessionLocal = sessionmaker(
                autocommit=False, 
                autoflush=False, 
                bind=self.engine
            )
            
            # 创建数据模型基类
            self.Base = declarative_base()
            
            logger.info("数据库引擎和会话初始化成功")
        except Exception as e:
            logger.error("*" * 50)
            logger.error(f"数据库初始化失败: {e}")
            logger.error("*" * 50)
            # 创建内存数据库作为备用
            self.engine = create_engine("sqlite:///:memory:", echo=True)
            self.SessionLocal = sessionmaker(
                autocommit=False, 
                autoflush=False, 
                bind=self.engine
            )
            self.Base = declarative_base()
            logger.warning("使用内存数据库作为备用")
    
    def _test_connection(self):
        """测试数据库连接"""
        try:
            with self.engine.connect() as connection:
                if self.database_url.startswith("sqlite"):
                    # SQLite特定的测试查询
                    result = connection.execute(text("SELECT 1")).scalar()
                    logger.info("*" * 50)
                    logger.info(f"SQLite数据库连接成功: {self.db_name}")
                    logger.info(f"数据库文件: {self.database_url}")
                    logger.info("*" * 50)
                else:
                    # MySQL特定的测试查询
                    result = connection.execute(text("SELECT DATABASE()")).fetchone()
                    connected_db = result[0] if result else "未知"
                    
                    # 显示醒目的连接成功信息
                    logger.info("*" * 50)
                    logger.info(f"数据库连接成功: {connected_db}")
                    logger.info(f"连接地址: {self.db_host}:{self.db_port}")
                    logger.info(f"当前时间: {connection.execute(text('SELECT NOW()')).scalar()}")
                    logger.info(f"数据库版本: {connection.execute(text('SELECT VERSION()')).scalar()}")
                    logger.info("*" * 50)
                    
                    # 验证连接的数据库是否是预期的数据库
                    if connected_db != self.db_name:
                        logger.warning("!" * 50)
                        logger.warning(f"警告: 连接到的数据库({connected_db})与配置的数据库({self.db_name})不一致!")
                        logger.warning("!" * 50)
        except Exception as e:
            logger.error(f"数据库连接测试失败: {e}")
    
    def get_db(self) -> Generator:
        """
        获取数据库会话的依赖函数
        用于FastAPI的Depends依赖注入
        """
        db = self.SessionLocal()
        try:
            yield db
        finally:
            db.close()
    
    @contextmanager
    def get_db_context(self):
        """
        获取数据库会话的上下文管理器
        用于with语句块
        """
        db = self.SessionLocal()
        try:
            yield db
        finally:
            db.close()
    
    def create_all_tables(self):
        """创建所有表"""
        try:
            self.Base.metadata.create_all(bind=self.engine)
            logger.info("所有表创建成功")
        except Exception as e:
            logger.error(f"创建表失败: {e}")
    
    def drop_all_tables(self):
        """删除所有表"""
        try:
            self.Base.metadata.drop_all(bind=self.engine)
            logger.info("所有表删除成功")
        except Exception as e:
            logger.error(f"删除表失败: {e}")

# 创建全局数据库实例
db = Database()

# 导出主要组件，方便其他模块导入
Base = db.Base
get_db = db.get_db 