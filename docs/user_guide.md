# USB继电器RTU控制软件用户指南

## 简介

USB继电器RTU控制软件是一个基于Modbus RTU协议的跨平台命令行工具，用于控制USB继电器模块和读取数字量输入。

## 系统要求

- Python 3.8 或更高版本
- 支持的操作系统：Ubuntu 18.04+、Windows 10+、macOS 10.15+
- USB转串口驱动程序

## 安装指南

### 1. 从源码安装

```bash
# 克隆或下载项目
cd usb_relay_rtu

# 安装依赖
pip install -r requirements.txt

# 直接运行（推荐）
python usb_relay.py --help

# 或者安装到系统
pip install -e .
usb-relay --help
```

### 2. Linux权限设置

在Linux系统下，需要将用户添加到`dialout`组以访问串口设备：

```bash
# 添加用户到dialout组
sudo usermod -a -G dialout $USER

# 重新登录或重启使更改生效
```

### 3. 验证安装

```bash
# 运行核心功能测试
python test_core.py

# 运行功能演示
python demo_simulation.py
```

## 基本使用

### 设备检测

```bash
# 列出所有串口设备
python usb_relay.py device list

# 列出USB串口设备
python usb_relay.py device usb

# 自动检测继电器设备
python usb_relay.py device auto-detect

# 获取设备信息
python usb_relay.py device info --port /dev/ttyUSB0
```

### 继电器控制

```bash
# 查看继电器状态
python usb_relay.py relay status --port /dev/ttyUSB0

# 打开继电器
python usb_relay.py relay on --port /dev/ttyUSB0 --relay 1

# 关闭继电器
python usb_relay.py relay off --port /dev/ttyUSB0 --relay 1

# 切换继电器状态
python usb_relay.py relay toggle --port /dev/ttyUSB0 --relay 1

# 关闭所有继电器
python usb_relay.py relay all-off --port /dev/ttyUSB0
```

### 数字量输入

```bash
# 查看输入状态
python usb_relay.py input status --port /dev/ttyUSB0

# 实时监控输入（按Ctrl+C退出）
python usb_relay.py input monitor --port /dev/ttyUSB0
```

### 高级功能

```bash
# 继电器脉冲控制（1秒）
python usb_relay.py relay pulse --port /dev/ttyUSB0 --relay 1 --duration 1.0

# 流水灯效果
python usb_relay.py relay running-lights --port /dev/ttyUSB0 --count 4

# 设备功能测试
python usb_relay.py test --port /dev/ttyUSB0
```

## 命令参数说明

### 通用参数

- `--port` / `-p`: 设备端口路径（必需）
- `--slave-id` / `-s`: 从设备地址（默认：1）
- `--help`: 显示帮助信息

### 继电器参数

- `--relay` / `-r`: 继电器编号（1-8）
- `--count` / `-c`: 继电器/输入数量
- `--duration` / `-d`: 脉冲持续时间（秒）
- `--delay`: 延时时间（秒）
- `--cycles`: 循环次数

### 监控参数

- `--input` / `-i`: 输入编号（1-8）
- `--interval`: 监控间隔（秒）

## 配置文件

软件支持配置文件来保存常用设置：

### 配置文件位置

- **Linux/macOS**: `~/.config/usb_relay_rtu/usb_relay_config.yaml`
- **Windows**: `%APPDATA%\USBRelayRTU\usb_relay_config.yaml`

### 配置示例

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

## 故障排除

### 常见问题

1. **权限被拒绝 (Permission denied)**
   ```bash
   # Linux解决方案
   sudo usermod -a -G dialout $USER
   # 然后重新登录
   ```

2. **设备未找到**
   - 检查USB连接
   - 确认驱动程序已安装
   - 检查设备路径是否正确

3. **通信超时**
   - 检查波特率设置（默认9600）
   - 确认从设备地址正确（默认1）
   - 检查设备是否支持Modbus RTU协议

4. **CRC校验失败**
   - 检查数据传输是否有干扰
   - 确认设备协议实现正确
   - 检查连接线缆质量

### 调试模式

暂时没有专门的调试模式，但可以通过以下方式获取详细信息：

1. 查看详细的错误消息
2. 使用设备测试功能验证连接
3. 检查系统日志

## 硬件兼容性

### 支持的设备

- 基于Modbus RTU协议的USB继电器模块
- 常见的USB转串口芯片：
  - CH340/CH341 (VID: 0x1a86)
  - CP2102 (Silicon Labs)
  - FTDI FT232
  - Prolific PL2303

### 通信参数

- **协议**: Modbus RTU
- **波特率**: 9600 (可配置)
- **数据位**: 8
- **停止位**: 1
- **校验位**: 无
- **从设备地址**: 1 (可配置)

### 功能映射

- **继电器控制**: 线圈寄存器 (功能码 01H, 05H, 0FH)
- **数字量输入**: 离散输入寄存器 (功能码 02H)
- **状态查询**: 读线圈/输入状态
- **批量操作**: 支持多继电器同时控制

## API编程接口

### Python API示例

```python
from src.device_controller import USBRelayController

# 使用上下文管理器
with USBRelayController("/dev/ttyUSB0") as controller:
    # 打开继电器1
    success = controller.turn_on_relay(1)
    print(f"操作成功: {success}")
    
    # 读取状态
    state = controller.get_relay_state(1)
    print(f"继电器1状态: {state}")
    
    # 读取输入
    input_state = controller.get_input_state(1)
    print(f"输入1状态: {input_state}")
```

更多API示例请参考 [API参考文档](api_reference.md)。

## 支持与帮助

- 查看 [README.md](../README.md) 了解项目概述
- 查看 [API参考文档](api_reference.md) 了解编程接口
- 运行 `python demo_simulation.py` 查看功能演示
- 运行 `python test_core.py` 验证核心功能

## 许可证

本项目采用 MIT 许可证。
