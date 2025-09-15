"""
USB继电器RTU守护进程模块

实现健壮的守护进程模式：
- 单一串口连接，避免多进程冲突
- 智能命令执行：自动检测daemon状态
- 异常处理和重试机制
- 简单可靠的通信协议
"""

import json
import socket
import threading
import time
import platform
from typing import Dict, Any, Optional
from pathlib import Path
import tempfile
import os
import signal
import sys

try:
    from .device_controller import USBRelayController
    from .modbus_rtu import ModbusRTUException
except ImportError:
    from device_controller import USBRelayController
    from modbus_rtu import ModbusRTUException


class USBRelayDaemon:
    """USB继电器守护进程 - 跨平台兼容版本"""
    
    def __init__(self, port: str, slave_id: int = 1, count: int = 4):
        self.port = port
        self.slave_id = slave_id
        self.count = count
        self.controller: Optional[USBRelayController] = None
        self.running = False
        
        # 跨平台IPC通信方式
        self.is_windows = platform.system().lower() == "windows"
        
        if self.is_windows:
            # Windows: 使用TCP套接字
            self.tcp_port = self._find_free_port()
            self.socket_path = f"127.0.0.1:{self.tcp_port}"
            self.lock_file_path = Path(tempfile.gettempdir()) / f"usb_relay_daemon_{port.replace('/', '_').replace(':', '_')}.lock"
        else:
            # Linux/macOS: 使用Unix套接字
            self.socket_path = str(Path(tempfile.gettempdir()) / f"usb_relay_daemon_{port.replace('/', '_')}.sock")
            self.lock_file_path = None
            
        self.server_socket = None
        
        # 串口访问锁
        self.serial_lock = threading.Lock()
        
        # 状态缓存（用于监控显示）
        self.last_relay_states = [False] * count
        self.last_input_states = [False] * count
        self.last_status_time = 0
        self.status_cache_lock = threading.Lock()
    
    def _find_free_port(self) -> int:
        """查找空闲的TCP端口（Windows专用）"""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('', 0))
            s.listen(1)
            port = s.getsockname()[1]
        return port
    
    def _create_lock_file(self):
        """创建锁文件记录端口信息（Windows专用）"""
        if self.is_windows and self.lock_file_path:
            with open(self.lock_file_path, 'w') as f:
                f.write(str(self.tcp_port))
    
    def _remove_lock_file(self):
        """删除锁文件（Windows专用）"""
        if self.lock_file_path and self.lock_file_path.exists():
            os.unlink(self.lock_file_path)
        
    def start(self):
        """启动守护进程 - 跨平台版本"""
        try:
            # 连接设备
            self.controller = USBRelayController(self.port, self.slave_id)
            self.controller.connect()
            
            # 跨平台创建套接字
            if self.is_windows:
                # Windows: TCP套接字
                self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                self.server_socket.bind(('127.0.0.1', self.tcp_port))
                self._create_lock_file()
            else:
                # Linux/macOS: Unix套接字
                if os.path.exists(self.socket_path):
                    os.unlink(self.socket_path)
                self.server_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                self.server_socket.bind(self.socket_path)
            
            self.server_socket.listen(5)
            self.running = True
            
            print(f"USB继电器守护进程已启动")
            print(f"设备: {self.port}")
            print(f"平台: {platform.system()}")
            if self.is_windows:
                print(f"TCP端口: {self.tcp_port}")
            else:
                print(f"Socket: {self.socket_path}")
            print("✓ 跨平台守护进程模式 - 智能串口管理")
            print("按 Ctrl+C 停止")
            
            # 启动后台状态更新线程（低频，避免冲突）
            threading.Thread(target=self._background_status_update, daemon=True).start()
            
            # 主循环处理客户端
            while self.running:
                try:
                    client_socket, addr = self.server_socket.accept()
                    # 每个客户端在独立线程中处理，但串口访问受锁保护
                    threading.Thread(
                        target=self._handle_client_safe,
                        args=(client_socket,),
                        daemon=True
                    ).start()
                except Exception as e:
                    if self.running:
                        continue
                    break
                
        except Exception as e:
            print(f"守护进程启动失败: {e}")
            self.stop()
            
    def stop(self):
        """停止守护进程 - 跨平台版本"""
        self.running = False
        
        if self.controller:
            self.controller.disconnect()
            
        if self.server_socket:
            self.server_socket.close()
            
        # 跨平台清理
        if self.is_windows:
            self._remove_lock_file()
        else:
            if os.path.exists(self.socket_path):
                os.unlink(self.socket_path)
            
        print("守护进程已停止")
    
    def _background_status_update(self):
        """后台状态更新线程 - 低频更新避免冲突"""
        while self.running:
            try:
                # 尝试获取锁，如果获取不到就跳过这次更新
                if self.serial_lock.acquire(blocking=False):
                    try:
                        # 读取当前状态
                        relay_states = self.controller.get_all_relay_states(self.count)
                        relay_list = [s.state for s in relay_states]
                        
                        input_states = self.controller.get_all_input_states(self.count)
                        input_list = [s.state for s in input_states]
                        
                        # 更新缓存
                        with self.status_cache_lock:
                            self.last_relay_states = relay_list
                            self.last_input_states = input_list
                            self.last_status_time = time.time()
                            
                    finally:
                        self.serial_lock.release()
                
                # 状态更新间隔2秒，避免频繁访问
                time.sleep(2.0)
                
            except Exception as e:
                if self.running:
                    print(f"\n后台状态更新错误: {e}")
                time.sleep(5.0)  # 出错后等待更长时间
    
    def _handle_client_safe(self, client_socket):
        """安全处理客户端连接"""
        try:
            # 设置socket超时
            client_socket.settimeout(10.0)
            
            while self.running:
                data = client_socket.recv(1024)
                if not data:
                    break
                
                try:
                    request = json.loads(data.decode())
                    
                    # 使用锁保护串口访问，带超时避免死锁
                    acquired = self.serial_lock.acquire(timeout=3.0)
                    if not acquired:
                        response = {"success": False, "error": "设备忙碌，请稍后重试"}
                    else:
                        try:
                            response = self._process_request_with_retry(request)
                        finally:
                            self.serial_lock.release()
                    
                    # 发送响应
                    client_socket.send(json.dumps(response).encode())
                    
                except Exception as e:
                    error_response = {"success": False, "error": str(e)}
                    try:
                        client_socket.send(json.dumps(error_response).encode())
                    except:
                        break
                    
        except Exception:
            pass
        finally:
            try:
                client_socket.close()
            except:
                pass
    
    def _process_request_with_retry(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """处理请求，带重试机制"""
        command = request.get("command")
        max_retries = 2
        
        for attempt in range(max_retries + 1):
            try:
                if command == "get_status":
                    # 返回缓存状态，避免每次都读取
                    with self.status_cache_lock:
                        return {
                            "success": True,
                            "relay_states": self.last_relay_states.copy(),
                            "input_states": self.last_input_states.copy(),
                            "last_update": self.last_status_time
                        }
                
                elif command == "set_relay":
                    relay_id = request.get("relay_id")
                    state = request.get("state")
                    
                    if state is None:  # toggle
                        success = self.controller.toggle_relay(relay_id)
                    else:
                        success = self.controller.set_relay_state(relay_id, state)
                    
                    return {"success": success}
                
                elif command == "pulse_relay":
                    relay_id = request.get("relay_id")
                    duration = request.get("duration", 1.0)
                    
                    self.controller.turn_on_relay(relay_id)
                    time.sleep(duration)
                    self.controller.turn_off_relay(relay_id)
                    
                    return {"success": True}
                
                else:
                    return {"success": False, "error": "未知命令"}
                    
            except Exception as e:
                if attempt < max_retries:
                    print(f"\n命令执行失败，重试 {attempt + 1}/{max_retries}: {e}")
                    time.sleep(0.1)  # 短暂等待后重试
                    continue
                else:
                    return {"success": False, "error": str(e)}


class DaemonClient:
    """守护进程客户端 - 跨平台版本，性能优化"""
    
    def __init__(self, port: str):
        self.port = port
        self.is_windows = platform.system().lower() == "windows"
        
        if self.is_windows:
            # Windows: 使用锁文件检测和TCP通信
            self.lock_file_path = Path(tempfile.gettempdir()) / f"usb_relay_daemon_{port.replace('/', '_').replace(':', '_')}.lock"
            self._cached_tcp_port = None  # 缓存TCP端口，避免重复读取
        else:
            # Linux/macOS: 使用Unix套接字
            self.socket_path = str(Path(tempfile.gettempdir()) / f"usb_relay_daemon_{port.replace('/', '_')}.sock")
    
    def is_daemon_running(self) -> bool:
        """检查守护进程是否运行 - 跨平台版本"""
        if self.is_windows:
            return self.lock_file_path.exists()
        else:
            return os.path.exists(self.socket_path)
    
    def _get_tcp_port(self) -> int:
        """获取TCP端口号（Windows专用，带缓存优化）"""
        # 性能优化：使用缓存避免重复读取锁文件
        if self._cached_tcp_port is not None:
            return self._cached_tcp_port
            
        if not self.lock_file_path.exists():
            raise Exception("守护进程未运行")
            
        try:
            with open(self.lock_file_path, 'r') as f:
                self._cached_tcp_port = int(f.read().strip())
                return self._cached_tcp_port
        except Exception:
            # 缓存失效，清除缓存
            self._cached_tcp_port = None
            raise
    
    def send_command(self, command: str, **kwargs) -> Dict[str, Any]:
        """发送命令到守护进程，带重试机制 - 跨平台版本，性能优化"""
        if not self.is_daemon_running():
            raise Exception("守护进程未运行")
        
        max_retries = 1 if self.is_windows else 2  # Windows减少重试次数
        for attempt in range(max_retries + 1):
            try:
                if self.is_windows:
                    # Windows性能优化：复用TCP连接配置
                    tcp_port = self._get_tcp_port()
                    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    client_socket.settimeout(2.0)  # 缩短超时时间
                    client_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)  # 禁用Nagle算法
                    client_socket.connect(('127.0.0.1', tcp_port))
                else:
                    # Linux/macOS: Unix套接字
                    client_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                    client_socket.settimeout(5.0)
                    client_socket.connect(self.socket_path)
                
                request = {"command": command, **kwargs}
                client_socket.send(json.dumps(request).encode())
                
                response_data = client_socket.recv(1024)
                response = json.loads(response_data.decode())
                
                client_socket.close()
                return response
                
            except Exception as e:
                if attempt < max_retries:
                    # Windows优化：更短的重试间隔
                    time.sleep(0.05 if self.is_windows else 0.1)
                    continue
                else:
                    # 清除缓存，以防端口变化
                    if self.is_windows:
                        self._cached_tcp_port = None
                    raise Exception(f"与守护进程通信失败: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """获取设备状态"""
        return self.send_command("get_status")
    
    def set_relay(self, relay_id: int, state: Optional[bool] = None) -> bool:
        """设置继电器状态"""
        response = self.send_command("set_relay", relay_id=relay_id, state=state)
        return response.get("success", False)
    
    def pulse_relay(self, relay_id: int, duration: float = 1.0) -> bool:
        """继电器脉冲控制"""
        response = self.send_command("pulse_relay", relay_id=relay_id, duration=duration)
        return response.get("success", False)


def execute_relay_command_smart(port: str, slave_id: int, relay_id: int, action: str, duration: Optional[float] = None):
    """
    智能执行继电器命令：
    - 如果守护进程运行，通过守护进程执行
    - 如果守护进程未运行，直接执行
    """
    client = DaemonClient(port)
    
    if client.is_daemon_running():
        # 通过守护进程执行
        try:
            if action == "on":
                return client.set_relay(relay_id, True)
            elif action == "off":
                return client.set_relay(relay_id, False)
            elif action == "toggle":
                return client.set_relay(relay_id, None)
            elif action == "pulse":
                return client.pulse_relay(relay_id, duration or 1.0)
            else:
                return False
        except Exception:
            # 守护进程通信失败，回退到直接模式
            pass
    
    # 直接执行模式
    try:
        with USBRelayController(port, slave_id) as controller:
            if action == "on":
                return controller.turn_on_relay(relay_id)
            elif action == "off":
                return controller.turn_off_relay(relay_id)
            elif action == "toggle":
                return controller.toggle_relay(relay_id)
            elif action == "pulse":
                from device_controller import RelaySequence
                sequence = RelaySequence(controller)
                return sequence.pulse_relay(relay_id, duration or 1.0)
            else:
                return False
    except Exception:
        return False


def get_status_smart(port: str, slave_id: int, count: int = 4):
    """
    智能获取状态：
    - 如果守护进程运行，通过守护进程获取
    - 如果守护进程未运行，直接获取
    """
    client = DaemonClient(port)
    
    if client.is_daemon_running():
        try:
            return client.get_status()
        except Exception:
            # 守护进程通信失败，回退到直接模式
            pass
    
    # 直接模式
    try:
        with USBRelayController(port, slave_id) as controller:
            relay_states = controller.get_all_relay_states(count)
            relay_list = [s.state for s in relay_states]
            
            input_states = controller.get_all_input_states(count)
            input_list = [s.state for s in input_states]
            
            return {
                "success": True,
                "relay_states": relay_list,
                "input_states": input_list,
                "last_update": time.time()
            }
    except Exception as e:
        return {"success": False, "error": str(e)}


def start_daemon_if_needed(port: str, slave_id: int = 1, count: int = 4) -> DaemonClient:
    """如果需要，启动守护进程"""
    client = DaemonClient(port)
    
    if not client.is_daemon_running():
        # 启动守护进程
        import subprocess
        import time
        
        # 启动守护进程
        proc = subprocess.Popen([
            sys.executable, "-c",
            f"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / 'src'))
from daemon import USBRelayDaemon
daemon = USBRelayDaemon('{port}', {slave_id}, {count})
daemon.start()
"""
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        # 等待守护进程启动
        for _ in range(10):  # 最多等待5秒
            if client.is_daemon_running():
                break
            time.sleep(0.5)
        else:
            raise Exception("守护进程启动超时")
    
    return client


if __name__ == "__main__":
    import sys
    if len(sys.argv) >= 2:
        port = sys.argv[1]
        slave_id = int(sys.argv[2]) if len(sys.argv) >= 3 else 1
        count = int(sys.argv[3]) if len(sys.argv) >= 4 else 4
        
        daemon = USBRelayDaemon(port, slave_id, count)
        
        # 设置信号处理
        def signal_handler(sig, frame):
            daemon.stop()
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        daemon.start()
