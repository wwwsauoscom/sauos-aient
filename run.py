#!/usr/bin/env python3
"""
SAUOS AI 自动化模式
交互式命令行界面，使用AI控制电脑
"""

import sys
import os
import time
import logging

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sauos import Automation, Screen
from sauos.ai.llm import OllamaClient, Message


# Ollama 配置
OLLAMA_URL = "http://10.10.0.20:11434"
TEXT_MODEL = "qwen3:8b"
VISION_MODEL = "moondream:1.8b"


SYSTEM_PROMPT = """你是SAUOS电脑自动化助手。用户会给你一个任务，你需要根据屏幕截图分析当前状态，然后返回要执行的操作。

你必须严格按照以下JSON格式返回，不要返回其他内容：

{"action":"click","x":100,"y":200,"reason":"点击搜索按钮"}
{"action":"type","text":"hello world","reason":"输入搜索内容"}
{"action":"hotkey","keys":["command","space"],"reason":"打开Spotlight"}
{"action":"scroll","direction":"down","reason":"向下滚动"}
{"action":"wait","duration":2,"reason":"等待页面加载"}
{"action":"done","reason":"任务已完成"}

规则：
1. 每次只返回一个JSON操作
2. 坐标基于屏幕截图的像素位置
3. macOS系统，用command代替ctrl
4. 如果任务完成，返回done
5. 不要用markdown包裹，直接返回JSON
/no_think"""


class AIAutomation:
    """AI自动化控制器"""
    
    def __init__(self):
        self.auto = Automation()
        self.screen = Screen()
        
        # 文本模型用于决策
        self.text_llm = OllamaClient(base_url=OLLAMA_URL, model=TEXT_MODEL)
        # 视觉模型用于屏幕分析
        self.vision_llm = OllamaClient(base_url=OLLAMA_URL, model=VISION_MODEL)
        
        self.running = False
        self.step_count = 0
    
    def analyze_screen(self):
        """用视觉模型分析屏幕"""
        screenshot = self.screen.capture_primary()
        messages = [Message("user", "Please describe this screenshot in detail in Chinese. Focus on: what application is open, what buttons/inputs are visible, and their approximate positions on screen.")]
        response = self.vision_llm.chat_with_vision(messages, [screenshot])
        return response.content, screenshot
    
    def plan_action(self, task, screen_desc, history=""):
        """用文本模型规划操作"""
        prompt = f"""当前屏幕状态：
{screen_desc}

用户任务：{task}

{f"已执行的操作：{history}" if history else ""}

请返回下一步操作的JSON："""
        
        messages = [
            Message("system", SYSTEM_PROMPT),
            Message("user", prompt)
        ]
        response = self.text_llm.chat(messages, temperature=0.3)
        return response.content
    
    def execute_action(self, action_json):
        """执行操作"""
        import json
        
        # 解析JSON
        content = action_json.strip()
        # 清理可能的markdown包裹
        if "```" in content:
            content = content.split("```")[1] if "```json" not in content else content.split("```json")[1]
            content = content.split("```")[0]
        
        # 找到第一个{到最后一个}
        start = content.find("{")
        end = content.rfind("}") + 1
        if start == -1 or end == 0:
            return False, "无法解析操作指令"
        
        try:
            action = json.loads(content[start:end])
        except json.JSONDecodeError as e:
            return False, f"JSON解析错误: {e}"
        
        action_type = action.get("action", "")
        reason = action.get("reason", "")
        
        if action_type == "done":
            return True, f"任务完成: {reason}"
        
        elif action_type == "click":
            x, y = action.get("x", 0), action.get("y", 0)
            self.auto.click((x, y))
            return False, f"点击 ({x}, {y}) - {reason}"
        
        elif action_type == "type":
            text = action.get("text", "")
            self.auto.keyboard.write(text)
            return False, f"输入 '{text}' - {reason}"
        
        elif action_type == "hotkey":
            keys = action.get("keys", [])
            self.auto.hotkey(*keys)
            return False, f"快捷键 {'+'.join(keys)} - {reason}"
        
        elif action_type == "scroll":
            direction = action.get("direction", "down")
            if direction == "up":
                self.auto.scroll_up(5)
            else:
                self.auto.scroll_down(5)
            return False, f"滚动 {direction} - {reason}"
        
        elif action_type == "wait":
            duration = action.get("duration", 1)
            time.sleep(duration)
            return False, f"等待 {duration}秒 - {reason}"
        
        else:
            return False, f"未知操作: {action_type}"
    
    def run_task(self, task, max_steps=20):
        """执行任务"""
        self.running = True
        self.step_count = 0
        history = []
        
        print(f"\n{'='*50}")
        print(f"  任务: {task}")
        print(f"{'='*50}\n")
        
        for step in range(max_steps):
            if not self.running:
                print("\n[已取消]")
                break
            
            self.step_count = step + 1
            print(f"--- Step {self.step_count} ---")
            
            # 1. 分析屏幕
            print("  [分析屏幕...]")
            screen_desc, _ = self.analyze_screen()
            print(f"  [屏幕] {screen_desc[:100]}...")
            
            # 2. 规划操作
            print("  [规划操作...]")
            history_str = "\n".join(history[-5:])  # 只保留最近5条
            action_json = self.plan_action(task, screen_desc, history_str)
            print(f"  [指令] {action_json.strip()[:120]}")
            
            # 3. 执行
            done, msg = self.execute_action(action_json)
            print(f"  [执行] {msg}")
            history.append(f"Step{self.step_count}: {msg}")
            
            if done:
                print(f"\n{'='*50}")
                print(f"  任务完成! 共 {self.step_count} 步")
                print(f"{'='*50}\n")
                self.running = False
                return True
            
            # 等待UI响应
            time.sleep(1)
        
        print(f"\n[达到最大步数 {max_steps}]")
        self.running = False
        return False


def interactive_mode():
    """交互式模式"""
    print("""
╔══════════════════════════════════════════════╗
║       SAUOS - AI 电脑全自动化系统            ║
║  连接: {:<37s} ║
║  文本模型: {:<34s} ║
║  视觉模型: {:<34s} ║
╚══════════════════════════════════════════════╝
""".format(OLLAMA_URL, TEXT_MODEL, VISION_MODEL[:34]))
    
    print("命令:")
    print("  输入任务描述 → AI自动执行")
    print("  screenshot   → 截图并分析屏幕")
    print("  mouse        → 显示鼠标位置")
    print("  window       → 显示活动窗口")
    print("  quit/exit    → 退出\n")
    
    ai = AIAutomation()
    
    while True:
        try:
            cmd = input("SAUOS> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n退出")
            break
        
        if not cmd:
            continue
        
        if cmd.lower() in ("quit", "exit", "q"):
            print("退出")
            break
        
        elif cmd.lower() == "screenshot":
            print("正在分析屏幕...")
            desc, img = ai.analyze_screen()
            img.save("/tmp/sauos_screen.png")
            print(f"截图已保存: /tmp/sauos_screen.png")
            print(f"分析结果:\n{desc}\n")
        
        elif cmd.lower() == "mouse":
            x, y = ai.auto.mouse.position
            print(f"鼠标位置: ({x}, {y})\n")
        
        elif cmd.lower() == "window":
            win = ai.auto.get_active_window()
            if win:
                print(f"应用: {win.app_name}")
                print(f"标题: {win.title}")
                print(f"位置: ({win.x}, {win.y}) 大小: {win.width}x{win.height}\n")
            else:
                print("无法获取窗口信息\n")
        
        else:
            # 执行AI任务
            ai.run_task(cmd)


if __name__ == "__main__":
    interactive_mode()
