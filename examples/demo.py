#!/usr/bin/env python3
"""
SAUOS 使用示例
演示各种自动化操作
"""

from sauos import Automation, TaskScheduler
from sauos.scheduler import WorkflowBuilder
from sauos.core.keyboard import Key


def example_basic_operations():
    """基础操作示例"""
    print("\n=== 基础操作示例 ===\n")
    
    auto = Automation()
    
    # 获取屏幕尺寸
    width, height = auto.get_screen_size()
    print(f"屏幕尺寸: {width}x{height}")
    
    # 截图
    screenshot = auto.screenshot()
    print(f"截图尺寸: {screenshot.size}")
    
    # 保存截图
    # auto.save_screenshot("screenshot.png")
    
    # 获取活动窗口
    window = auto.get_active_window()
    if window:
        print(f"活动窗口: {window.app_name} - {window.title}")


def example_mouse_operations():
    """鼠标操作示例"""
    print("\n=== 鼠标操作示例 ===\n")
    
    auto = Automation()
    
    # 获取当前鼠标位置
    x, y = auto.mouse.position
    print(f"当前鼠标位置: ({x}, {y})")
    
    # 移动鼠标（演示用，取消注释后生效）
    # auto.mouse.move(100, 100, duration=0.5)
    # auto.mouse.left_click()
    
    # 链式操作
    # auto.move_to((200, 200)).sleep(0.5).then_click()
    
    print("鼠标操作示例完成")


def example_keyboard_operations():
    """键盘操作示例"""
    print("\n=== 键盘操作示例 ===\n")
    
    auto = Automation()
    
    # 按键操作（演示用，取消注释后生效）
    # auto.press(Key.ESCAPE)
    # auto.hotkey("command", "space")  # macOS Spotlight
    # auto.type_text("hello world")
    
    print("键盘操作示例完成")


def example_image_matching():
    """图像匹配示例"""
    print("\n=== 图像匹配示例 ===\n")
    
    auto = Automation()
    
    # 在屏幕上查找图像
    # result = auto.find("button.png")
    # if result:
    #     print(f"找到目标: 位置({result.x}, {result.y}), 置信度: {result.confidence:.2f}")
    #     auto.click(result)  # 点击找到的位置
    
    # 等待目标出现
    # result = auto.wait_for("loading_complete.png", timeout=10)
    # if result:
    #     print("加载完成")
    
    print("图像匹配示例完成")


def example_workflow():
    """工作流示例"""
    print("\n=== 工作流示例 ===\n")
    
    # 使用工作流构建器
    workflow = WorkflowBuilder()
    
    # 构建工作流（演示，实际运行需要取消注释）
    # workflow.click((100, 100), "点击位置A") \
    #         .wait(0.5) \
    #         .type("Hello", "输入文本") \
    #         .hotkey("command", "a", name="全选") \
    #         .screenshot("result.png", "保存截图")
    
    # 执行工作流
    # workflow.run()
    # workflow.summary()
    
    print("工作流示例完成")


def example_task_scheduler():
    """任务调度器示例"""
    print("\n=== 任务调度器示例 ===\n")
    
    scheduler = TaskScheduler()
    
    # 添加任务
    scheduler.add("截图", lambda auto: auto.screenshot())
    scheduler.add("获取窗口信息", lambda auto: auto.get_active_window())
    scheduler.add("等待1秒", lambda auto: auto.sleep(1))
    
    # 带条件的任务
    # scheduler.add(
    #     "点击确认按钮",
    #     lambda auto: auto.click("confirm.png"),
    #     condition=lambda auto: auto.exists("confirm.png"),
    #     retry_count=3
    # )
    
    # 执行所有任务
    results = scheduler.run()
    
    # 打印摘要
    scheduler.print_summary()


def example_real_automation():
    """
    真实自动化场景示例
    
    示例：打开Safari搜索
    """
    print("\n=== 真实自动化场景示例 ===\n")
    
    auto = Automation()
    
    # 以下是一个完整的自动化流程示例（取消注释后运行）
    """
    # 1. 激活Safari
    auto.activate_app("Safari")
    auto.sleep(0.5)
    
    # 2. 打开新标签页
    auto.hotkey("command", "t")
    auto.sleep(0.3)
    
    # 3. 输入网址
    auto.write("https://www.google.com")
    auto.enter()
    auto.sleep(2)
    
    # 4. 在搜索框输入
    auto.click("search_box.png")  # 需要准备搜索框的截图
    auto.write("Python automation")
    auto.enter()
    
    # 5. 截图保存结果
    auto.sleep(2)
    auto.save_screenshot("search_result.png")
    """
    
    print("真实自动化场景示例完成（代码已注释，取消注释后运行）")


def main():
    """主函数"""
    print("="*60)
    print("SAUOS - 电脑全自动化系统 示例")
    print("="*60)
    
    example_basic_operations()
    example_mouse_operations()
    example_keyboard_operations()
    example_image_matching()
    example_workflow()
    example_task_scheduler()
    example_real_automation()
    
    print("\n" + "="*60)
    print("所有示例执行完成！")
    print("="*60)


if __name__ == "__main__":
    main()
