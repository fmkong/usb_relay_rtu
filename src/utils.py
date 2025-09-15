"""
工具函数模块

提供常用的工具函数，包括：
- 数据转换工具
- 日志记录工具
- 系统信息获取
- 其他辅助函数
"""

import sys
import platform
import logging
import time
from typing import List, Dict, Any, Optional, Union
from pathlib import Path
import re


def setup_logging(log_level: str = "INFO", log_file: Optional[str] = None) -> logging.Logger:
    """
    设置日志记录
    
    Args:
        log_level: 日志级别 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: 日志文件路径，如果为None则只输出到控制台
        
    Returns:
        logging.Logger: 配置好的日志记录器
    """
    # 创建日志记录器
    logger = logging.getLogger("usb_relay_rtu")
    
    # 清除现有的处理器
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # 设置日志级别
    level = getattr(logging, log_level.upper(), logging.INFO)
    logger.setLevel(level)
    
    # 创建格式化器
    formatter = logging.Formatter(
        fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # 文件处理器（如果指定了日志文件）
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger


def bytes_to_hex_string(data: bytes, separator: str = " ") -> str:
    """
    将字节数据转换为十六进制字符串
    
    Args:
        data: 字节数据
        separator: 分隔符
        
    Returns:
        str: 十六进制字符串
    """
    return separator.join(f"{byte:02X}" for byte in data)


def hex_string_to_bytes(hex_str: str) -> bytes:
    """
    将十六进制字符串转换为字节数据
    
    Args:
        hex_str: 十六进制字符串，可以包含空格、逗号等分隔符
        
    Returns:
        bytes: 字节数据
    """
    # 清理字符串，只保留十六进制字符
    cleaned = re.sub(r'[^0-9A-Fa-f]', '', hex_str)
    
    # 确保长度为偶数
    if len(cleaned) % 2 != 0:
        cleaned = '0' + cleaned
    
    return bytes.fromhex(cleaned)


def parse_relay_list(relay_str: str) -> List[int]:
    """
    解析继电器列表字符串
    
    Args:
        relay_str: 继电器列表字符串，例如："1,2,3" 或 "1-4" 或 "1,3-5,7"
        
    Returns:
        List[int]: 继电器编号列表
    """
    relays = []
    
    # 分割逗号分隔的部分
    parts = relay_str.split(',')
    
    for part in parts:
        part = part.strip()
        
        if '-' in part:
            # 处理范围，例如 "1-4"
            start, end = part.split('-', 1)
            start = int(start.strip())
            end = int(end.strip())
            relays.extend(range(start, end + 1))
        else:
            # 单个继电器
            relays.append(int(part))
    
    # 去重并排序
    return sorted(list(set(relays)))


def validate_relay_id(relay_id: int, max_relays: int = 8) -> bool:
    """
    验证继电器编号是否有效
    
    Args:
        relay_id: 继电器编号
        max_relays: 最大继电器数量
        
    Returns:
        bool: 是否有效
    """
    return 1 <= relay_id <= max_relays


def validate_input_id(input_id: int, max_inputs: int = 8) -> bool:
    """
    验证输入编号是否有效
    
    Args:
        input_id: 输入编号
        max_inputs: 最大输入数量
        
    Returns:
        bool: 是否有效
    """
    return 1 <= input_id <= max_inputs


def get_system_info() -> Dict[str, Any]:
    """
    获取系统信息
    
    Returns:
        Dict[str, Any]: 系统信息字典
    """
    info = {
        "platform": platform.platform(),
        "system": platform.system(),
        "version": platform.version(),
        "architecture": platform.architecture(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "python_version": platform.python_version(),
        "python_implementation": platform.python_implementation(),
    }
    
    return info


def format_duration(seconds: float) -> str:
    """
    格式化时间长度
    
    Args:
        seconds: 秒数
        
    Returns:
        str: 格式化的时间字符串
    """
    if seconds < 1:
        return f"{seconds*1000:.0f}ms"
    elif seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = seconds // 60
        secs = seconds % 60
        return f"{minutes:.0f}m {secs:.0f}s"
    else:
        hours = seconds // 3600
        remaining = seconds % 3600
        minutes = remaining // 60
        secs = remaining % 60
        return f"{hours:.0f}h {minutes:.0f}m {secs:.0f}s"


def format_file_size(size_bytes: int) -> str:
    """
    格式化文件大小
    
    Args:
        size_bytes: 字节数
        
    Returns:
        str: 格式化的大小字符串
    """
    if size_bytes == 0:
        return "0B"
    
    size_names = ["B", "KB", "MB", "GB", "TB", "PB"]
    i = 0
    
    while size_bytes >= 1024.0 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    
    return f"{size_bytes:.1f}{size_names[i]}"


def retry_operation(func, max_retries: int = 3, delay: float = 1.0, backoff_factor: float = 2.0):
    """
    重试操作装饰器
    
    Args:
        func: 要重试的函数
        max_retries: 最大重试次数
        delay: 初始延时时间（秒）
        backoff_factor: 退避因子
        
    Returns:
        装饰器函数
    """
    def decorator(function):
        def wrapper(*args, **kwargs):
            last_exception = None
            current_delay = delay
            
            for attempt in range(max_retries + 1):
                try:
                    return function(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    
                    if attempt < max_retries:
                        time.sleep(current_delay)
                        current_delay *= backoff_factor
                    else:
                        raise last_exception
            
            return None
        return wrapper
    
    if func is None:
        return decorator
    else:
        return decorator(func)


def safe_int_convert(value: Any, default: int = 0) -> int:
    """
    安全的整数转换
    
    Args:
        value: 要转换的值
        default: 默认值
        
    Returns:
        int: 转换后的整数
    """
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def safe_float_convert(value: Any, default: float = 0.0) -> float:
    """
    安全的浮点数转换
    
    Args:
        value: 要转换的值
        default: 默认值
        
    Returns:
        float: 转换后的浮点数
    """
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def is_valid_port_name(port: str) -> bool:
    """
    验证串口名称是否有效
    
    Args:
        port: 串口名称
        
    Returns:
        bool: 是否有效
    """
    if not port:
        return False
    
    system = platform.system().lower()
    
    if system == "windows":
        # Windows: COM1, COM2, etc.
        return re.match(r'^COM\d+$', port, re.IGNORECASE) is not None
    elif system == "linux":
        # Linux: /dev/ttyUSB0, /dev/ttyACM0, etc.
        return re.match(r'^/dev/tty(USB|ACM|S)\d+$', port) is not None
    elif system == "darwin":  # macOS
        # macOS: /dev/tty.usbserial-*, /dev/cu.usbserial-*, etc.
        return re.match(r'^/dev/(tty|cu)\.(usb|wchusbserial)', port) is not None
    
    return True  # 其他系统暂时返回True


def create_backup_filename(original_path: str) -> str:
    """
    创建备份文件名
    
    Args:
        original_path: 原始文件路径
        
    Returns:
        str: 备份文件路径
    """
    path = Path(original_path)
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    backup_name = f"{path.stem}_backup_{timestamp}{path.suffix}"
    return str(path.parent / backup_name)


def ensure_directory_exists(directory: Union[str, Path]) -> Path:
    """
    确保目录存在，如果不存在则创建
    
    Args:
        directory: 目录路径
        
    Returns:
        Path: 目录Path对象
    """
    dir_path = Path(directory)
    dir_path.mkdir(parents=True, exist_ok=True)
    return dir_path


def get_available_filename(base_path: Union[str, Path]) -> Path:
    """
    获取可用的文件名（如果文件已存在，则添加数字后缀）
    
    Args:
        base_path: 基础文件路径
        
    Returns:
        Path: 可用的文件路径
    """
    path = Path(base_path)
    
    if not path.exists():
        return path
    
    counter = 1
    while True:
        new_path = path.parent / f"{path.stem}_{counter}{path.suffix}"
        if not new_path.exists():
            return new_path
        counter += 1


class Timer:
    """简单的计时器类"""
    
    def __init__(self):
        self.start_time = None
        self.end_time = None
    
    def start(self):
        """开始计时"""
        self.start_time = time.time()
        self.end_time = None
    
    def stop(self) -> float:
        """停止计时并返回经过的时间"""
        if self.start_time is None:
            return 0.0
        
        self.end_time = time.time()
        return self.elapsed()
    
    def elapsed(self) -> float:
        """获取经过的时间"""
        if self.start_time is None:
            return 0.0
        
        end_time = self.end_time if self.end_time is not None else time.time()
        return end_time - self.start_time
    
    def __enter__(self):
        """上下文管理器入口"""
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.stop()


def validate_modbus_address(address: int) -> bool:
    """
    验证Modbus地址是否有效
    
    Args:
        address: Modbus地址
        
    Returns:
        bool: 是否有效
    """
    return 0 <= address <= 0xFFFF


def validate_slave_id(slave_id: int) -> bool:
    """
    验证从设备地址是否有效
    
    Args:
        slave_id: 从设备地址
        
    Returns:
        bool: 是否有效
    """
    return 1 <= slave_id <= 247


def calculate_expected_response_length(function_code: int, data_length: int) -> int:
    """
    计算预期的响应长度
    
    Args:
        function_code: 功能码
        data_length: 数据长度
        
    Returns:
        int: 预期响应长度
    """
    # 基本长度：从设备地址(1) + 功能码(1) + CRC(2) = 4字节
    base_length = 4
    
    if function_code in [0x01, 0x02]:  # 读线圈/离散输入
        # 字节数(1) + 数据字节
        return base_length + 1 + ((data_length + 7) // 8)
    elif function_code in [0x03, 0x04]:  # 读寄存器
        # 字节数(1) + 数据字节
        return base_length + 1 + (data_length * 2)
    elif function_code in [0x05, 0x06]:  # 写单个
        # 地址(2) + 值(2)
        return base_length + 4
    elif function_code in [0x0F, 0x10]:  # 写多个
        # 地址(2) + 数量(2)
        return base_length + 4
    else:
        # 未知功能码，返回最小长度
        return base_length
