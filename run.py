#!/usr/bin/env python3
"""
USB继电器RTU控制软件运行脚本

自动处理权限问题，提供简化的使用方式
"""

import os
import sys
import subprocess
import grp
from pathlib import Path

def check_dialout_permission():
    """检查当前用户是否有dialout组权限"""
    try:
        # 检查用户是否在dialout组中
        current_groups = [grp.getgrgid(gid).gr_name for gid in os.getgroups()]
        return 'dialout' in current_groups
    except:
        return False

def run_with_dialout_permission(cmd_args):
    """使用dialout组权限运行命令"""
    if check_dialout_permission():
        # 已有权限，直接运行
        cmd = ["python", "usb_relay.py"] + cmd_args
    else:
        # 需要临时获取权限
        cmd = ["sg", "dialout", "-c", f"python usb_relay.py {' '.join(cmd_args)}"]
    
    try:
        result = subprocess.run(cmd, check=True)
        return result.returncode
    except subprocess.CalledProcessError as e:
        return e.returncode
    except FileNotFoundError:
        print("错误：无法找到必要的命令")
        return 1

def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("USB继电器RTU控制软件")
        print("使用方法: python run.py [命令] [选项]")
        print()
        print("示例:")
        print("  python run.py device list")
        print("  python run.py relay status --port /dev/ttyUSB0")
        print("  python run.py relay on --port /dev/ttyUSB0 --relay 1")
        print("  python run.py input status --port /dev/ttyUSB0")
        print("  python run.py test --port /dev/ttyUSB0")
        print()
        print("获取完整帮助:")
        print("  python run.py --help")
        return 0
    
    # 检查权限状态
    if not check_dialout_permission():
        print("⚠️  注意：当前用户不在dialout组中，将使用临时权限")
        print("   要永久解决此问题，请重新登录或运行: newgrp dialout")
        print()
    
    # 传递所有参数给usb_relay.py
    cmd_args = sys.argv[1:]
    return run_with_dialout_permission(cmd_args)

if __name__ == "__main__":
    sys.exit(main())
