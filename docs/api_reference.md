# API参考文档

本文档提供USB继电器RTU控制软件的详细API参考。

## 模块概览

### modbus_rtu.py - Modbus RTU协议实现

#### ModbusCRC16类

**计算CRC16校验码**
```python
@classmethod
def calculate(cls, data: bytes) -> Tuple[int, int]
```
- 参数：`data` - 需要计算CRC的数据
- 返回：`(CRC低字节, CRC高字节)`

**验证CRC16校验码**
```python
@classmethod
def verify(cls, data: bytes) -> bool
```
- 参数：`data` - 包含CRC的完整数据帧
- 返回：校验是否正确

#### ModbusRTUClient类

**初始化客户端**
```python
def __init__(self, port: str, baudrate: int = 9600, timeout: float = 1.0)
```

**读取线圈状态**
```python
def read_coils(self, slave_id: int, start_address: int, count: int) -> List[bool]
```

**读取离散输入状态**
```python
def read_discrete_inputs(self, slave_id: int, start_address: int, count: int) -> List[bool]
```

**写单个线圈**
```python
def write_single_coil(self, slave_id: int, address: int, value: bool) -> bool
```

**写多个线圈**
```python
def write_multiple_coils(self, slave_id: int, start_address: int, values: List[bool]) -> bool
```

### device_controller.py - 设备控制接口

#### USBRelayController类

**初始化控制器**
```python
def __init__(self, port: str, slave_id: int = 1, baudrate: int = 9600, timeout: float = 1.0)
```

**继电器控制方法**
```python
def turn_on_relay(self, relay_id: int) -> bool
def turn_off_relay(self, relay_id: int) -> bool
def toggle_relay(self, relay_id: int) -> bool
def get_relay_state(self, relay_id: int) -> RelayState
```

**数字量输入方法**
```python
def get_input_state(self, input_id: int) -> InputState
def get_input_states(self, start_input: int, count: int) -> List[InputState]
```

#### DeviceManager类

**设备检测方法**
```python
@staticmethod
def list_serial_ports() -> List[DeviceInfo]

@staticmethod
def find_usb_serial_devices() -> List[DeviceInfo]

@staticmethod
def auto_detect_relay_device() -> Optional[str]
```

## 使用示例

### 基本继电器控制

```python
from src.device_controller import USBRelayController

# 使用上下文管理器确保正确关闭连接
with USBRelayController("/dev/ttyUSB0") as controller:
    # 打开继电器1
    success = controller.turn_on_relay(1)
    if success:
        print("继电器1已打开")
    
    # 读取继电器状态
    state = controller.get_relay_state(1)
    print(f"继电器1状态: {state}")
    
    # 读取所有继电器状态
    all_states = controller.get_all_relay_states()
    for state in all_states:
        print(state)
```

### 数字量输入读取

```python
with USBRelayController("/dev/ttyUSB0") as controller:
    # 读取单个输入
    input_state = controller.get_input_state(1)
    print(f"输入1状态: {input_state}")
    
    # 读取所有输入
    all_inputs = controller.get_all_input_states()
    for input_state in all_inputs:
        print(input_state)
```

### 设备管理

```python
from src.device_controller import DeviceManager

# 列出所有串口设备
devices = DeviceManager.list_serial_ports()
for device in devices:
    print(device)

# 查找USB串口设备
usb_devices = DeviceManager.find_usb_serial_devices()
for device in usb_devices:
    print(f"USB设备: {device.port}")

# 自动检测继电器设备
relay_port = DeviceManager.auto_detect_relay_device()
if relay_port:
    print(f"找到继电器设备: {relay_port}")
```

### 低级Modbus操作

```python
from src.modbus_rtu import ModbusRTUClient

client = ModbusRTUClient("/dev/ttyUSB0")
client.connect()

try:
    # 读取线圈状态
    coils = client.read_coils(slave_id=1, start_address=0, count=8)
    print(f"线圈状态: {coils}")
    
    # 写单个线圈
    success = client.write_single_coil(slave_id=1, address=0, value=True)
    print(f"写入成功: {success}")
    
finally:
    client.disconnect()
```

## 数据类型

### RelayState
```python
@dataclass
class RelayState:
    relay_id: int    # 继电器编号
    state: bool      # 继电器状态
    address: int     # 寄存器地址
```

### InputState
```python
@dataclass
class InputState:
    input_id: int    # 输入编号
    state: bool      # 输入状态
    address: int     # 寄存器地址
```

### DeviceInfo
```python
@dataclass
class DeviceInfo:
    port: str           # 端口路径
    description: str    # 设备描述
    manufacturer: str   # 制造商
    vendor_id: str      # 厂商ID
    product_id: str     # 产品ID
    serial_number: str  # 序列号
```

## 异常处理

### ModbusRTU异常
- `ModbusRTUException` - 基础异常
- `ModbusRTUTimeoutException` - 超时异常
- `ModbusRTUCRCException` - CRC校验异常

### 异常处理示例
```python
from src.modbus_rtu import ModbusRTUException, ModbusRTUTimeoutException

try:
    with USBRelayController("/dev/ttyUSB0") as controller:
        controller.turn_on_relay(1)
except ModbusRTUTimeoutException:
    print("通信超时，请检查设备连接")
except ModbusRTUException as e:
    print(f"Modbus通信错误: {e}")
except Exception as e:
    print(f"未知错误: {e}")
```

## 配置管理

### 配置文件示例
```yaml
serial:
  port: "/dev/ttyUSB0"
  baudrate: 9600
  timeout: 1.0
  bytesize: 8
  parity: "N"
  stopbits: 1

device:
  slave_id: 1
  max_relays: 8
  max_inputs: 8
  relay_start_address: 0
  input_start_address: 0

ui:
  console_width: 120
  show_progress: true
  colored_output: true
  auto_detect_device: true
```

### 配置管理API
```python
from src.config import get_config_manager

config_manager = get_config_manager()

# 获取配置
serial_config = config_manager.get_serial_config()
device_config = config_manager.get_device_config()

# 更新配置
config_manager.update_serial_config(port="/dev/ttyUSB1")
config_manager.save_config()
