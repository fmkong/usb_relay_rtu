"""
Modbus RTU模块测试
"""

import pytest
from src.modbus_rtu import ModbusCRC16, ModbusRTUClient, ModbusRTUException


class TestModbusCRC16:
    """测试Modbus CRC16校验算法"""
    
    def test_crc16_calculation(self):
        """测试CRC16计算"""
        # 测试数据来自协议手册中的示例
        test_data = bytes([0x01, 0x01, 0x00, 0x13, 0x00, 0x25])
        crc_lo, crc_hi = ModbusCRC16.calculate(test_data)
        
        # 根据协议手册，这个数据的CRC应该是0x140C
        expected_crc_lo = 0x0C
        expected_crc_hi = 0x14
        
        assert crc_lo == expected_crc_lo, f"CRC低字节错误: 期望{expected_crc_lo:02X}, 实际{crc_lo:02X}"
        assert crc_hi == expected_crc_hi, f"CRC高字节错误: 期望{expected_crc_hi:02X}, 实际{crc_hi:02X}"
    
    def test_crc16_verification(self):
        """测试CRC16验证"""
        # 包含CRC的完整数据帧
        complete_frame = bytes([0x01, 0x01, 0x00, 0x13, 0x00, 0x25, 0x0C, 0x14])
        
        assert ModbusCRC16.verify(complete_frame), "CRC验证应该通过"
        
        # 错误的CRC
        wrong_frame = bytes([0x01, 0x01, 0x00, 0x13, 0x00, 0x25, 0x00, 0x00])
        assert not ModbusCRC16.verify(wrong_frame), "错误的CRC验证应该失败"
    
    def test_empty_data(self):
        """测试空数据"""
        crc_lo, crc_hi = ModbusCRC16.calculate(b"")
        # 空数据的CRC应该是初始值
        assert crc_lo == 0xFF
        assert crc_hi == 0xFF
    
    def test_single_byte(self):
        """测试单字节数据"""
        test_data = bytes([0x01])
        crc_lo, crc_hi = ModbusCRC16.calculate(test_data)
        
        # 验证计算结果不为空且有变化
        assert crc_lo != 0xFF or crc_hi != 0xFF


class TestModbusRTUClient:
    """测试Modbus RTU客户端类"""
    
    def test_client_initialization(self):
        """测试客户端初始化"""
        client = ModbusRTUClient("/dev/ttyUSB0", 9600, 1.0)
        
        assert client.port == "/dev/ttyUSB0"
        assert client.baudrate == 9600
        assert client.timeout == 1.0
        assert not client.is_connected()
    
    def test_frame_building(self):
        """测试数据帧构建"""
        client = ModbusRTUClient("/dev/ttyUSB0")
        
        # 构建读线圈命令帧
        frame = client._build_frame(0x01, 0x01, bytes([0x00, 0x13, 0x00, 0x25]))
        
        # 验证帧结构：从设备地址 + 功能码 + 数据 + CRC
        assert len(frame) == 8
        assert frame[0] == 0x01  # 从设备地址
        assert frame[1] == 0x01  # 功能码
        assert frame[2:6] == bytes([0x00, 0x13, 0x00, 0x25])  # 数据
        
        # 验证CRC（最后两个字节）
        expected_crc = bytes([0x0C, 0x14])
        assert frame[6:8] == expected_crc


if __name__ == "__main__":
    pytest.main([__file__])
