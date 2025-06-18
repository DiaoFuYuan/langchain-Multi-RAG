"""
智能体平台应用初始化模块
"""

import os
import sys
import logging
import warnings
from pathlib import Path

# 修复Windows平台兼容性问题
if os.name == 'nt':  # Windows
    import platform
    # 确保平台检测正常工作
    try:
        platform.machine()
    except Exception:
        # 如果平台检测失败，设置默认值
        platform.machine = lambda: "AMD64"

# 抑制警告
warnings.filterwarnings("ignore", category=UserWarning, module="pkg_resources")
warnings.filterwarnings("ignore", category=DeprecationWarning)

# 配置NLTK数据目录
nltk_data_dir = Path(__file__).parent.parent / "data" / "nltk_data"
nltk_data_dir.mkdir(parents=True, exist_ok=True)
os.environ['NLTK_DATA'] = str(nltk_data_dir)

# 抑制openpyxl警告
import openpyxl
openpyxl.reader.excel.warnings.simplefilter(action='ignore')

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)
logger.info("已初始化NLTK数据目录: %s", nltk_data_dir)
logger.info("已抑制openpyxl警告")

# 应用信息
logger.info("=" * 70)
logger.info("智能体平台应用启动")
logger.info("基于FastAPI的模块化网站")
logger.info("=" * 70)

# 延迟导入数据库模块，避免循环导入
try:
    from app.database import db, Base, get_db
    logger.info("数据库模块导入成功")
except Exception as e:
    logger.error(f"数据库模块导入失败: {e}")
    # 不抛出异常，让应用继续启动
    db = None
    Base = None
    get_db = None

logger.info("应用初始化完成")
logger.info("=" * 70) 