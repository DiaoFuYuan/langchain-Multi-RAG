"""
智能体平台启动脚本
运行此脚本将启动FastAPI应用程序

使用方法:
    python run.py
"""

import uvicorn
import os
import sys
import time

# 修复Windows平台兼容性问题
if os.name == 'nt':  # Windows
    import platform
    # 确保平台检测正常工作
    try:
        platform.machine()
    except Exception:
        # 如果平台检测失败，设置默认值
        platform.machine = lambda: "AMD64"

if __name__ == "__main__":
    # 清屏，让终端看起来更整洁
    os.system('cls' if os.name == 'nt' else 'clear')
    
    # 应用信息
    print("\n" + "=" * 60)
    print(f"{'智能体平台 - 应用启动器':^58}")
    print("=" * 60)
    print(" * 应用版本: v0.1.0")
    print(" * 主机地址: 127.0.0.1")
    print(" * 端口号  : 8000")
    print(" * 热重载  : 已启用")
    print("-" * 60)
    print(" 启动完成后，应用将运行在: http://127.0.0.1:8000")
    print(" 按 CTRL+C 可随时停止服务")
    print("=" * 60)
    print("\n正在初始化服务，请稍候...\n")
    
    # 短暂延迟，让用户阅读信息
    time.sleep(1)
    
    # 打印分隔符，使Uvicorn的信息更加突出
    print("\n" + "·" * 60)
    print(" 以下为Uvicorn服务器输出:")
    print("·" * 60 + "\n")
    
    try:
        # 启动Uvicorn服务器
        uvicorn.run(
            "app.main:app",
            host="127.0.0.1",
            port=8000,
            reload=True,
            reload_excludes=[
                "test_*.py",
                "*/test/*",
                "*/__pycache__/*",
                "*.pyc",
                "data/*",
                ".git/*",
                ".idea/*",
                ".cursor/*",
                "*.log",
                "*.tmp"
            ],
            # 添加错误处理配置
            log_level="info",
            access_log=True,
            use_colors=True
        )
    except KeyboardInterrupt:
        print("\n\n" + "=" * 60)
        print("服务已停止")
        print("=" * 60)
    except Exception as e:
        print(f"\n\n❌ 启动失败: {e}")
        print("请检查：")
        print("1. 端口8000是否被占用")
        print("2. 依赖包是否正确安装")
        print("3. 数据库配置是否正确")
        sys.exit(1) 