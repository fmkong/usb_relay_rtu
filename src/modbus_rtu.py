"""
Modbus RTU协议实现模块

实现Modbus RTU通信协议，包括：
- CRC16校验计算
- 数据帧封装和解析
- 串口通信管理
"""

import struct
import time
from typing import List, Tuple, Optional, Union
import serial


class ModbusCRC16:
    """Modbus CRC16校验计算类"""
    
    # CRC低字节表
    CRC_LO_TABLE = [
        0x00, 0xC0, 0xC1, 0x01, 0xC3, 0x03, 0x02, 0xC2, 0xC6, 0x06,
        0x07, 0xC7, 0x05, 0xC5, 0xC4, 0x04, 0xCC, 0x0C, 0x0D, 0xCD,
        0x0F, 0xCF, 0xCE, 0x0E, 0x0A, 0xCA, 0xCB, 0x0B, 0xC9, 0x09,
        0x08, 0xC8, 0xD8, 0x18, 0x19, 0xD9, 0x1B, 0xDB, 0xDA, 0x1A,
        0x1E, 0xDE, 0xDF, 0x1F, 0xDD, 0x1D, 0x1C, 0xDC, 0x14, 0xD4,
        0xD5, 0x15, 0xD7, 0x17, 0x16, 0xD6, 0xD2, 0x12, 0x13, 0xD3,
        0x11, 0xD1, 0xD0, 0x10, 0xF0, 0x30, 0x31, 0xF1, 0x33, 0xF3,
        0xF2, 0x32, 0x36, 0xF6, 0xF7, 0x37, 0xF5, 0x35, 0x34, 0xF4,
        0x3C, 0xFC, 0xFD, 0x3D, 0xFF, 0x3F, 0x3E, 0xFE, 0xFA, 0x3A,
        0x3B, 0xFB, 0x39, 0xF9, 0xF8, 0x38, 0x28, 0xE8, 0xE9, 0x29,
        0xEB, 0x2B, 0x2A, 0xEA, 0xEE, 0x2E, 0x2F, 0xEF, 0x2D, 0xED,
        0xEC, 0x2C, 0xE4, 0x24, 0x25, 0xE5, 0x27, 0xE7, 0xE6, 0x26,
        0x22, 0xE2, 0xE3, 0x23, 0xE1, 0x21, 0x20, 0xE0, 0xA0, 0x60,
        0x61, 0xA1, 0x63, 0xA3, 0xA2, 0x62, 0x66, 0xA6, 0xA7, 0x67,
        0xA5, 0x65, 0x64, 0xA4, 0x6C, 0xAC, 0xAD, 0x6D, 0xAF, 0x6F,
        0x6E, 0xAE, 0xAA, 0x6A, 0x6B, 0xAB, 0x69, 0xA9, 0xA8, 0x68,
        0x78, 0xB8, 0xB9, 0x79, 0xBB, 0x7B, 0x7A, 0xBA, 0xBE, 0x7E,
        0x7F, 0xBF, 0x7D, 0xBD, 0xBC, 0x7C, 0xB4, 0x74, 0x75, 0xB5,
        0x77, 0xB7, 0xB6, 0x76, 0x72, 0xB2, 0xB3, 0x73, 0xB1, 0x71,
        0x70, 0xB0, 0x50, 0x90, 0x91, 0x51, 0x93, 0x53, 0x52, 0x92,
        0x96, 0x56, 0x57, 0x97, 0x55, 0x95, 0x94, 0x54, 0x9C, 0x5C,
        0x5D, 0x9D, 0x5F, 0x9F, 0x9E, 0x5E, 0x5A, 0x9A, 0x9B, 0x5B,
        0x99, 0x59, 0x58, 0x98, 0x88, 0x48, 0x49, 0x89, 0x4B, 0x8B,
        0x8A, 0x4A, 0x4E, 0x8E, 0x8F, 0x4F, 0x8D, 0x4D, 0x4C, 0x8C,
        0x44, 0x84, 0x85, 0x45, 0x87, 0x47, 0x46, 0x86, 0x82, 0x42,
        0x43, 0x83, 0x41, 0x81, 0x80, 0x40
    ]
    
    # CRC高字节表
    CRC_HI_TABLE = [
        0x00, 0xC1, 0x81, 0x40, 0x01, 0xC0, 0x80, 0x41, 0x01, 0xC0,
        0x80, 0x41, 0x00, 0xC1, 0x81, 0x40, 0x01, 0xC0, 0x80, 0x41,
        0x00, 0xC1, 0x81, 0x40, 0x00, 0xC1, 0x81, 0x40, 0x01, 0xC0,
        0x80, 0x41, 0x01, 0xC0, 0x80, 0x41, 0x00, 0xC1, 0x81, 0x40,
        0x00, 0xC1, 0x81, 0x40, 0x01, 0xC0, 0x80, 0x41, 0x00, 0xC1,
        0x81, 0x40, 0x01, 0xC0, 0x80, 0x41, 0x01, 0xC0, 0x80, 0x41,
        0x00, 0xC1, 0x81, 0x40, 0x01, 0xC0, 0x80, 0x41, 0x00, 0xC1,
        0x81, 0x40, 0x00, 0xC1, 0x81, 0x40, 0x01, 0xC0, 0x80, 0x41,
        0x00, 0xC1, 0x81, 0x40, 0x01, 0xC0, 0x80, 0x41, 0x01, 0xC0,
        0x80, 0x41, 0x00, 0xC1, 0x81, 0x40, 0x00, 0xC1, 0x81, 0x40,
        0x01, 0xC0, 0x80, 0x41, 0x01, 0xC0, 0x80, 0x41, 0x00, 0xC1,
        0x81, 0x40, 0x01, 0xC0, 0x80, 0x41, 0x00, 0xC1, 0x81, 0x40,
        0x00, 0xC1, 0x81, 0x40, 0x01, 0xC0, 0x80, 0x41, 0x01, 0xC0,
        0x80, 0x41, 0x00, 0xC1, 0x81, 0x40, 0x00, 0xC1, 0x81, 0x40,
        0x01, 0xC0, 0x80, 0x41, 0x00, 0xC1, 0x81, 0x40, 0x01, 0xC0,
        0x80, 0x41, 0x01, 0xC0, 0x80, 0x41, 0x00, 0xC1, 0x81, 0x40,
        0x00, 0xC1, 0x81, 0x40, 0x01, 0xC0, 0x80, 0x41, 0x01, 0xC0,
        0x80, 0x41, 0x00, 0xC1, 0x81, 0x40, 0x01, 0xC0, 0x80, 0x41,
        0x00, 0xC1, 0x81, 0x40, 0x00, 0xC1, 0x81, 0x40, 0x01, 0xC0,
        0x80, 0x41, 0x00, 0xC1, 0x81, 0x40, 0x01, 0xC0, 0x80, 0x41,
        0x01, 0xC0, 0x80, 0x41, 0x00, 0xC1, 0x81, 0x40, 0x01, 0xC0,
        0x80, 0x41, 0x00, 0xC1, 0x81, 0x40, 0x00, 0xC1, 0x81, 0x40,
        0x01, 0xC0, 0x80, 0x41, 0x01, 0xC0, 0x80, 0x41, 0x00, 0xC1,
        0x81, 0x40, 0x00, 0xC1, 0x81, 0x40, 0x01, 0xC0, 0x80, 0x41,
        0x00, 0xC1, 0x81, 0x40, 0x01, 0xC0, 0x80, 0x41, 0x01, 0xC0,
        0x80, 0x41, 0x00, 0xC1, 0x81, 0x40
    ]
    
    @classmethod
    def calculate(cls, data: bytes) -> Tuple[int, int]:
        """
        计算Modbus CRC16校验码
        
        Args:
            data: 需要计算CRC的数据
            
        Returns:
            Tuple[int, int]: (CRC低字节, CRC高字节)
        """
        crc_hi = 0xFF
        crc_lo = 0xFF
        
        for byte in data:
            index = crc_hi ^ byte
            crc_hi = crc_lo ^ cls.CRC_HI_TABLE[index]
            crc_lo = cls.CRC_LO_TABLE[index]
        
        return crc_hi, crc_lo
    
    @classmethod
    def verify(cls, data: bytes) -> bool:
        """
        验证CRC校验码
        
        Args:
            data: 包含CRC的完整数据帧
            
        Returns:
            bool: 校验是否正确
        """
        if len(data) < 2:
            return False
        
        # 分离数据和CRC
        message = data[:-2]
        received_crc_lo = data[-2]
        received_crc_hi = data[-1]
        
        # 计算CRC
        calculated_crc_lo, calculated_crc_hi = cls.calculate(message)
        
        return (received_crc_lo == calculated_crc_lo and 
                received_crc_hi == calculated_crc_hi)


class ModbusRTUException(Exception):
    """Modbus RTU异常基类"""
    pass


class ModbusRTUTimeoutException(ModbusRTUException):
    """Modbus RTU超时异常"""
    pass


class ModbusRTUCRCException(ModbusRTUException):
    """Modbus RTU CRC校验异常"""
    pass


class ModbusRTUResponse:
    """Modbus RTU响应数据类"""
    
    def __init__(self, slave_id: int, function_code: int, data: bytes, raw_data: bytes):
        self.slave_id = slave_id
        self.function_code = function_code
        self.data = data
        self.raw_data = raw_data
        self.is_error = (function_code & 0x80) != 0
        
    def __repr__(self):
        return f"ModbusRTUResponse(slave_id={self.slave_id}, function_code=0x{self.function_code:02X}, data_len={len(self.data)})"


class ModbusRTUClient:
    """Modbus RTU客户端类"""
    
    # 功能码常量
    FUNCTION_READ_COILS = 0x01
    FUNCTION_READ_DISCRETE_INPUTS = 0x02
    FUNCTION_READ_HOLDING_REGISTERS = 0x03
    FUNCTION_READ_INPUT_REGISTERS = 0x04
    FUNCTION_WRITE_SINGLE_COIL = 0x05
    FUNCTION_WRITE_SINGLE_REGISTER = 0x06
    FUNCTION_WRITE_MULTIPLE_COILS = 0x0F
    FUNCTION_WRITE_MULTIPLE_REGISTERS = 0x10
    
    def __init__(self, port: str, baudrate: int = 9600, timeout: float = 1.0):
        """
        初始化Modbus RTU客户端
        
        Args:
            port: 串口设备路径
            baudrate: 波特率
            timeout: 通信超时时间（秒）
        """
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.serial_port: Optional[serial.Serial] = None
        
    def connect(self) -> None:
        """连接串口设备"""
        try:
            self.serial_port = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=self.timeout
            )
            # 清空缓冲区
            self.serial_port.flushInput()
            self.serial_port.flushOutput()
        except serial.SerialException as e:
            raise ModbusRTUException(f"无法连接串口设备 {self.port}: {e}")
    
    def disconnect(self) -> None:
        """断开串口连接"""
        if self.serial_port and self.serial_port.is_open:
            self.serial_port.close()
            self.serial_port = None
    
    def is_connected(self) -> bool:
        """检查是否已连接"""
        return self.serial_port is not None and self.serial_port.is_open
    
    def _send_frame(self, frame: bytes) -> None:
        """发送数据帧"""
        if not self.is_connected():
            raise ModbusRTUException("串口未连接")
        
        self.serial_port.write(frame)
        self.serial_port.flush()
    
    def _receive_frame(self, expected_length: int = None) -> bytes:
        """接收数据帧"""
        if not self.is_connected():
            raise ModbusRTUException("串口未连接")
        
        # 等待数据
        start_time = time.time()
        while self.serial_port.in_waiting == 0:
            if time.time() - start_time > self.timeout:
                raise ModbusRTUTimeoutException("接收数据超时")
            time.sleep(0.001)
        
        # 读取数据
        data = bytearray()
        last_receive_time = time.time()
        
        while True:
            if self.serial_port.in_waiting > 0:
                chunk = self.serial_port.read(self.serial_port.in_waiting)
                data.extend(chunk)
                last_receive_time = time.time()
            else:
                # 如果一段时间没有接收到新数据，认为帧结束
                if time.time() - last_receive_time > 0.01:  # 10ms空闲时间
                    break
                # 检查超时
                if time.time() - start_time > self.timeout:
                    raise ModbusRTUTimeoutException("接收数据超时")
                time.sleep(0.001)
        
        return bytes(data)
    
    def _build_frame(self, slave_id: int, function_code: int, data: bytes) -> bytes:
        """构建Modbus RTU数据帧"""
        frame = struct.pack('BB', slave_id, function_code) + data
        crc_lo, crc_hi = ModbusCRC16.calculate(frame)
        frame += struct.pack('BB', crc_lo, crc_hi)
        return frame
    
    def _parse_response(self, response_data: bytes) -> ModbusRTUResponse:
        """解析响应数据"""
        if len(response_data) < 4:  # 最小帧长度：设备地址+功能码+数据+CRC
            raise ModbusRTUException("响应数据长度不足")
        
        # 验证CRC
        if not ModbusCRC16.verify(response_data):
            raise ModbusRTUCRCException("CRC校验失败")
        
        # 解析数据
        slave_id = response_data[0]
        function_code = response_data[1]
        data = response_data[2:-2]  # 去除CRC
        
        return ModbusRTUResponse(slave_id, function_code, data, response_data)
    
    def execute_request(self, slave_id: int, function_code: int, data: bytes) -> ModbusRTUResponse:
        """
        执行Modbus请求
        
        Args:
            slave_id: 从设备地址
            function_code: 功能码
            data: 请求数据
            
        Returns:
            ModbusRTUResponse: 响应对象
        """
        # 构建请求帧
        request_frame = self._build_frame(slave_id, function_code, data)
        
        # 发送请求
        self._send_frame(request_frame)
        
        # 接收响应
        response_data = self._receive_frame()
        
        # 解析响应
        response = self._parse_response(response_data)
        
        # 检查从设备地址是否匹配
        if response.slave_id != slave_id:
            raise ModbusRTUException(f"从设备地址不匹配: 期望{slave_id}, 收到{response.slave_id}")
        
        # 检查是否为错误响应
        if response.is_error:
            error_code = response.data[0] if response.data else 0
            raise ModbusRTUException(f"设备返回错误: 功能码=0x{function_code:02X}, 错误码=0x{error_code:02X}")
        
        return response
    
    def read_coils(self, slave_id: int, start_address: int, count: int) -> List[bool]:
        """
        读取线圈状态（功能码01H）
        
        Args:
            slave_id: 从设备地址
            start_address: 起始地址
            count: 读取数量
            
        Returns:
            List[bool]: 线圈状态列表
        """
        data = struct.pack('>HH', start_address, count)
        response = self.execute_request(slave_id, self.FUNCTION_READ_COILS, data)
        
        byte_count = response.data[0]
        coil_data = response.data[1:1+byte_count]
        
        coils = []
        for i in range(count):
            byte_index = i // 8
            bit_index = i % 8
            if byte_index < len(coil_data):
                coils.append((coil_data[byte_index] >> bit_index) & 1 == 1)
            else:
                coils.append(False)
        
        return coils
    
    def read_discrete_inputs(self, slave_id: int, start_address: int, count: int) -> List[bool]:
        """
        读取离散输入状态（功能码02H）
        
        Args:
            slave_id: 从设备地址
            start_address: 起始地址
            count: 读取数量
            
        Returns:
            List[bool]: 输入状态列表
        """
        data = struct.pack('>HH', start_address, count)
        response = self.execute_request(slave_id, self.FUNCTION_READ_DISCRETE_INPUTS, data)
        
        byte_count = response.data[0]
        input_data = response.data[1:1+byte_count]
        
        inputs = []
        for i in range(count):
            byte_index = i // 8
            bit_index = i % 8
            if byte_index < len(input_data):
                inputs.append((input_data[byte_index] >> bit_index) & 1 == 1)
            else:
                inputs.append(False)
        
        return inputs
    
    def read_holding_registers(self, slave_id: int, start_address: int, count: int) -> List[int]:
        """
        读取保持寄存器（功能码03H）
        
        Args:
            slave_id: 从设备地址
            start_address: 起始地址
            count: 读取数量
            
        Returns:
            List[int]: 寄存器值列表
        """
        data = struct.pack('>HH', start_address, count)
        response = self.execute_request(slave_id, self.FUNCTION_READ_HOLDING_REGISTERS, data)
        
        byte_count = response.data[0]
        register_data = response.data[1:1+byte_count]
        
        registers = []
        for i in range(0, len(register_data), 2):
            if i + 1 < len(register_data):
                value = struct.unpack('>H', register_data[i:i+2])[0]
                registers.append(value)
        
        return registers
    
    def read_input_registers(self, slave_id: int, start_address: int, count: int) -> List[int]:
        """
        读取输入寄存器（功能码04H）
        
        Args:
            slave_id: 从设备地址
            start_address: 起始地址
            count: 读取数量
            
        Returns:
            List[int]: 寄存器值列表
        """
        data = struct.pack('>HH', start_address, count)
        response = self.execute_request(slave_id, self.FUNCTION_READ_INPUT_REGISTERS, data)
        
        byte_count = response.data[0]
        register_data = response.data[1:1+byte_count]
        
        registers = []
        for i in range(0, len(register_data), 2):
            if i + 1 < len(register_data):
                value = struct.unpack('>H', register_data[i:i+2])[0]
                registers.append(value)
        
        return registers
    
    def write_single_coil(self, slave_id: int, address: int, value: bool) -> bool:
        """
        写单个线圈（功能码05H）
        
        Args:
            slave_id: 从设备地址
            address: 线圈地址
            value: 线圈值（True=ON, False=OFF）
            
        Returns:
            bool: 操作是否成功
        """
        coil_value = 0xFF00 if value else 0x0000
        data = struct.pack('>HH', address, coil_value)
        response = self.execute_request(slave_id, self.FUNCTION_WRITE_SINGLE_COIL, data)
        
        # 验证响应
        resp_address, resp_value = struct.unpack('>HH', response.data)
        return resp_address == address and resp_value == coil_value
    
    def write_single_register(self, slave_id: int, address: int, value: int) -> bool:
        """
        写单个寄存器（功能码06H）
        
        Args:
            slave_id: 从设备地址
            address: 寄存器地址
            value: 寄存器值
            
        Returns:
            bool: 操作是否成功
        """
        data = struct.pack('>HH', address, value)
        response = self.execute_request(slave_id, self.FUNCTION_WRITE_SINGLE_REGISTER, data)
        
        # 验证响应
        resp_address, resp_value = struct.unpack('>HH', response.data)
        return resp_address == address and resp_value == value
    
    def write_multiple_coils(self, slave_id: int, start_address: int, values: List[bool]) -> bool:
        """
        写多个线圈（功能码0FH）
        
        Args:
            slave_id: 从设备地址
            start_address: 起始地址
            values: 线圈值列表
            
        Returns:
            bool: 操作是否成功
        """
        count = len(values)
        byte_count = (count + 7) // 8  # 计算所需字节数
        
        # 构建线圈数据
        coil_bytes = bytearray(byte_count)
        for i, value in enumerate(values):
            if value:
                byte_index = i // 8
                bit_index = i % 8
                coil_bytes[byte_index] |= (1 << bit_index)
        
        data = struct.pack('>HHB', start_address, count, byte_count) + bytes(coil_bytes)
        response = self.execute_request(slave_id, self.FUNCTION_WRITE_MULTIPLE_COILS, data)
        
        # 验证响应
        resp_address, resp_count = struct.unpack('>HH', response.data)
        return resp_address == start_address and resp_count == count
    
    def write_multiple_registers(self, slave_id: int, start_address: int, values: List[int]) -> bool:
        """
        写多个寄存器（功能码10H）
        
        Args:
            slave_id: 从设备地址
            start_address: 起始地址
            values: 寄存器值列表
            
        Returns:
            bool: 操作是否成功
        """
        count = len(values)
        byte_count = count * 2
        
        # 构建寄存器数据
        register_data = bytearray()
        for value in values:
            register_data.extend(struct.pack('>H', value))
        
        data = struct.pack('>HHB', start_address, count, byte_count) + bytes(register_data)
        response = self.execute_request(slave_id, self.FUNCTION_WRITE_MULTIPLE_REGISTERS, data)
        
        # 验证响应
        resp_address, resp_count = struct.unpack('>HH', response.data)
        return resp_address == start_address and resp_count == count
    
    def __enter__(self):
        """上下文管理器入口"""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.disconnect()
