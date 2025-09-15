#!/usr/bin/env python3
"""
测试守护进程同步优化的脚本

这个脚本用于验证守护进程的通信同步机制是否能解决"接收数据超时"问题。
"""

import sys
import time
import threading
from pathlib import Path

# 添加src目录到Python路径
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from device_controller import USBRelayController
from daemon import USBRelayDaemon, DaemonClient


def test_direct_mode(port="/dev/ttyUSB0", slave_id=1):
    """测试直接模式 - 应该会有冲突"""
    print("=" * 50)
    print("测试直接模式（预期会有串口冲突）")
    print("=" * 50)
    
    def worker1():
        """工作线程1：持续读取状态"""
        try:
            with USBRelayController(port, slave_id) as controller:
                for i in range(10):
                    states = controller.get_all_relay_states(4)
                    print(f"工作线程1 - 读取到 {len(states)} 个继电器状态")
                    time.sleep(0.3)
        except Exception as e:
            print(f"工作线程1 错误: {e}")
    
    def worker2():
        """工作线程2：控制继电器"""
        try:
            with USBRelayController(port, slave_id) as controller:
                for i in range(5):
                    controller.set_relay_state(1, True)
                    time.sleep(0.2)
                    controller.set_relay_state(1, False)
                    time.sleep(0.2)
                    print(f"工作线程2 - 完成第 {i+1} 次切换")
        except Exception as e:
            print(f"工作线程2 错误: {e}")
    
    # 同时启动两个线程，模拟串口冲突
    t1 = threading.Thread(target=worker1)
    t2 = threading.Thread(target=worker2)
    
    t1.start()
    time.sleep(0.1)  # 稍微错开启动时间
    t2.start()
    
    t1.join()
    t2.join()
    
    print("直接模式测试完成\n")


def test_daemon_mode(port="/dev/ttyUSB0", slave_id=1):
    """测试守护进程模式 - 应该解决冲突"""
    print("=" * 50)
    print("测试守护进程模式（预期无冲突）")
    print("=" * 50)
    
    # 启动守护进程
    daemon = USBRelayDaemon(port, slave_id, 4)
    daemon_thread = threading.Thread(target=daemon.start, daemon=True)
    daemon_thread.start()
    
    # 等待守护进程启动
    time.sleep(2)
    
    # 创建客户端
    client = DaemonClient(port)
    
    def worker1():
        """工作线程1：持续读取状态"""
        try:
            for i in range(10):
                status = client.get_status()
                if status.get("success"):
                    relay_states = status.get("relay_states", [])
                    print(f"工作线程1 - 读取到 {len(relay_states)} 个继电器状态")
                else:
                    print(f"工作线程1 - 状态读取失败: {status.get('error', '未知错误')}")
                time.sleep(0.3)
        except Exception as e:
            print(f"工作线程1 错误: {e}")
    
    def worker2():
        """工作线程2：控制继电器"""
        try:
            for i in range(5):
                success1 = client.set_relay(1, True)
                time.sleep(0.2)
                success2 = client.set_relay(1, False)
                time.sleep(0.2)
                if success1 and success2:
                    print(f"工作线程2 - 完成第 {i+1} 次切换")
                else:
                    print(f"工作线程2 - 第 {i+1} 次切换失败")
        except Exception as e:
            print(f"工作线程2 错误: {e}")
    
    # 同时启动两个线程，测试同步机制
    t1 = threading.Thread(target=worker1)
    t2 = threading.Thread(target=worker2)
    
    t1.start()
    time.sleep(0.1)  # 稍微错开启动时间
    t2.start()
    
    t1.join()
    t2.join()
    
    # 停止守护进程
    daemon.stop()
    print("守护进程模式测试完成\n")


def main():
    """主测试函数"""
    print("USB继电器RTU守护进程同步优化测试")
    print("=" * 60)
    
    # 检查参数
    if len(sys.argv) < 2:
        print("用法: python test_daemon_fix.py <设备端口> [从设备地址]")
        print("示例: python test_daemon_fix.py /dev/ttyUSB0 1")
        sys.exit(1)
    
    port = sys.argv[1]
    slave_id = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    
    print(f"测试设备: {port}")
    print(f"从设备地址: {slave_id}")
    print()
    
    try:
        # 测试1：直接模式（预期有冲突）
        print("第一阶段：直接模式测试")
        test_direct_mode(port, slave_id)
        
        time.sleep(2)  # 间隔2秒
        
        # 测试2：守护进程模式（预期无冲突）
        print("第二阶段：守护进程模式测试")
        test_daemon_mode(port, slave_id)
        
        print("=" * 60)
        print("✓ 所有测试完成")
        print("如果守护进程模式没有出现'接收数据超时'错误，说明同步优化成功！")
        
    except KeyboardInterrupt:
        print("\n测试被用户中断")
    except Exception as e:
        print(f"测试过程中发生错误: {e}")


if __name__ == "__main__":
    main()
