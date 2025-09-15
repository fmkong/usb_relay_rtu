#!/usr/bin/env python3
"""
核心功能测试脚本

直接测试Modbus RTU核心功能，不依赖外部测试框架
"""

import sys
from pathlib import Path

# 添加src目录到路径
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from modbus_rtu import ModbusCRC16, ModbusRTUClient
from device_controller import DeviceManager

def test_crc16():
    """测试CRC16计算"""
    print("🔍 测试CRC16校验算法...")
    
    # 测试数据来自协议手册中的示例
    test_data = bytes([0x01, 0x01, 0x00, 0x13, 0x00, 0x25])
    crc_lo, crc_hi = ModbusCRC16.calculate(test_data)
    
    # 根据协议手册，这个数据的CRC应该是0x140C
    expected_crc_lo = 0x0C
    expected_crc_hi = 0x14
    
    if crc_lo == expected_crc_lo and crc_hi == expected_crc_hi:
        print(f"  ✅ CRC16计算正确: {crc_hi:02X}{crc_lo:02X}")
    else:
        print(f"  ❌ CRC16计算错误: 期望{expected_crc_hi:02X}{expected_crc_lo:02X}, 实际{crc_hi:02X}{crc_lo:02X}")
        return False
    
    # 测试CRC验证
    complete_frame = bytes([0x01, 0x01, 0x00, 0x13, 0x00, 0x25, 0x0C, 0x14])
    if ModbusCRC16.verify(complete_frame):
        print("  ✅ CRC16验证正确")
    else:
        print("  ❌ CRC16验证失败")
        return False
    
    return True

def test_frame_building():
    """测试数据帧构建"""
    print("🔍 测试Modbus RTU数据帧构建...")
    
    client = ModbusRTUClient("/dev/null")  # 使用虚拟端口
    
    # 构建读线圈命令帧
    frame = client._build_frame(0x01, 0x01, bytes([0x00, 0x13, 0x00, 0x25]))
    
    expected_frame = bytes([0x01, 0x01, 0x00, 0x13, 0x00, 0x25, 0x0C, 0x14])
    
    if frame == expected_frame:
        print(f"  ✅ 数据帧构建正确: {' '.join(f'{b:02X}' for b in frame)}")
    else:
        print(f"  ❌ 数据帧构建错误")
        print(f"    期望: {' '.join(f'{b:02X}' for b in expected_frame)}")
        print(f"    实际: {' '.join(f'{b:02X}' for b in frame)}")
        return False
    
    return True

def test_device_detection():
    """测试设备检测功能"""
    print("🔍 测试设备检测功能...")
    
    # 测试串口设备列表
    devices = DeviceManager.list_serial_ports()
    print(f"  ✅ 检测到 {len(devices)} 个串口设备")
    
    # 测试USB设备筛选
    usb_devices = DeviceManager.find_usb_serial_devices()
    print(f"  ✅ 检测到 {len(usb_devices)} 个USB串口设备")
    
    if usb_devices:
        for device in usb_devices:
            print(f"    - {device.port}: {device.description}")
    
    return True

def test_helper_functions():
    """测试辅助函数"""
    print("🔍 测试辅助函数...")
    
    from utils import bytes_to_hex_string, hex_string_to_bytes, parse_relay_list
    
    # 测试十六进制转换
    test_bytes = bytes([0x01, 0x02, 0x03, 0xFF])
    hex_str = bytes_to_hex_string(test_bytes)
    if hex_str == "01 02 03 FF":
        print("  ✅ 字节转十六进制字符串正确")
    else:
        print(f"  ❌ 字节转十六进制字符串错误: {hex_str}")
        return False
    
    # 测试继电器列表解析
    relay_list = parse_relay_list("1,3-5,7")
    expected = [1, 3, 4, 5, 7]
    if relay_list == expected:
        print("  ✅ 继电器列表解析正确")
    else:
        print(f"  ❌ 继电器列表解析错误: {relay_list}")
        return False
    
    return True

def main():
    """主测试函数"""
    print("🚀 开始核心功能测试...\n")
    
    tests = [
        ("CRC16算法", test_crc16),
        ("数据帧构建", test_frame_building),
        ("设备检测", test_device_detection),
        ("辅助函数", test_helper_functions),
    ]
    
    passed = 0
    total = len(tests)
    
    for name, test_func in tests:
        try:
            if test_func():
                passed += 1
                print(f"✅ {name} 测试通过\n")
            else:
                print(f"❌ {name} 测试失败\n")
        except Exception as e:
            print(f"❌ {name} 测试异常: {e}\n")
    
    print(f"📊 测试结果: {passed}/{total} 通过")
    
    if passed == total:
        print("🎉 所有核心功能测试通过！")
        return True
    else:
        print("⚠️  部分测试失败，请检查实现。")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
