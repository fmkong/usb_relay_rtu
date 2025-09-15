"""
配置管理模块

提供系统配置管理功能，包括：
- 设备配置参数
- 通信参数设置
- 用户偏好设置
"""

import os
import json
import yaml
from typing import Dict, Any, Optional, List
from pathlib import Path
from dataclasses import dataclass, asdict


@dataclass
class SerialConfig:
    """串口通信配置"""
    port: str = ""
    baudrate: int = 9600
    timeout: float = 1.0
    bytesize: int = 8
    parity: str = "N"  # N=None, E=Even, O=Odd
    stopbits: int = 1


@dataclass
class DeviceConfig:
    """设备配置"""
    slave_id: int = 1
    max_relays: int = 8
    max_inputs: int = 8
    relay_start_address: int = 0x0000
    input_start_address: int = 0x0000


@dataclass
class UIConfig:
    """界面配置"""
    console_width: int = 120
    show_progress: bool = True
    colored_output: bool = True
    auto_detect_device: bool = True


@dataclass
class AppConfig:
    """应用程序配置"""
    serial: SerialConfig
    device: DeviceConfig
    ui: UIConfig
    
    def __init__(self):
        self.serial = SerialConfig()
        self.device = DeviceConfig()
        self.ui = UIConfig()


class ConfigManager:
    """配置管理器"""
    
    DEFAULT_CONFIG_NAME = "usb_relay_config"
    SUPPORTED_FORMATS = ["json", "yaml", "yml"]
    
    def __init__(self, config_dir: Optional[str] = None):
        """
        初始化配置管理器
        
        Args:
            config_dir: 配置文件目录，如果为None则使用默认目录
        """
        self.config_dir = Path(config_dir) if config_dir else self._get_default_config_dir()
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.config = AppConfig()
    
    def _get_default_config_dir(self) -> Path:
        """获取默认配置目录"""
        # 根据操作系统选择合适的配置目录
        if os.name == "nt":  # Windows
            config_dir = Path(os.environ.get("APPDATA", "")) / "USBRelayRTU"
        else:  # Linux/macOS
            config_dir = Path.home() / ".config" / "usb_relay_rtu"
        
        return config_dir
    
    def _get_config_file_path(self, format: str = "yaml") -> Path:
        """获取配置文件路径"""
        if format not in self.SUPPORTED_FORMATS:
            format = "yaml"
        
        return self.config_dir / f"{self.DEFAULT_CONFIG_NAME}.{format}"
    
    def load_config(self, format: str = "yaml") -> bool:
        """
        加载配置文件
        
        Args:
            format: 配置文件格式 (json, yaml, yml)
            
        Returns:
            bool: 是否加载成功
        """
        config_file = self._get_config_file_path(format)
        
        if not config_file.exists():
            # 尝试其他格式
            for fmt in self.SUPPORTED_FORMATS:
                test_file = self._get_config_file_path(fmt)
                if test_file.exists():
                    config_file = test_file
                    format = fmt
                    break
            else:
                # 没有找到配置文件，使用默认配置
                return False
        
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                if format == "json":
                    data = json.load(f)
                else:  # yaml
                    data = yaml.safe_load(f)
            
            # 更新配置对象
            self._update_config_from_dict(data)
            return True
            
        except Exception as e:
            print(f"加载配置文件失败: {e}")
            return False
    
    def save_config(self, format: str = "yaml") -> bool:
        """
        保存配置文件
        
        Args:
            format: 配置文件格式 (json, yaml, yml)
            
        Returns:
            bool: 是否保存成功
        """
        config_file = self._get_config_file_path(format)
        
        try:
            config_dict = self._config_to_dict()
            
            with open(config_file, 'w', encoding='utf-8') as f:
                if format == "json":
                    json.dump(config_dict, f, indent=2, ensure_ascii=False)
                else:  # yaml
                    yaml.dump(config_dict, f, default_flow_style=False, 
                             allow_unicode=True, indent=2)
            
            return True
            
        except Exception as e:
            print(f"保存配置文件失败: {e}")
            return False
    
    def _config_to_dict(self) -> Dict[str, Any]:
        """将配置对象转换为字典"""
        return {
            "serial": asdict(self.config.serial),
            "device": asdict(self.config.device),
            "ui": asdict(self.config.ui)
        }
    
    def _update_config_from_dict(self, data: Dict[str, Any]) -> None:
        """从字典更新配置对象"""
        if "serial" in data:
            serial_data = data["serial"]
            self.config.serial = SerialConfig(**serial_data)
        
        if "device" in data:
            device_data = data["device"]
            self.config.device = DeviceConfig(**device_data)
        
        if "ui" in data:
            ui_data = data["ui"]
            self.config.ui = UIConfig(**ui_data)
    
    def get_serial_config(self) -> SerialConfig:
        """获取串口配置"""
        return self.config.serial
    
    def get_device_config(self) -> DeviceConfig:
        """获取设备配置"""
        return self.config.device
    
    def get_ui_config(self) -> UIConfig:
        """获取界面配置"""
        return self.config.ui
    
    def update_serial_config(self, **kwargs) -> None:
        """更新串口配置"""
        for key, value in kwargs.items():
            if hasattr(self.config.serial, key):
                setattr(self.config.serial, key, value)
    
    def update_device_config(self, **kwargs) -> None:
        """更新设备配置"""
        for key, value in kwargs.items():
            if hasattr(self.config.device, key):
                setattr(self.config.device, key, value)
    
    def update_ui_config(self, **kwargs) -> None:
        """更新界面配置"""
        for key, value in kwargs.items():
            if hasattr(self.config.ui, key):
                setattr(self.config.ui, key, value)
    
    def reset_to_defaults(self) -> None:
        """重置为默认配置"""
        self.config = AppConfig()
    
    def get_config_file_path(self, format: str = "yaml") -> str:
        """获取配置文件路径字符串"""
        return str(self._get_config_file_path(format))
    
    def config_exists(self, format: str = "yaml") -> bool:
        """检查配置文件是否存在"""
        return self._get_config_file_path(format).exists()


class ProfileManager:
    """配置档案管理器"""
    
    def __init__(self, config_manager: ConfigManager):
        """
        初始化档案管理器
        
        Args:
            config_manager: 配置管理器实例
        """
        self.config_manager = config_manager
        self.profiles_dir = config_manager.config_dir / "profiles"
        self.profiles_dir.mkdir(exist_ok=True)
    
    def save_profile(self, name: str, description: str = "") -> bool:
        """
        保存当前配置为档案
        
        Args:
            name: 档案名称
            description: 档案描述
            
        Returns:
            bool: 是否保存成功
        """
        profile_file = self.profiles_dir / f"{name}.yaml"
        
        try:
            profile_data = {
                "name": name,
                "description": description,
                "created_at": str(Path().cwd()),  # 使用当前时间
                "config": self.config_manager._config_to_dict()
            }
            
            with open(profile_file, 'w', encoding='utf-8') as f:
                yaml.dump(profile_data, f, default_flow_style=False, 
                         allow_unicode=True, indent=2)
            
            return True
            
        except Exception as e:
            print(f"保存档案失败: {e}")
            return False
    
    def load_profile(self, name: str) -> bool:
        """
        加载指定档案
        
        Args:
            name: 档案名称
            
        Returns:
            bool: 是否加载成功
        """
        profile_file = self.profiles_dir / f"{name}.yaml"
        
        if not profile_file.exists():
            return False
        
        try:
            with open(profile_file, 'r', encoding='utf-8') as f:
                profile_data = yaml.safe_load(f)
            
            if "config" in profile_data:
                self.config_manager._update_config_from_dict(profile_data["config"])
                return True
            
            return False
            
        except Exception as e:
            print(f"加载档案失败: {e}")
            return False
    
    def list_profiles(self) -> List[Dict[str, str]]:
        """
        列出所有档案
        
        Returns:
            List[Dict[str, str]]: 档案信息列表
        """
        profiles = []
        
        for profile_file in self.profiles_dir.glob("*.yaml"):
            try:
                with open(profile_file, 'r', encoding='utf-8') as f:
                    profile_data = yaml.safe_load(f)
                
                profiles.append({
                    "name": profile_data.get("name", profile_file.stem),
                    "description": profile_data.get("description", ""),
                    "file": str(profile_file)
                })
                
            except Exception:
                continue
        
        return profiles
    
    def delete_profile(self, name: str) -> bool:
        """
        删除指定档案
        
        Args:
            name: 档案名称
            
        Returns:
            bool: 是否删除成功
        """
        profile_file = self.profiles_dir / f"{name}.yaml"
        
        if profile_file.exists():
            try:
                profile_file.unlink()
                return True
            except Exception:
                return False
        
        return False


# 全局配置管理器实例
_config_manager = None


def get_config_manager() -> ConfigManager:
    """获取全局配置管理器实例"""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
        _config_manager.load_config()
    return _config_manager


def get_profile_manager() -> ProfileManager:
    """获取档案管理器实例"""
    return ProfileManager(get_config_manager())
