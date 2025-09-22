# USB继电器RTU控制软件

基于Modbus RTU协议的跨平台USB继电器控制软件，完全支持Ubuntu、Windows和macOS操作系统。

## 功能特性

- 🔌 **真正跨平台支持**: 单一代码库支持Ubuntu、Windows和macOS，无需额外配置
- 🪟 **Windows完全适配**: 智能COM端口检测，TCP守护进程，零配置运行
- 🔗 **Modbus RTU协议**: 完整实现Modbus RTU通信协议
- ⚡ **继电器控制**: 支持单个和批量继电器控制
- 📊 **数字量输入**: 实时读取数字量输入状态
- 🖥️ **命令行界面**: 用户友好的CLI界面
- 🎛️ **设备管理**: 自动检测和管理USB串口设备
- ⚙️ **配置管理**: 灵活的配置文件和配置档案管理
- 🎨 **美化输出**: 彩色终端输出和进度指示
- 🚀 **智能守护进程**: 跨平台守护进程模式，支持多终端协作
- ⚡ **高响应性**: 优化的检查周期，提供快速的状态更新

## 安装说明

### 系统要求

- Python 3.8 或更高版本
- USB转串口驱动程序
- 支持的操作系统：Ubuntu 18.04+、Windows 10+、macOS 10.15+

### Windows安装（完全适配）

Windows用户可以享受零配置的完整功能体验：

1. **安装Python依赖**：
```cmd
pip install -r requirements.txt
```

2. **直接使用**（无需管理员权限）：
```cmd
# 自动检测COM端口
python run.py device auto-detect

# 开始使用（示例COM11）
python run.py relay toggle --port COM11 --relay 1
python run.py input monitor --port COM11
```

#### Windows特有优化
- ✅ **智能COM端口检测**: 自动扫描可用的COM端口（COM1-COM256）
- ✅ **TCP守护进程**: 使用TCP套接字代替Unix套接字，确保跨进程通信
- ✅ **零权限要求**: 无需管理员权限，直接运行
- ✅ **驱动程序兼容**: 支持所有Windows串口驱动（CH340/CH341/CP2102/FTDI等）

### Linux/macOS安装

1. 克隆项目仓库：
```bash
git clone https://github.com/fmkong/usb-relay-rtu.git
cd usb-relay-rtu
```

2. 安装依赖：
```bash
pip install -r requirements.txt
```

3. 权限设置（仅Linux需要）：
```bash
sudo usermod -a -G dialout $USER
# 重新登录后生效
```

### 使用pip安装

```bash
pip install usb-relay-rtu
```

## 快速开始

### 1. 检测设备

```bash
# 使用优化的运行脚本（自动处理权限）
python run.py device list
python run.py device usb
python run.py device auto-detect

# 或直接使用原始脚本
python usb_relay.py device list
```

### 2. 继电器控制

```bash
# 使用优化脚本（推荐）
python run.py relay status --port /dev/ttyUSB0
python run.py relay on --port /dev/ttyUSB0 --relay 1
python run.py relay off --port /dev/ttyUSB0 --relay 1
python run.py relay toggle --port /dev/ttyUSB0 --relay 1

# 高级功能
python run.py relay pulse --port /dev/ttyUSB0 --relay 1 --duration 2
python run.py relay running-lights --port /dev/ttyUSB0
```

### 3. 数字量输入

```bash
python run.py input status --port /dev/ttyUSB0
python run.py input monitor --port /dev/ttyUSB0
```

### 4. 设备测试

```bash
python run.py test --port /dev/ttyUSB0
```

### 5. 功能验证

```bash
# 运行核心功能测试
python tests/test_core.py

# 运行功能演示
python tests/demo_simulation.py
```

## 命令参考

### 设备管理命令

- `usb-relay device list` - 列出所有串口设备
- `usb-relay device usb` - 列出USB转串口设备
- `usb-relay device auto-detect` - 自动检测继电器设备
- `usb-relay device info --port <port>` - 获取设备信息

### 继电器控制命令

- `usb-relay relay status --port <port> [--relay <id>]` - 查看继电器状态
- `usb-relay relay on --port <port> --relay <id>` - 打开继电器
- `usb-relay relay off --port <port> --relay <id>` - 关闭继电器
- `usb-relay relay toggle --port <port> --relay <id>` - 切换继电器状态
- `usb-relay relay all-on --port <port>` - 打开所有继电器
- `usb-relay relay all-off --port <port>` - 关闭所有继电器
- `usb-relay relay pulse --port <port> --relay <id> --duration <seconds>` - 继电器脉冲控制
- `usb-relay relay running-lights --port <port>` - 流水灯效果

### 数字量输入命令

- `usb-relay input status --port <port> [--input <id>]` - 查看输入状态
- `usb-relay input monitor --port <port>` - 实时监控输入状态

### 测试命令

- `usb-relay test --port <port>` - 测试设备功能

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

## 硬件支持

### 支持的设备

- 基于Modbus RTU协议的USB继电器模块
- 常见的USB转串口芯片：CH340、CH341、CP2102、FTDI等

### 通信参数

- **协议**: Modbus RTU
- **波特率**: 9600 (可配置)
- **数据位**: 8
- **停止位**: 1
- **校验位**: 无
- **从设备地址**: 1 (可配置)

## 开发指南

### 项目结构

```
usb_relay_rtu/
├── src/
│   ├── __init__.py          # 包初始化
│   ├── modbus_rtu.py        # Modbus RTU协议实现
│   ├── device_controller.py # 设备控制接口
│   ├── cli.py              # 命令行接口
│   ├── config.py           # 配置管理
│   └── utils.py            # 工具函数
├── docs/
│   ├── project_plan.md     # 项目规划
│   ├── api_reference.md    # API参考文档
│   └── user_guide.md       # 用户指南
├── tests/                  # 单元测试
├── requirements.txt        # Python依赖
├── setup.py               # 安装脚本
└── README.md              # 项目说明
```

### 开发环境设置

1. 克隆仓库并创建虚拟环境：
```bash
git clone https://github.com/fmkong/usb-relay-rtu.git
cd usb-relay-rtu
python -m venv venv
source venv/bin/activate  # Linux/macOS
# venv\Scripts\activate   # Windows
```

2. 安装开发依赖：
```bash
pip install -r requirements.txt
pip install -e .[dev]
```

3. 运行测试：
```bash
pytest tests/
```

### API使用示例

```python
from src.device_controller import USBRelayController

# 创建控制器实例
with USBRelayController("/dev/ttyUSB0") as controller:
    # 打开继电器1
    controller.turn_on_relay(1)
    
    # 读取继电器状态
    state = controller.get_relay_state(1)
    print(f"继电器1状态: {state}")
    
    # 读取数字量输入
    input_state = controller.get_input_state(1)
    print(f"输入1状态: {input_state}")
```

## 故障排除

### 常见问题

1. **设备未检测到**
   - 检查USB连接
   - 确认驱动程序已安装
   - 检查设备权限（Linux下可能需要添加用户到dialout组）

2. **通信超时**
   - 检查波特率设置
   - 确认从设备地址正确
   - 检查串口是否被其他程序占用

3. **权限错误（Linux）**
   ```bash
   sudo usermod -a -G dialout $USER
   # 重新登录后生效
   ```

### 调试模式

使用`--verbose`参数启用详细输出：
```bash
usb-relay --verbose relay status --port /dev/ttyUSB0
```

## 许可证

本项目采用 MIT 许可证。详见 [LICENSE](LICENSE) 文件。

## 贡献指南

欢迎贡献代码！请遵循以下步骤：

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建 Pull Request

## 支持

- 📖 [文档](docs/)
- 🐛 [问题反馈](https://github.com/fmkong/usb-relay-rtu/issues)
- 💬 [讨论区](https://github.com/fmkong/usb-relay-rtu/discussions)

## 更新日志

### v1.3.0 (2025-09-22)

#### 🚀 批量控制 + 智能监控优化
- ✅ **多继电器批量控制**: 支持多个`-r`参数同时控制多个继电器
- ✅ **详细状态反馈**: 每个继电器操作显示成功/失败状态和总结统计
- ✅ **智能监控显示**: 状态变化时保留历史记录，稳定时覆盖显示
- ✅ **状态跟踪优化**: 防止冗余换行，保持监控界面简洁清晰
- ✅ **批量操作支持**: `relay on/off/toggle`命令全面支持批量操作

#### 使用示例
```bash
# 同时打开多个继电器
python usb_relay.py relay on -p /dev/ttyUSB0 -r 1 -r 2 -r 3

# 同时切换多个继电器状态
python usb_relay.py relay toggle -p /dev/ttyUSB0 -r 1 -r 2

# 智能监控显示（状态变化保留记录，稳定时覆盖显示）
python usb_relay.py input monitor -p /dev/ttyUSB0
```

### v1.2.0 (2025-09-15)

#### 🪟 Windows完全适配 + 性能优化
- ✅ **Windows原生支持**: TCP守护进程、智能COM端口检测，零配置运行
- ✅ **跨平台IPC**: Windows使用TCP套接字，Linux/macOS使用Unix套接字
- ✅ **高响应性**: 守护进程检查周期从2秒优化到0.5秒，提升4倍响应速度
- ✅ **错误恢复优化**: 错误恢复时间从5秒缩短到2秒，提升60%恢复效率
- ✅ **驱动程序兼容**: 全面支持CH340/CH341/CP2102/FTDI等主流串口芯片
- ✅ **无权限运行**: Windows环境下无需管理员权限，直接使用

### v1.1.0 (2024-09-15)

#### 🚀 重大更新：守护进程通信同步优化
- ✅ **通信同步机制**: 实现队列化串口访问，确保Modbus RTU事务原子性
- ✅ **解决串口冲突**: 彻底解决多终端"接收数据超时"问题
- ✅ **智能避让策略**: 状态更新智能避开命令执行时机
- ✅ **多终端协作**: 支持多个终端安全协作，无串口冲突
- ✅ **线程同步**: 使用RLock和队列机制协调多线程访问

### v1.0.0 (2024-09-15)

- 🎉 首次发布
- ✅ 完整的Modbus RTU协议实现
- ✅ 跨平台支持
- ✅ 命令行界面
- ✅ 设备自动检测
- ✅ 配置文件支持

---

**作者**: Fanming
**邮箱**: kongming2liya@outlook.com
**项目地址**: https://github.com/fmkong/usb_relay_rtu
