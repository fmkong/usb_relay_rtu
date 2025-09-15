"""
设备控制模块

提供USB继电器设备的高级控制接口，包括：
- 继电器状态控制
- 数字量输入读取
- 设备状态管理
"""

import platform
import glob
import serial.tools.list_ports
from typing import List, Dict, Optional, Union, Tuple
from dataclasses import dataclass
try:
    from .modbus_rtu import ModbusRTUClient, ModbusRTUException
except ImportError:
    from modbus_rtu import ModbusRTUClient, ModbusRTUException


@dataclass
class RelayState:
    """继电器状态数据类"""
    relay_id: int
    state: bool
    address: int
    
    def __str__(self):
        state_text = "ON" if self.state else "OFF"
        return f"继电器 {self.relay_id}: {state_text}"


@dataclass
class InputState:
    """数字量输入状态数据类"""
    input_id: int
    state: bool
    address: int
    
    def __str__(self):
        state_text = "HIGH" if self.state else "LOW"
        return f"输入 {self.input_id}: {state_text}"


@dataclass
class DeviceInfo:
    """设备信息数据类"""
    port: str
    description: str
    manufacturer: str
    vendor_id: str
    product_id: str
    serial_number: str
    
    def __str__(self):
        return f"{self.port} - {self.description}"


class USBRelayController:
    """USB继电器控制器类"""
    
    def __init__(self, port: str, slave_id: int = 1, baudrate: int = 9600, timeout: float = 1.0):
        """
        初始化USB继电器控制器
        
        Args:
            port: 串口设备路径
            slave_id: 从设备地址
            baudrate: 波特率
            timeout: 通信超时时间
        """
        self.port = port
        self.slave_id = slave_id
        self.baudrate = baudrate
        self.timeout = timeout
        self.client = ModbusRTUClient(port, baudrate, timeout)
        self._connected = False
        
        # 默认地址映射配置
        self.relay_start_address = 0x0000  # 继电器起始地址
        self.input_start_address = 0x0000  # 数字量输入起始地址
        
    def connect(self) -> None:
        """连接设备"""
        try:
            self.client.connect()
            self._connected = True
        except ModbusRTUException as e:
            self._connected = False
            raise e
    
    def disconnect(self) -> None:
        """断开连接"""
        self.client.disconnect()
        self._connected = False
    
    def is_connected(self) -> bool:
        """检查连接状态"""
        return self._connected and self.client.is_connected()
    
    def test_connection(self) -> bool:
        """测试设备连接"""
        try:
            # 尝试读取第一个继电器状态来测试连接
            self.get_relay_state(1)
            return True
        except ModbusRTUException:
            return False
    
    def get_relay_state(self, relay_id: int) -> RelayState:
        """
        获取单个继电器状态
        
        Args:
            relay_id: 继电器编号（从1开始）
            
        Returns:
            RelayState: 继电器状态对象
        """
        if not self.is_connected():
            raise ModbusRTUException("设备未连接")
        
        address = self.relay_start_address + relay_id - 1
        states = self.client.read_coils(self.slave_id, address, 1)
        
        return RelayState(
            relay_id=relay_id,
            state=states[0],
            address=address
        )
    
    def get_relay_states(self, start_relay: int, count: int) -> List[RelayState]:
        """
        获取多个继电器状态
        
        Args:
            start_relay: 起始继电器编号（从1开始）
            count: 继电器数量
            
        Returns:
            List[RelayState]: 继电器状态列表
        """
        if not self.is_connected():
            raise ModbusRTUException("设备未连接")
        
        address = self.relay_start_address + start_relay - 1
        states = self.client.read_coils(self.slave_id, address, count)
        
        return [
            RelayState(
                relay_id=start_relay + i,
                state=states[i],
                address=address + i
            )
            for i in range(count)
        ]
    
    def get_all_relay_states(self, max_relays: int = 8) -> List[RelayState]:
        """
        获取所有继电器状态
        
        Args:
            max_relays: 最大继电器数量
            
        Returns:
            List[RelayState]: 所有继电器状态列表
        """
        return self.get_relay_states(1, max_relays)
    
    def set_relay_state(self, relay_id: int, state: bool) -> bool:
        """
        设置单个继电器状态
        
        Args:
            relay_id: 继电器编号（从1开始）
            state: 继电器状态（True=开启, False=关闭）
            
        Returns:
            bool: 操作是否成功
        """
        if not self.is_connected():
            raise ModbusRTUException("设备未连接")
        
        address = self.relay_start_address + relay_id - 1
        return self.client.write_single_coil(self.slave_id, address, state)
    
    def set_relay_states(self, start_relay: int, states: List[bool]) -> bool:
        """
        设置多个继电器状态
        
        Args:
            start_relay: 起始继电器编号（从1开始）
            states: 继电器状态列表
            
        Returns:
            bool: 操作是否成功
        """
        if not self.is_connected():
            raise ModbusRTUException("设备未连接")
        
        address = self.relay_start_address + start_relay - 1
        return self.client.write_multiple_coils(self.slave_id, address, states)
    
    def turn_on_relay(self, relay_id: int) -> bool:
        """
        打开继电器
        
        Args:
            relay_id: 继电器编号（从1开始）
            
        Returns:
            bool: 操作是否成功
        """
        return self.set_relay_state(relay_id, True)
    
    def turn_off_relay(self, relay_id: int) -> bool:
        """
        关闭继电器
        
        Args:
            relay_id: 继电器编号（从1开始）
            
        Returns:
            bool: 操作是否成功
        """
        return self.set_relay_state(relay_id, False)
    
    def toggle_relay(self, relay_id: int) -> bool:
        """
        切换继电器状态
        
        Args:
            relay_id: 继电器编号（从1开始）
            
        Returns:
            bool: 操作是否成功
        """
        current_state = self.get_relay_state(relay_id)
        return self.set_relay_state(relay_id, not current_state.state)
    
    def turn_on_all_relays(self, max_relays: int = 8) -> bool:
        """
        打开所有继电器
        
        Args:
            max_relays: 最大继电器数量
            
        Returns:
            bool: 操作是否成功
        """
        states = [True] * max_relays
        return self.set_relay_states(1, states)
    
    def turn_off_all_relays(self, max_relays: int = 8) -> bool:
        """
        关闭所有继电器
        
        Args:
            max_relays: 最大继电器数量
            
        Returns:
            bool: 操作是否成功
        """
        states = [False] * max_relays
        return self.set_relay_states(1, states)
    
    def get_input_state(self, input_id: int) -> InputState:
        """
        获取单个数字量输入状态
        
        Args:
            input_id: 输入编号（从1开始）
            
        Returns:
            InputState: 输入状态对象
        """
        if not self.is_connected():
            raise ModbusRTUException("设备未连接")
        
        address = self.input_start_address + input_id - 1
        states = self.client.read_discrete_inputs(self.slave_id, address, 1)
        
        return InputState(
            input_id=input_id,
            state=states[0],
            address=address
        )
    
    def get_input_states(self, start_input: int, count: int) -> List[InputState]:
        """
        获取多个数字量输入状态
        
        Args:
            start_input: 起始输入编号（从1开始）
            count: 输入数量
            
        Returns:
            List[InputState]: 输入状态列表
        """
        if not self.is_connected():
            raise ModbusRTUException("设备未连接")
        
        address = self.input_start_address + start_input - 1
        states = self.client.read_discrete_inputs(self.slave_id, address, count)
        
        return [
            InputState(
                input_id=start_input + i,
                state=states[i],
                address=address + i
            )
            for i in range(count)
        ]
    
    def get_all_input_states(self, max_inputs: int = 8) -> List[InputState]:
        """
        获取所有数字量输入状态
        
        Args:
            max_inputs: 最大输入数量
            
        Returns:
            List[InputState]: 所有输入状态列表
        """
        return self.get_input_states(1, max_inputs)
    
    def __enter__(self):
        """上下文管理器入口"""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.disconnect()


class DeviceManager:
    """设备管理器类"""
    
    @staticmethod
    def list_serial_ports() -> List[DeviceInfo]:
        """
        列出所有串口设备
        
        Returns:
            List[DeviceInfo]: 设备信息列表
        """
        ports = []
        
        # 使用pyserial获取串口列表
        for port_info in serial.tools.list_ports.comports():
            device_info = DeviceInfo(
                port=port_info.device,
                description=port_info.description or "Unknown Device",
                manufacturer=port_info.manufacturer or "Unknown",
                vendor_id=hex(port_info.vid) if port_info.vid else "Unknown",
                product_id=hex(port_info.pid) if port_info.pid else "Unknown",
                serial_number=port_info.serial_number or "Unknown"
            )
            ports.append(device_info)
        
        return ports
    
    @staticmethod
    def find_usb_serial_devices() -> List[DeviceInfo]:
        """
        查找USB转串口设备
        
        Returns:
            List[DeviceInfo]: USB串口设备列表
        """
        usb_devices = []
        all_ports = DeviceManager.list_serial_ports()
        
        for device in all_ports:
            # 检查是否为USB设备
            if ("USB" in device.description.upper() or 
                "CH34" in device.description.upper() or  # CH340/CH341
                "CP21" in device.description.upper() or  # CP2102
                "FT23" in device.description.upper() or  # FTDI
                device.vendor_id != "Unknown"):
                usb_devices.append(device)
        
        return usb_devices
    
    @staticmethod
    def auto_detect_relay_device() -> Optional[str]:
        """
        自动检测继电器设备
        
        Returns:
            Optional[str]: 设备端口路径，如果未找到则返回None
        """
        usb_devices = DeviceManager.find_usb_serial_devices()
        
        # 尝试连接每个USB串口设备
        for device in usb_devices:
            try:
                with USBRelayController(device.port) as controller:
                    if controller.test_connection():
                        return device.port
            except Exception:
                continue
        
        return None
    
    @staticmethod
    def get_platform_specific_ports() -> List[str]:
        """
        获取平台特定的常见串口设备路径
        
        Returns:
            List[str]: 串口设备路径列表
        """
        system = platform.system().lower()
        
        if system == "linux":
            # Linux常见串口设备
            patterns = [
                "/dev/ttyUSB*",
                "/dev/ttyACM*",
                "/dev/ttyS*"
            ]
        elif system == "windows":
            # Windows串口设备
            patterns = [
                "COM*"
            ]
        elif system == "darwin":  # macOS
            # macOS串口设备
            patterns = [
                "/dev/tty.usb*",
                "/dev/cu.usb*",
                "/dev/tty.wchusbserial*"
            ]
        else:
            return []
        
        ports = []
        for pattern in patterns:
            if system == "windows":
                # Windows需要特殊处理
                for i in range(1, 256):
                    ports.append(f"COM{i}")
            else:
                ports.extend(glob.glob(pattern))
        
        return sorted(ports)


class RelaySequence:
    """继电器序列控制类"""
    
    def __init__(self, controller: USBRelayController):
        """
        初始化继电器序列控制
        
        Args:
            controller: USB继电器控制器实例
        """
        self.controller = controller
    
    def pulse_relay(self, relay_id: int, duration: float = 1.0) -> bool:
        """
        继电器脉冲控制（打开->等待->关闭）
        
        Args:
            relay_id: 继电器编号
            duration: 脉冲持续时间（秒）
            
        Returns:
            bool: 操作是否成功
        """
        import time
        
        # 打开继电器
        if not self.controller.turn_on_relay(relay_id):
            return False
        
        # 等待指定时间
        time.sleep(duration)
        
        # 关闭继电器
        return self.controller.turn_off_relay(relay_id)
    
    def sequence_control(self, sequence: List[Tuple[int, bool, float]]) -> bool:
        """
        按序列控制多个继电器
        
        Args:
            sequence: 控制序列，每个元素为(继电器编号, 状态, 延时时间)
            
        Returns:
            bool: 操作是否成功
        """
        import time
        
        for relay_id, state, delay in sequence:
            if not self.controller.set_relay_state(relay_id, state):
                return False
            
            if delay > 0:
                time.sleep(delay)
        
        return True
    
    def running_lights(self, relay_count: int = 4, delay: float = 0.5, cycles: int = 3) -> bool:
        """
        流水灯效果
        
        Args:
            relay_count: 继电器数量
            delay: 每步延时时间
            cycles: 循环次数
            
        Returns:
            bool: 操作是否成功
        """
        import time
        
        try:
            # 先关闭所有继电器
            for i in range(1, relay_count + 1):
                self.controller.turn_off_relay(i)
            
            for cycle in range(cycles):
                # 正向流水
                for i in range(1, relay_count + 1):
                    self.controller.turn_on_relay(i)
                    time.sleep(delay)
                    self.controller.turn_off_relay(i)
                
                # 反向流水
                for i in range(relay_count, 0, -1):
                    self.controller.turn_on_relay(i)
                    time.sleep(delay)
                    self.controller.turn_off_relay(i)
            
            return True
        except Exception:
            return False
