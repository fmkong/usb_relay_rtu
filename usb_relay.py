#!/usr/bin/env python3
"""
USB继电器RTU控制软件启动脚本

可以直接运行此脚本来使用软件，无需安装
"""

import sys
import os
from pathlib import Path

# 添加src目录到Python路径
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

try:
    from cli import cli
    
    if __name__ == "__main__":
        cli()
        
except ImportError as e:
    print(f"错误：无法导入必要的模块: {e}")
    print("请确保已安装所有依赖包:")
    print("pip install -r requirements.txt")
    sys.exit(1)
except Exception as e:
    print(f"启动错误: {e}")
    sys.exit(1)
