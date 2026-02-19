#!/usr/bin/env python3
"""
AI 自动化示例
演示如何使用大模型控制电脑完成任务
"""

import os
import sys

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def example_basic_ai_agent():
    """基础AI Agent示例"""
    print("\n=== 基础AI Agent示例 ===\n")
    
    from sauos.ai.agent import AIAgentBuilder
    
    # 方式1: 使用OpenAI (需要设置OPENAI_API_KEY环境变量)
    # agent = AIAgentBuilder() \
    #     .with_openai(model="gpt-4o") \
    #     .max_steps(20) \
    #     .step_delay(1.0) \
    #     .save_screenshots(True) \
    #     .build()
    
    # 方式2: 使用Claude (需要设置ANTHROPIC_API_KEY环境变量)
    # agent = AIAgentBuilder() \
    #     .with_claude(model="claude-sonnet-4-20250514") \
    #     .build()
    
    # 方式3: 使用Ollama本地模型 (需要运行Ollama服务)
    # agent = AIAgentBuilder() \
    #     .with_ollama(model="llama3.2-vision") \
    #     .build()
    
    print("AI Agent构建器示例完成")
    print("取消注释上面的代码并配置API密钥后可运行")


def example_run_task():
    """运行AI任务示例"""
    print("\n=== AI任务执行示例 ===\n")
    
    # 以下代码需要配置API密钥后运行
    """
    from sauos.ai.agent import AIAgentBuilder
    
    # 创建Agent
    agent = AIAgentBuilder() \
        .with_openai() \
        .max_steps(30) \
        .save_screenshots(True, "./task_screenshots") \
        .build()
    
    # 执行任务
    result = agent.run("打开Safari浏览器，搜索Python教程")
    
    # 查看结果
    print(f"任务: {result.task}")
    print(f"成功: {result.success}")
    print(f"总耗时: {result.total_duration:.2f}秒")
    print(f"执行步数: {len(result.steps)}")
    print(f"结果: {result.final_message}")
    
    # 打印每步详情
    for step in result.steps:
        status = "✓" if step.success else "✗"
        print(f"  {status} Step {step.step}: {step.action.type.value} - {step.action.reason}")
    """
    
    print("任务执行示例代码已注释，配置API密钥后取消注释运行")


def example_smart_click():
    """智能点击示例"""
    print("\n=== 智能点击示例 ===\n")
    
    """
    from sauos.ai.agent import AIAgentBuilder
    
    agent = AIAgentBuilder().with_openai().build()
    
    # 智能点击 - AI会自动识别屏幕上的元素位置
    agent.click("搜索按钮")
    agent.click("关闭按钮")
    agent.click("Safari图标")
    
    # 带等待的点击
    agent.find_and_click("确认按钮", timeout=10)
    
    # 在输入框输入
    agent.type_at("搜索框", "Python automation")
    """
    
    print("智能点击示例代码已注释")


def example_screen_analysis():
    """屏幕分析示例"""
    print("\n=== 屏幕分析示例 ===\n")
    
    """
    from sauos.ai.agent import AIAgentBuilder
    
    agent = AIAgentBuilder().with_openai().build()
    
    # 分析当前屏幕
    analysis = agent.analyze_screen()
    
    print(f"屏幕描述: {analysis.description}")
    print(f"应用: {analysis.app_name}")
    print(f"窗口: {analysis.window_title}")
    print(f"发现 {len(analysis.elements)} 个UI元素:")
    
    for elem in analysis.elements[:5]:  # 只显示前5个
        print(f"  - {elem.name} ({elem.type}) @ ({elem.x}, {elem.y})")
    
    # 获取屏幕描述
    description = agent.describe_screen()
    print(f"\\n详细描述:\\n{description}")
    
    # 基于屏幕回答问题
    answer = agent.ask("当前打开的是什么应用？有哪些可点击的按钮？")
    print(f"\\n回答:\\n{answer}")
    """
    
    print("屏幕分析示例代码已注释")


def example_with_callback():
    """带回调的任务执行"""
    print("\n=== 带回调的任务执行示例 ===\n")
    
    """
    from sauos.ai.agent import AIAgentBuilder
    
    def on_step(step_num, action):
        print(f"[Step {step_num}] 执行: {action.type.value}")
        if action.reason:
            print(f"         原因: {action.reason}")
    
    def on_screenshot(step_num, screenshot):
        print(f"[Step {step_num}] 截图尺寸: {screenshot.size}")
    
    agent = AIAgentBuilder() \
        .with_openai() \
        .max_steps(20) \
        .build()
    
    # 设置回调
    agent.on_step = on_step
    agent.on_screenshot = on_screenshot
    
    # 执行任务
    result = agent.run("打开系统设置")
    """
    
    print("回调示例代码已注释")


def example_llm_direct():
    """直接使用LLM客户端"""
    print("\n=== 直接使用LLM客户端示例 ===\n")
    
    """
    from sauos.ai.llm import OpenAIClient, ClaudeClient, OllamaClient, Message
    from sauos import Screen
    
    # 创建客户端
    client = OpenAIClient()  # 或 ClaudeClient() 或 OllamaClient()
    
    # 普通对话
    messages = [
        Message("system", "你是一个有帮助的助手。"),
        Message("user", "用Python写一个Hello World程序")
    ]
    response = client.chat(messages)
    print(f"回答: {response.content}")
    
    # 带图像的对话
    screen = Screen()
    screenshot = screen.capture_primary()
    
    messages = [Message("user", "描述这张截图中的内容")]
    response = client.chat_with_vision(messages, [screenshot])
    print(f"图像描述: {response.content}")
    """
    
    print("LLM客户端示例代码已注释")


def example_vision_analyzer():
    """视觉分析器示例"""
    print("\n=== 视觉分析器示例 ===\n")
    
    """
    from sauos.ai.llm import OpenAIClient
    from sauos.ai.vision import VisionAnalyzer
    from sauos import Screen
    
    # 创建分析器
    client = OpenAIClient()
    analyzer = VisionAnalyzer(client)
    
    # 截取屏幕
    screen = Screen()
    screenshot = screen.capture_primary()
    
    # 分析屏幕
    analysis = analyzer.analyze_screen(screenshot)
    print(f"识别到 {len(analysis.elements)} 个元素")
    
    # 查找特定元素
    element = analyzer.find_element(screenshot, "关闭按钮")
    if element:
        print(f"找到元素: {element.name} @ {element.center}")
    
    # 获取点击位置
    position = analyzer.get_click_position(screenshot, "搜索框")
    if position:
        print(f"点击位置: {position}")
    """
    
    print("视觉分析器示例代码已注释")


def main():
    """主函数"""
    print("="*60)
    print("SAUOS - AI自动化示例")
    print("="*60)
    
    example_basic_ai_agent()
    example_run_task()
    example_smart_click()
    example_screen_analysis()
    example_with_callback()
    example_llm_direct()
    example_vision_analyzer()
    
    print("\n" + "="*60)
    print("所有示例展示完成！")
    print("配置API密钥后取消注释代码即可运行")
    print("="*60)
    
    # 打印配置说明
    print("\n配置说明:")
    print("-" * 40)
    print("OpenAI: 设置环境变量 OPENAI_API_KEY")
    print("Claude: 设置环境变量 ANTHROPIC_API_KEY")
    print("Ollama: 运行本地Ollama服务 (ollama serve)")
    print("-" * 40)


if __name__ == "__main__":
    main()
