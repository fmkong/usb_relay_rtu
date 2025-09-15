"""
命令行接口模块

提供用户友好的命令行界面，包括：
- 继电器控制命令
- 数字量输入读取命令
- 设备管理命令
- 系统监控命令
"""

import click
import sys
import time
from typing import List, Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Confirm

try:
    from .device_controller import USBRelayController, DeviceManager, RelaySequence
    from .modbus_rtu import ModbusRTUException
    from .daemon import DaemonClient, start_daemon_if_needed
except ImportError:
    from device_controller import USBRelayController, DeviceManager, RelaySequence
    from modbus_rtu import ModbusRTUException
    from daemon import DaemonClient, start_daemon_if_needed


console = Console()


def handle_exceptions(func):
    """异常处理装饰器"""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ModbusRTUException as e:
            console.print(f"[red]通信错误: {e}[/red]")
            sys.exit(1)
        except Exception as e:
            console.print(f"[red]未知错误: {e}[/red]")
            sys.exit(1)
    return wrapper


@click.group()
@click.version_option(version="1.0.0", prog_name="USB继电器RTU控制软件")
def cli():
    """USB继电器RTU控制软件
    
    基于Modbus RTU协议的跨平台USB继电器控制工具。
    支持继电器控制、数字量输入读取和设备管理。
    """
    pass


@cli.group()
def device():
    """设备管理命令"""
    pass


@device.command("list")
def list_devices():
    """列出所有串口设备"""
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True,
    ) as progress:
        task = progress.add_task("正在扫描串口设备...", total=None)
        devices = DeviceManager.list_serial_ports()
        progress.update(task, completed=True)
    
    if not devices:
        console.print("[yellow]未找到任何串口设备[/yellow]")
        return
    
    table = Table(title="可用串口设备")
    table.add_column("端口", style="cyan", no_wrap=True)
    table.add_column("描述", style="magenta")
    table.add_column("制造商", style="green")
    table.add_column("VID:PID", style="yellow")
    table.add_column("序列号", style="blue")
    
    for device in devices:
        table.add_row(
            device.port,
            device.description,
            device.manufacturer,
            f"{device.vendor_id}:{device.product_id}",
            device.serial_number
        )
    
    console.print(table)


@device.command("usb")
def list_usb_devices():
    """列出USB转串口设备"""
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True,
    ) as progress:
        task = progress.add_task("正在扫描USB串口设备...", total=None)
        devices = DeviceManager.find_usb_serial_devices()
        progress.update(task, completed=True)
    
    if not devices:
        console.print("[yellow]未找到任何USB串口设备[/yellow]")
        return
    
    table = Table(title="可用USB串口设备")
    table.add_column("端口", style="cyan", no_wrap=True)
    table.add_column("描述", style="magenta")
    table.add_column("制造商", style="green")
    table.add_column("VID:PID", style="yellow")
    
    for device in devices:
        table.add_row(
            device.port,
            device.description,
            device.manufacturer,
            f"{device.vendor_id}:{device.product_id}"
        )
    
    console.print(table)


@device.command("auto-detect")
def auto_detect():
    """自动检测继电器设备"""
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True,
    ) as progress:
        task = progress.add_task("正在自动检测继电器设备...", total=None)
        device_port = DeviceManager.auto_detect_relay_device()
        progress.update(task, completed=True)
    
    if device_port:
        console.print(f"[green]✓ 检测到继电器设备: {device_port}[/green]")
    else:
        console.print("[red]✗ 未检测到继电器设备[/red]")


@device.command("info")
@click.option("--port", "-p", required=True, help="设备端口路径")
@click.option("--slave-id", "-s", default=1, help="从设备地址")
@handle_exceptions
def device_info(port: str, slave_id: int):
    """获取设备信息"""
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True,
    ) as progress:
        task = progress.add_task("正在连接设备...", total=None)
        
        with USBRelayController(port, slave_id) as controller:
            progress.update(task, description="正在读取设备信息...")
            
            # 测试连接
            is_connected = controller.test_connection()
            progress.update(task, completed=True)
    
    # 显示设备信息
    info_panel = Panel.fit(
        f"""
[cyan]设备端口:[/cyan] {port}
[cyan]从设备地址:[/cyan] {slave_id}
[cyan]连接状态:[/cyan] {'[green]已连接[/green]' if is_connected else '[red]连接失败[/red]'}
[cyan]波特率:[/cyan] 9600
[cyan]数据位:[/cyan] 8
[cyan]停止位:[/cyan] 1
[cyan]校验位:[/cyan] 无
        """.strip(),
        title="设备信息",
        border_style="blue"
    )
    
    console.print(info_panel)


@cli.group()
def relay():
    """继电器控制命令"""
    pass


@relay.command("status")
@click.option("--port", "-p", required=True, help="设备端口路径")
@click.option("--slave-id", "-s", default=1, help="从设备地址")
@click.option("--relay", "-r", type=int, help="继电器编号（1-8），不指定则显示所有")
@click.option("--count", "-c", default=8, help="最大继电器数量")
@handle_exceptions
def relay_status(port: str, slave_id: int, relay: Optional[int], count: int):
    """查看继电器状态"""
    with USBRelayController(port, slave_id) as controller:
        if relay is not None:
            # 显示单个继电器状态
            state = controller.get_relay_state(relay)
            status_color = "green" if state.state else "red"
            status_text = "开启" if state.state else "关闭"
            console.print(f"继电器 {relay}: [{status_color}]{status_text}[/{status_color}]")
        else:
            # 显示所有继电器状态
            states = controller.get_all_relay_states(count)
            
            table = Table(title="继电器状态")
            table.add_column("继电器", justify="center", style="cyan")
            table.add_column("状态", justify="center")
            table.add_column("地址", justify="center", style="yellow")
            
            for state in states:
                status_color = "green" if state.state else "red"
                status_text = "开启" if state.state else "关闭"
                table.add_row(
                    str(state.relay_id),
                    f"[{status_color}]{status_text}[/{status_color}]",
                    f"0x{state.address:04X}"
                )
            
            console.print(table)


@relay.command("on")
@click.option("--port", "-p", required=True, help="设备端口路径")
@click.option("--slave-id", "-s", default=1, help="从设备地址")
@click.option("--relay", "-r", required=True, type=int, help="继电器编号（1-8）")
@handle_exceptions
def relay_on(port: str, slave_id: int, relay: int):
    """打开继电器"""
    from daemon import execute_relay_command_smart
    
    success = execute_relay_command_smart(port, slave_id, relay, "on")
    
    if success:
        console.print(f"[green]✓ 继电器 {relay} 已打开[/green]")
    else:
        console.print(f"[red]✗ 继电器 {relay} 打开失败[/red]")


@relay.command("off")
@click.option("--port", "-p", required=True, help="设备端口路径")
@click.option("--slave-id", "-s", default=1, help="从设备地址")
@click.option("--relay", "-r", required=True, type=int, help="继电器编号（1-8）")
@handle_exceptions
def relay_off(port: str, slave_id: int, relay: int):
    """关闭继电器"""
    from daemon import execute_relay_command_smart
    
    success = execute_relay_command_smart(port, slave_id, relay, "off")
    
    if success:
        console.print(f"[green]✓ 继电器 {relay} 已关闭[/green]")
    else:
        console.print(f"[red]✗ 继电器 {relay} 关闭失败[/red]")


@relay.command("toggle")
@click.option("--port", "-p", required=True, help="设备端口路径")
@click.option("--slave-id", "-s", default=1, help="从设备地址")
@click.option("--relay", "-r", required=True, type=int, help="继电器编号（1-8）")
@handle_exceptions
def relay_toggle(port: str, slave_id: int, relay: int):
    """切换继电器状态"""
    from daemon import DaemonClient, get_status_smart, execute_relay_command_smart
    
    # 先获取当前状态
    try:
        status_result = get_status_smart(port, slave_id, 8)
        if status_result.get("success"):
            relay_states = status_result.get("relay_states", [])
            if relay <= len(relay_states):
                current_state = relay_states[relay - 1]  # relay从1开始，数组从0开始
                current_text = "开启" if current_state else "关闭"
                target_text = "关闭" if current_state else "开启"
            else:
                current_text = "未知"
                target_text = "切换"
        else:
            current_text = "未知"
            target_text = "切换"
    except Exception:
        current_text = "未知"
        target_text = "切换"
    
    # 执行toggle操作
    success = execute_relay_command_smart(port, slave_id, relay, "toggle")
    
    if success:
        if current_text != "未知":
            console.print(f"[green]✓ 继电器 {relay} 已从 {current_text} 切换为 {target_text}[/green]")
        else:
            console.print(f"[green]✓ 继电器 {relay} 状态已切换[/green]")
    else:
        console.print(f"[red]✗ 继电器 {relay} 切换失败[/red]")


@relay.command("all-on")
@click.option("--port", "-p", required=True, help="设备端口路径")
@click.option("--slave-id", "-s", default=1, help="从设备地址")
@click.option("--count", "-c", default=8, help="继电器数量")
@handle_exceptions
def relay_all_on(port: str, slave_id: int, count: int):
    """打开所有继电器"""
    if not Confirm.ask(f"确定要打开所有 {count} 个继电器吗？"):
        console.print("[yellow]操作已取消[/yellow]")
        return
    
    with USBRelayController(port, slave_id) as controller:
        success = controller.turn_on_all_relays(count)
        
        if success:
            console.print(f"[green]✓ 所有继电器已打开[/green]")
        else:
            console.print(f"[red]✗ 批量打开继电器失败[/red]")


@relay.command("all-off")
@click.option("--port", "-p", required=True, help="设备端口路径")
@click.option("--slave-id", "-s", default=1, help="从设备地址")
@click.option("--count", "-c", default=8, help="继电器数量")
@handle_exceptions
def relay_all_off(port: str, slave_id: int, count: int):
    """关闭所有继电器"""
    with USBRelayController(port, slave_id) as controller:
        success = controller.turn_off_all_relays(count)
        
        if success:
            console.print(f"[green]✓ 所有继电器已关闭[/green]")
        else:
            console.print(f"[red]✗ 批量关闭继电器失败[/red]")


@relay.command("pulse")
@click.option("--port", "-p", required=True, help="设备端口路径")
@click.option("--slave-id", "-s", default=1, help="从设备地址")
@click.option("--relay", "-r", required=True, type=int, help="继电器编号（1-8）")
@click.option("--duration", "-d", default=1.0, type=float, help="脉冲持续时间（秒）")
@handle_exceptions
def relay_pulse(port: str, slave_id: int, relay: int, duration: float):
    """继电器脉冲控制"""
    with USBRelayController(port, slave_id) as controller:
        sequence = RelaySequence(controller)
        
        console.print(f"[cyan]执行继电器 {relay} 脉冲控制，持续 {duration} 秒...[/cyan]")
        
        success = sequence.pulse_relay(relay, duration)
        
        if success:
            console.print(f"[green]✓ 继电器 {relay} 脉冲控制完成[/green]")
        else:
            console.print(f"[red]✗ 继电器 {relay} 脉冲控制失败[/red]")


@relay.command("running-lights")
@click.option("--port", "-p", required=True, help="设备端口路径")
@click.option("--slave-id", "-s", default=1, help="从设备地址")
@click.option("--count", "-c", default=4, help="继电器数量")
@click.option("--delay", "-d", default=0.5, type=float, help="每步延时（秒）")
@click.option("--cycles", default=3, help="循环次数")
@handle_exceptions
def running_lights(port: str, slave_id: int, count: int, delay: float, cycles: int):
    """流水灯效果"""
    with USBRelayController(port, slave_id) as controller:
        sequence = RelaySequence(controller)
        
        console.print(f"[cyan]执行流水灯效果，{count} 个继电器，{cycles} 个循环...[/cyan]")
        
        success = sequence.running_lights(count, delay, cycles)
        
        if success:
            console.print(f"[green]✓ 流水灯效果执行完成[/green]")
        else:
            console.print(f"[red]✗ 流水灯效果执行失败[/red]")


@cli.group()
def input():
    """数字量输入命令"""
    pass


@input.command("status")
@click.option("--port", "-p", required=True, help="设备端口路径")
@click.option("--slave-id", "-s", default=1, help="从设备地址")
@click.option("--input", "-i", type=int, help="输入编号（1-8），不指定则显示所有")
@click.option("--count", "-c", default=8, help="最大输入数量")
@handle_exceptions
def input_status(port: str, slave_id: int, input: Optional[int], count: int):
    """查看数字量输入状态"""
    with USBRelayController(port, slave_id) as controller:
        if input is not None:
            # 显示单个输入状态
            state = controller.get_input_state(input)
            status_color = "green" if state.state else "red"
            status_text = "高电平" if state.state else "低电平"
            console.print(f"输入 {input}: [{status_color}]{status_text}[/{status_color}]")
        else:
            # 显示所有输入状态
            states = controller.get_all_input_states(count)
            
            table = Table(title="数字量输入状态")
            table.add_column("输入", justify="center", style="cyan")
            table.add_column("状态", justify="center")
            table.add_column("地址", justify="center", style="yellow")
            
            for state in states:
                status_color = "green" if state.state else "red"
                status_text = "高电平" if state.state else "低电平"
                table.add_row(
                    str(state.input_id),
                    f"[{status_color}]{status_text}[/{status_color}]",
                    f"0x{state.address:04X}"
                )
            
            console.print(table)


@input.command("monitor")
@click.option("--port", "-p", required=True, help="设备端口路径")
@click.option("--slave-id", "-s", default=1, help="从设备地址")
@click.option("--input", "-i", type=int, help="输入编号（1-4），不指定则监控所有")
@click.option("--count", "-c", default=4, help="输入数量（默认4路）")
@click.option("--interval", default=0.5, type=float, help="监控间隔（秒）")
@click.option("--interactive", "-I", is_flag=True, help="交互式模式，可通过键盘控制继电器")
@handle_exceptions
def input_monitor(port: str, slave_id: int, input: Optional[int], count: int, interval: float, interactive: bool):
    """实时监控数字量输入状态"""
    console.print("[cyan]启动守护进程监控模式...[/cyan]")
    console.print(f"[yellow]设备: {port} | 从地址: {slave_id} | 路数: {count}[/yellow]")
    console.print()
    
    # 启动完整的守护进程（包含通信同步机制）
    from daemon import USBRelayDaemon, DaemonClient
    import signal
    import threading
    
    daemon = USBRelayDaemon(port, slave_id, count)
    
    def signal_handler(sig, frame):
        print()  # 换行清理当前行
        daemon.stop()
        console.print("[green]✓ 监控守护进程已停止[/green]")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # 在后台线程启动完整的守护进程
        daemon_thread = threading.Thread(target=daemon.start, daemon=True)
        daemon_thread.start()
        
        # 等待守护进程启动
        time.sleep(2)
        
        # 创建客户端来获取状态
        client = DaemonClient(port)
        
        console.print("[green]✓ 守护进程已启动，现在可以在其他终端使用控制命令[/green]")
        console.print("[cyan]在新终端中使用以下命令控制继电器:[/cyan]")
        console.print(f"[dim]  python run.py relay toggle -p {port} -r 1[/dim]")
        console.print(f"[dim]  python run.py relay on -p {port} -r 2[/dim]")
        console.print(f"[dim]  python run.py relay status -p {port}[/dim]")
        console.print()
        
        # 主监控循环
        while daemon.running:
            current_time = time.strftime("%H:%M:%S")
            
            try:
                # 通过客户端获取状态
                status = client.get_status()
                
                if status.get("success"):
                    relay_states = status.get("relay_states", [False] * count)
                    input_states = status.get("input_states", [False] * count)
                    
                    # 构建状态显示
                    relay_status = []
                    for i in range(count):
                        state = "●" if (i < len(relay_states) and relay_states[i]) else "○"
                        relay_status.append(f"R{i+1}{state}")
                    
                    input_status = []
                    for i in range(count):
                        state = "●" if (i < len(input_states) and input_states[i]) else "○"
                        input_status.append(f"I{i+1}{state}")
                    
                    # 简洁的状态显示
                    print(f"\r[{current_time}] 继电器: {' '.join(relay_status)} | 输入: {' '.join(input_status)}", end="", flush=True)
                else:
                    print(f"\r[{current_time}] 状态获取失败: {status.get('error', '未知错误')}", end="", flush=True)
                    
            except Exception as e:
                print(f"\r[{current_time}] 通信错误: {e}", end="", flush=True)
            
            time.sleep(interval)
    
    except Exception as e:
        # 先换行，再输出错误信息
        print()  # 换行
        console.print(f"[red]监控启动失败: {e}[/red]")
        daemon.stop()


@cli.command("daemon")
@click.option("--port", "-p", required=True, help="设备端口路径")
@click.option("--slave-id", "-s", default=1, help="从设备地址")
@click.option("--count", "-c", default=4, help="继电器/输入数量")
@handle_exceptions
def start_daemon(port: str, slave_id: int, count: int):
    """启动守护进程模式"""
    from daemon import USBRelayDaemon
    import signal
    
    daemon = USBRelayDaemon(port, slave_id, count)
    
    def signal_handler(sig, frame):
        daemon.stop()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    daemon.start()


@cli.command("test")
@click.option("--port", "-p", required=True, help="设备端口路径")
@click.option("--slave-id", "-s", default=1, help="从设备地址")
@handle_exceptions
def test_device(port: str, slave_id: int):
    """测试设备功能"""
    console.print("[cyan]开始设备功能测试...[/cyan]")
    
    # 检查是否有守护进程运行
    daemon_client = DaemonClient(port)
    if daemon_client.is_daemon_running():
        console.print("[yellow]检测到守护进程正在运行，将通过守护进程进行测试[/yellow]")
        
        # 通过守护进程测试
        try:
            # 测试状态获取
            status = daemon_client.get_status()
            if status.get("success"):
                console.print("[green]   ✓ 守护进程通信正常[/green]")
            
            # 测试继电器控制
            console.print("测试继电器控制...")
            success1 = daemon_client.set_relay(1, True)
            time.sleep(0.5)
            success2 = daemon_client.set_relay(1, False)
            
            if success1 and success2:
                console.print("[green]   ✓ 继电器控制正常[/green]")
            else:
                console.print("[red]   ✗ 继电器控制异常[/red]")
                
            console.print("[green]守护进程模式测试完成[/green]")
            
        except Exception as e:
            console.print(f"[red]守护进程测试失败: {e}[/red]")
    
    else:
        # 直接模式测试
        with USBRelayController(port, slave_id) as controller:
            # 测试连接
            console.print("1. 测试设备连接...")
            if controller.test_connection():
                console.print("[green]   ✓ 设备连接正常[/green]")
            else:
                console.print("[red]   ✗ 设备连接失败[/red]")
                return
            
            # 测试继电器控制
            console.print("2. 测试继电器控制...")
            try:
                # 测试单个继电器
                controller.turn_on_relay(1)
                time.sleep(0.5)
                state1 = controller.get_relay_state(1)
                
                controller.turn_off_relay(1)
                time.sleep(0.5)
                state2 = controller.get_relay_state(1)
                
                if state1.state and not state2.state:
                    console.print("[green]   ✓ 继电器控制正常[/green]")
                else:
                    console.print("[red]   ✗ 继电器控制异常[/red]")
            except Exception as e:
                console.print(f"[red]   ✗ 继电器测试失败: {e}[/red]")
            
            # 测试数字量输入
            console.print("3. 测试数字量输入...")
            try:
                inputs = controller.get_all_input_states(4)
                console.print(f"[green]   ✓ 成功读取 {len(inputs)} 个输入状态[/green]")
            except Exception as e:
                console.print(f"[red]   ✗ 数字量输入测试失败: {e}[/red]")
            
            console.print("[green]设备功能测试完成[/green]")


if __name__ == "__main__":
    cli()
