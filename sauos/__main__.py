#!/usr/bin/env python3
"""
SAUOS 命令行入口
"""

import sys
import argparse


def main():
    parser = argparse.ArgumentParser(
        prog="sauos",
        description="SAUOS - 电脑全自动化系统"
    )
    
    parser.add_argument(
        "--version", "-v",
        action="store_true",
        help="显示版本信息"
    )
    
    parser.add_argument(
        "--screenshot", "-s",
        metavar="FILE",
        help="截取屏幕并保存到指定文件"
    )
    
    parser.add_argument(
        "--info", "-i",
        action="store_true",
        help="显示系统信息"
    )
    
    parser.add_argument(
        "--mouse-pos", "-m",
        action="store_true",
        help="显示当前鼠标位置"
    )
    
    parser.add_argument(
        "--active-window", "-w",
        action="store_true",
        help="显示活动窗口信息"
    )
    
    parser.add_argument(
        "script",
        nargs="?",
        help="要执行的自动化脚本"
    )
    
    args = parser.parse_args()
    
    if args.version:
        from sauos import __version__
        print(f"SAUOS v{__version__}")
        return 0
    
    if args.info:
        show_system_info()
        return 0
    
    if args.screenshot:
        from sauos import Screen
        screen = Screen()
        screen.save_screenshot(args.screenshot)
        print(f"截图已保存: {args.screenshot}")
        return 0
    
    if args.mouse_pos:
        from sauos import Mouse
        mouse = Mouse()
        x, y = mouse.position
        print(f"鼠标位置: ({x}, {y})")
        return 0
    
    if args.active_window:
        from sauos import Window
        window = Window()
        info = window.get_active_window()
        if info:
            print(f"应用: {info.app_name}")
            print(f"标题: {info.title}")
            print(f"位置: ({info.x}, {info.y})")
            print(f"大小: {info.width}x{info.height}")
        else:
            print("无法获取活动窗口信息")
        return 0
    
    if args.script:
        # 执行脚本
        import runpy
        runpy.run_path(args.script, run_name="__main__")
        return 0
    
    # 默认显示帮助
    parser.print_help()
    return 0


def show_system_info():
    """显示系统信息"""
    import platform
    
    print("="*50)
    print("SAUOS 系统信息")
    print("="*50)
    
    print(f"操作系统: {platform.system()} {platform.release()}")
    print(f"Python版本: {platform.python_version()}")
    
    try:
        from sauos import Screen
        screen = Screen()
        monitors = screen.get_monitors()
        print(f"\n显示器数量: {len(monitors) - 1}")  # 第一个是全部显示器
        for i, mon in enumerate(monitors[1:], 1):
            print(f"  显示器 {i}: {mon['width']}x{mon['height']} @ ({mon['left']}, {mon['top']})")
    except Exception as e:
        print(f"\n无法获取显示器信息: {e}")
    
    print("="*50)


if __name__ == "__main__":
    sys.exit(main())
