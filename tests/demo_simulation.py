#!/usr/bin/env python3
"""
USB继电器RTU控制软件功能演示

模拟继电器控制功能演示，不需要实际硬件连接
"""

import sys
import time
from pathlib import Path

# 添加src目录到路径
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from modbus_rtu import ModbusCRC16
from device_controller import DeviceManager
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
import random

console = Console()

def demo_device_detection():
    """演示设备检测功能"""
    console.print("\n[cyan]🔍 设备检测功能演示[/cyan]")
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True,
    ) as progress:
        task = progress.add_task("正在扫描USB串口设备...", total=None)
        time.sleep(1)  # 模拟扫描时间
        
        devices = DeviceManager.find_usb_serial_devices()
        progress.update(task, completed=True)
    
    if devices:
        table = Table(title="检测到的USB串口设备")
        table.add_column("端口", style="cyan", no_wrap=True)
        table.add_column("描述", style="magenta")
        table.add_column("VID:PID", style="yellow")
        
        for device in devices:
            table.add_row(
                device.port,
                device.description,
                f"{device.vendor_id}:{device.product_id}"
            )
        
        console.print(table)
        return devices[0].port  # 返回第一个设备用于后续演示
    else:
        console.print("[yellow]未找到USB串口设备[/yellow]")
        return "/dev/ttyUSB0"  # 使用默认设备

def demo_crc16_calculation():
    """演示CRC16计算功能"""
    console.print("\n[cyan]🔧 Modbus CRC16计算演示[/cyan]")
    
    # 使用协议手册中的示例数据
    test_data = bytes([0x01, 0x01, 0x00, 0x13, 0x00, 0x25])
    
    console.print(f"输入数据: {' '.join(f'{b:02X}' for b in test_data)}")
    
    crc_lo, crc_hi = ModbusCRC16.calculate(test_data)
    console.print(f"计算CRC: {crc_hi:02X}{crc_lo:02X}")
    
    # 构建完整帧
    complete_frame = test_data + bytes([crc_lo, crc_hi])
    console.print(f"完整帧: {' '.join(f'{b:02X}' for b in complete_frame)}")
    
    # 验证CRC
    is_valid = ModbusCRC16.verify(complete_frame)
    console.print(f"CRC验证: {'[green]✓ 通过[/green]' if is_valid else '[red]✗ 失败[/red]'}")

def demo_relay_control_simulation(port: str):
    """演示继电器控制功能（模拟）"""
    console.print(f"\n[cyan]⚡ 继电器控制演示 (模拟设备: {port})[/cyan]")
    
    # 模拟继电器状态
    relay_states = [False] * 8  # 8个继电器，初始状态都是关闭
    
    def show_relay_status():
        table = Table(title="继电器状态")
        table.add_column("继电器", justify="center", style="cyan")
        table.add_column("状态", justify="center")
        table.add_column("地址", justify="center", style="yellow")
        
        for i in range(8):
            relay_id = i + 1
            state = relay_states[i]
            status_color = "green" if state else "red"
            status_text = "开启" if state else "关闭"
            address = f"0x{i:04X}"
            
            table.add_row(
                str(relay_id),
                f"[{status_color}]{status_text}[/{status_color}]",
                address
            )
        
        console.print(table)
    
    # 初始状态
    console.print("[dim]初始状态：[/dim]")
    show_relay_status()
    
    # 模拟操作序列
    operations = [
        ("打开继电器1", lambda: setattr(relay_states, '__setitem__', relay_states.__setitem__(0, True))),
        ("打开继电器3", lambda: setattr(relay_states, '__setitem__', relay_states.__setitem__(2, True))),
        ("打开继电器5", lambda: setattr(relay_states, '__setitem__', relay_states.__setitem__(4, True))),
        ("关闭继电器1", lambda: setattr(relay_states, '__setitem__', relay_states.__setitem__(0, False))),
        ("切换继电器3", lambda: setattr(relay_states, '__setitem__', relay_states.__setitem__(2, not relay_states[2]))),
    ]
    
    # 简化操作
    operations = [
        ("打开继电器1", 0, True),
        ("打开继电器3", 2, True),
        ("打开继电器5", 4, True),
        ("关闭继电器1", 0, False),
        ("切换继电器3", 2, None),  # None表示切换
    ]
    
    for op_name, relay_idx, new_state in operations:
        console.print(f"\n[cyan]执行操作: {op_name}[/cyan]")
        
        if new_state is None:  # 切换操作
            relay_states[relay_idx] = not relay_states[relay_idx]
        else:
            relay_states[relay_idx] = new_state
        
        time.sleep(0.5)  # 模拟操作延时
        show_relay_status()

def demo_running_lights_simulation():
    """演示流水灯效果（模拟）"""
    console.print(f"\n[cyan]💡 流水灯效果演示[/cyan]")
    
    relay_count = 4
    cycles = 2
    
    for cycle in range(cycles):
        console.print(f"\n[dim]循环 {cycle + 1}/{cycles}[/dim]")
        
        # 正向流水
        console.print("[yellow]正向流水:[/yellow]")
        for i in range(relay_count):
            states = ["⚫"] * relay_count
            states[i] = "[red]🔴[/red]"  # 当前亮起的继电器
            console.print(f"  继电器: {' '.join(states)}")
            time.sleep(0.3)
        
        # 反向流水
        console.print("[yellow]反向流水:[/yellow]")
        for i in range(relay_count - 1, -1, -1):
            states = ["⚫"] * relay_count
            states[i] = "[red]🔴[/red]"
            console.print(f"  继电器: {' '.join(states)}")
            time.sleep(0.3)
    
    console.print("[green]✓ 流水灯效果演示完成[/green]")

def demo_input_monitoring_simulation():
    """演示数字量输入监控（模拟）"""
    console.print(f"\n[cyan]📊 数字量输入监控演示[/cyan]")
    
    console.print("[yellow]模拟5秒输入监控，输入状态随机变化...[/yellow]")
    
    for i in range(5):
        # 模拟随机输入状态
        input_states = [random.choice([True, False]) for _ in range(4)]
        
        table = Table(title=f"数字量输入状态 - 第{i+1}秒")
        table.add_column("输入", justify="center", style="cyan")
        table.add_column("状态", justify="center")
        table.add_column("值", justify="center", style="yellow")
        
        for j, state in enumerate(input_states):
            input_id = j + 1
            status_color = "green" if state else "red"
            status_text = "高电平" if state else "低电平"
            value_text = "1" if state else "0"
            
            table.add_row(
                str(input_id),
                f"[{status_color}]{status_text}[/{status_color}]",
                value_text
            )
        
        console.print(table)
        time.sleep(1)

def main():
    """主演示函数"""
    console.print(Panel.fit(
        "[bold blue]USB继电器RTU控制软件功能演示[/bold blue]\n"
        "[dim]本演示展示软件的各项功能，无需实际硬件连接[/dim]",
        title="🚀 功能演示",
        border_style="blue"
    ))
    
    try:
        # 1. 设备检测演示
        detected_port = demo_device_detection()
        
        # 2. CRC16计算演示
        demo_crc16_calculation()
        
        # 3. 继电器控制演示
        demo_relay_control_simulation(detected_port)
        
        # 4. 流水灯效果演示
        demo_running_lights_simulation()
        
        # 5. 输入监控演示
        demo_input_monitoring_simulation()
        
        # 总结
        console.print(Panel.fit(
            "[green]✅ 所有功能演示完成！[/green]\n\n"
            "[cyan]软件功能包括：[/cyan]\n"
            "• 设备自动检测和管理\n"
            "• 标准Modbus RTU协议实现\n"
            "• 继电器状态控制和查询\n"
            "• 数字量输入实时监控\n"
            "• 高级序列控制（流水灯、脉冲等）\n"
            "• 美观的命令行界面\n\n"
            "[yellow]要连接真实设备，请确保：[/yellow]\n"
            "• 用户在dialout组中 (sudo usermod -a -G dialout $USER)\n"
            "• 设备正确连接并支持Modbus RTU协议\n"
            "• 使用正确的设备路径和通信参数",
            title="📋 演示总结",
            border_style="green"
        ))
        
    except KeyboardInterrupt:
        console.print("\n[yellow]演示被用户中断[/yellow]")

if __name__ == "__main__":
    main()
