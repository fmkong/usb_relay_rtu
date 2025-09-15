"""
USB继电器RTU守护进程模块

实现守护进程模式，统一管理串口访问：
- 单一串口连接，避免多进程冲突
- 进程间通信协调控制命令
- 实时状态监控和命令分发
- 通信同步机制，确保Modbus RTU事务原子性
"""

import json
import socket
import threading
import time
import queue
from typing import Dict, Any, Optional, Callable
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
    """USB继电器守护进程"""
    
    def __init__(self, port: str, slave_id: int = 1, count: int = 4):
        self.port = port
        self.slave_id = slave_id
        self.count = count
        self.controller: Optional[USBRelayController] = None
        self.running = False
        self.clients = []
        
        # IPC socket路径
        self.socket_path = str(Path(tempfile.gettempdir()) / f"usb_relay_daemon_{port.replace('/', '_')}.sock")
        self.server_socket = None
        
        # 当前状态缓存
        self.relay_states = [False] * count
        self.input_states = [False] * count
        self.last_update = 0
        
        # 通信同步机制 - 核心改进
        self.comm_queue = queue.Queue()
        self.comm_lock = threading.RLock()  # 使用可重入锁
        self.comm_worker_thread = None
        
        # 状态更新控制
        self.state_update_enabled = True
        self.last_command_time = 0
        self.state_update_delay = 0.2  # 命令执行后延迟更新状态
        
        # 状态缓存锁
        self.state_lock = threading.Lock()
        
    def start(self):
        """启动守护进程"""
        try:
            # 连接设备
            self.controller = USBRelayController(self.port, self.slave_id)
            self.controller.connect()
            
            # 创建Unix socket
            if os.path.exists(self.socket_path):
                os.unlink(self.socket_path)
            
            self.server_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            self.server_socket.bind(self.socket_path)
            self.server_socket.listen(5)
            
            self.running = True
            
            # 启动通信工作线程 - 核心同步机制
            self.comm_worker_thread = threading.Thread(target=self._communication_worker, daemon=True)
            self.comm_worker_thread.start()
            
            # 启动状态更新线程
            threading.Thread(target=self._update_states, daemon=True).start()
            
            # 启动客户端处理线程
            threading.Thread(target=self._handle_clients, daemon=True).start()
            
            print(f"USB继电器守护进程已启动")
            print(f"设备: {self.port}")
            print(f"Socket: {self.socket_path}")
            print("✓ 通信同步机制已启用 - 解决串口冲突问题")
            print("按 Ctrl+C 停止")
            
            # 主循环
            while self.running:
                time.sleep(1)
                
        except Exception as e:
            print(f"守护进程启动失败: {e}")
            self.stop()
            
    def stop(self):
        """停止守护进程"""
        self.running = False
        
        if self.controller:
            self.controller.disconnect()
            
        if self.server_socket:
            self.server_socket.close()
            
        if os.path.exists(self.socket_path):
            os.unlink(self.socket_path)
            
        print("守护进程已停止")
    
    def _communication_worker(self):
        """通信工作线程 - 统一处理所有串口通信"""
        while self.running:
            try:
                # 从队列获取通信任务，带超时避免阻塞
                try:
                    task = self.comm_queue.get(timeout=0.1)
                except queue.Empty:
                    continue
                
                try:
                    # 使用通信锁确保Modbus RTU事务的原子性
                    with self.comm_lock:
                        # 执行通信任务
                        if callable(task['operation']):
                            result = task['operation']()
                        else:
                            result = None
                        
                        # 设置结果
                        task['result_queue'].put({
                            'success': True,
                            'result': result
                        })
                        
                        # 记录命令执行时间，智能暂停状态更新
                        self.last_command_time = time.time()
                        
                except Exception as e:
                    # 通信失败，返回错误
                    task['result_queue'].put({
                        'success': False,
                        'error': str(e)
                    })
                
                finally:
                    # 标记任务完成
                    self.comm_queue.task_done()
                    
            except Exception as e:
                if self.running:
                    print(f"\n通信工作线程错误: {e}")
    
    def _execute_command(self, operation: Callable, timeout: float = 2.0):
        """
        安全执行设备通信命令
        
        Args:
            operation: 要执行的操作函数
            timeout: 操作超时时间
            
        Returns:
            操作结果
        """
        result_queue = queue.Queue()
        task = {
            'operation': operation,
            'result_queue': result_queue
        }
        
        # 提交任务到通信队列
        self.comm_queue.put(task)
        
        try:
            # 等待结果
            result = result_queue.get(timeout=timeout)
            if result['success']:
                return result['result']
            else:
                raise Exception(result['error'])
        except queue.Empty:
            raise Exception("操作超时")
    
    def _update_states(self):
        """状态更新线程 - 智能避开命令执行时机"""
        while self.running:
            try:
                # 检查是否应该避开状态更新（刚执行完命令）
                if (self.last_command_time > 0 and 
                    time.time() - self.last_command_time < self.state_update_delay):
                    time.sleep(0.1)
                    continue
                
                # 使用通信队列机制安全读取状态
                def read_states():
                    # 读取继电器状态
                    relay_states = self.controller.get_all_relay_states(self.count)
                    relay_list = [s.state for s in relay_states]
                    
                    # 读取输入状态
                    input_states = self.controller.get_all_input_states(self.count)
                    input_list = [s.state for s in input_states]
                    
                    return relay_list, input_list
                
                # 安全执行状态读取
                relay_states, input_states = self._execute_command(read_states, timeout=1.0)
                
                # 更新缓存
                with self.state_lock:
                    self.relay_states = relay_states
                    self.input_states = input_states
                    self.last_update = time.time()
                
                time.sleep(0.5)  # 500ms更新间隔
                
            except Exception as e:
                if self.running:
                    print(f"\n状态更新错误: {e}")
                time.sleep(1)
    
    def _handle_clients(self):
        """客户端处理线程"""
        while self.running:
            try:
                client_socket, addr = self.server_socket.accept()
                threading.Thread(
                    target=self._handle_client,
                    args=(client_socket,),
                    daemon=True
                ).start()
            except Exception:
                if self.running:
                    continue
                break
    
    def _handle_client(self, client_socket):
        """处理单个客户端连接"""
        try:
            while self.running:
                data = client_socket.recv(1024)
                if not data:
                    break
                
                try:
                    request = json.loads(data.decode())
                    response = self._process_request(request)
                    client_socket.send(json.dumps(response).encode())
                except Exception as e:
                    error_response = {"success": False, "error": str(e)}
                    client_socket.send(json.dumps(error_response).encode())
                    
        except Exception:
            pass
        finally:
            client_socket.close()
    
    def _process_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """处理客户端请求 - 使用同步机制"""
        command = request.get("command")
        
        if command == "get_status":
            # 状态查询不需要通过通信队列，直接返回缓存
            with self.state_lock:
                return {
                    "success": True,
                    "relay_states": self.relay_states,
                    "input_states": self.input_states,
                    "last_update": self.last_update
                }
        
        elif command == "set_relay":
            relay_id = request.get("relay_id")
            state = request.get("state")
            
            try:
                # 定义控制操作
                def relay_operation():
                    if state is None:  # toggle
                        return self.controller.toggle_relay(relay_id)
                    else:
                        return self.controller.set_relay_state(relay_id, state)
                
                # 通过通信队列安全执行
                success = self._execute_command(relay_operation)
                return {"success": success}
                
            except Exception as e:
                return {"success": False, "error": str(e)}
        
        elif command == "pulse_relay":
            relay_id = request.get("relay_id")
            duration = request.get("duration", 1.0)
            
            try:
                # 定义脉冲操作
                def pulse_operation():
                    # 打开继电器
                    self.controller.turn_on_relay(relay_id)
                    time.sleep(duration)
                    # 关闭继电器
                    self.controller.turn_off_relay(relay_id)
                    return True
                
                # 通过通信队列安全执行
                self._execute_command(pulse_operation, timeout=duration + 2.0)
                return {"success": True}
                
            except Exception as e:
                return {"success": False, "error": str(e)}
        
        else:
            return {"success": False, "error": "未知命令"}


class DaemonClient:
    """守护进程客户端"""
    
    def __init__(self, port: str):
        self.port = port
        self.socket_path = str(Path(tempfile.gettempdir()) / f"usb_relay_daemon_{port.replace('/', '_')}.sock")
    
    def is_daemon_running(self) -> bool:
        """检查守护进程是否运行"""
        return os.path.exists(self.socket_path)
    
    def send_command(self, command: str, **kwargs) -> Dict[str, Any]:
        """发送命令到守护进程"""
        if not self.is_daemon_running():
            raise Exception("守护进程未运行")
        
        try:
            client_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            client_socket.connect(self.socket_path)
            
            request = {"command": command, **kwargs}
            client_socket.send(json.dumps(request).encode())
            
            response_data = client_socket.recv(1024)
            response = json.loads(response_data.decode())
            
            client_socket.close()
            return response
            
        except Exception as e:
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
