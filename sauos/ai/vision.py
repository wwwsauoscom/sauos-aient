"""
视觉分析模块
使用大模型分析屏幕截图，识别UI元素
"""

import json
from typing import Optional, List, Dict, Any, Union, Tuple
from dataclasses import dataclass
from PIL import Image

from .llm import LLMClient, Message


@dataclass
class UIElement:
    """UI元素"""
    name: str
    type: str  # button, input, text, image, icon, etc.
    description: str
    x: int
    y: int
    width: int
    height: int
    clickable: bool = True
    text: Optional[str] = None
    
    @property
    def center(self) -> Tuple[int, int]:
        return (self.x + self.width // 2, self.y + self.height // 2)
    
    @property
    def bounds(self) -> Tuple[int, int, int, int]:
        return (self.x, self.y, self.width, self.height)


@dataclass
class ScreenAnalysis:
    """屏幕分析结果"""
    description: str
    elements: List[UIElement]
    app_name: Optional[str] = None
    window_title: Optional[str] = None
    suggested_actions: Optional[List[str]] = None


class VisionAnalyzer:
    """视觉分析器"""
    
    ANALYSIS_PROMPT = '''你是一个专业的UI分析助手。请仔细分析这张屏幕截图，识别所有可交互的UI元素。

请以JSON格式返回分析结果，格式如下：
{
    "description": "屏幕整体描述",
    "app_name": "应用名称（如果能识别）",
    "window_title": "窗口标题（如果能识别）",
    "elements": [
        {
            "name": "元素名称",
            "type": "元素类型(button/input/text/image/icon/link/menu/checkbox/dropdown等)",
            "description": "元素描述",
            "x": 左上角X坐标(整数),
            "y": 左上角Y坐标(整数),
            "width": 宽度(整数),
            "height": 高度(整数),
            "clickable": true或false,
            "text": "元素上的文字（如果有）"
        }
    ],
    "suggested_actions": ["可能的操作建议1", "可能的操作建议2"]
}

注意：
1. 坐标应该是相对于截图左上角的像素坐标
2. 尽量准确识别所有可点击的按钮、输入框、链接等
3. type字段使用英文小写
4. 只返回JSON，不要有其他内容'''

    FIND_ELEMENT_PROMPT = '''请在这张屏幕截图中找到"{target}"。

如果找到，请返回JSON格式：
{{
    "found": true,
    "element": {{
        "name": "元素名称",
        "type": "元素类型",
        "description": "元素描述",
        "x": 左上角X坐标,
        "y": 左上角Y坐标,
        "width": 宽度,
        "height": 高度,
        "clickable": true或false,
        "text": "元素文字"
    }}
}}

如果未找到，返回：
{{
    "found": false,
    "reason": "未找到的原因"
}}

只返回JSON，不要有其他内容。'''

    ACTION_PROMPT = '''你是一个电脑自动化助手。根据用户的任务描述和当前屏幕截图，规划下一步操作。

用户任务：{task}

请分析截图，返回JSON格式的操作指令：
{{
    "analysis": "当前屏幕状态分析",
    "can_proceed": true或false,
    "action": {{
        "type": "操作类型(click/type/scroll/hotkey/wait/done)",
        "target": "操作目标描述",
        "x": X坐标(如果是点击操作),
        "y": Y坐标(如果是点击操作),
        "text": "要输入的文本(如果是输入操作)",
        "keys": ["按键列表"](如果是快捷键操作),
        "direction": "up或down(如果是滚动操作)",
        "duration": 等待秒数(如果是等待操作)
    }},
    "reason": "为什么执行这个操作",
    "next_expected": "执行后预期的屏幕变化"
}}

如果任务已完成，action.type 设为 "done"。
如果无法继续，can_proceed 设为 false 并说明原因。
只返回JSON。'''
    
    def __init__(self, llm_client: LLMClient):
        """
        Args:
            llm_client: LLM客户端实例
        """
        self.llm = llm_client
    
    def analyze_screen(self, screenshot: Union[str, Image.Image, bytes]) -> ScreenAnalysis:
        """
        分析屏幕截图，识别所有UI元素
        
        Args:
            screenshot: 屏幕截图
            
        Returns:
            屏幕分析结果
        """
        messages = [Message("user", self.ANALYSIS_PROMPT)]
        
        response = self.llm.chat_with_vision(messages, [screenshot])
        
        # 解析JSON响应
        try:
            # 尝试从响应中提取JSON
            content = response.content
            # 处理可能的markdown代码块
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            
            data = json.loads(content.strip())
        except json.JSONDecodeError:
            # 如果解析失败，返回基础结果
            return ScreenAnalysis(
                description=response.content,
                elements=[],
                suggested_actions=None
            )
        
        # 构建UIElement列表
        elements = []
        for elem_data in data.get("elements", []):
            try:
                elements.append(UIElement(
                    name=elem_data.get("name", ""),
                    type=elem_data.get("type", "unknown"),
                    description=elem_data.get("description", ""),
                    x=int(elem_data.get("x", 0)),
                    y=int(elem_data.get("y", 0)),
                    width=int(elem_data.get("width", 0)),
                    height=int(elem_data.get("height", 0)),
                    clickable=elem_data.get("clickable", True),
                    text=elem_data.get("text")
                ))
            except (ValueError, TypeError):
                continue
        
        return ScreenAnalysis(
            description=data.get("description", ""),
            elements=elements,
            app_name=data.get("app_name"),
            window_title=data.get("window_title"),
            suggested_actions=data.get("suggested_actions")
        )
    
    def find_element(self, screenshot: Union[str, Image.Image, bytes],
                     target: str) -> Optional[UIElement]:
        """
        在截图中查找指定元素
        
        Args:
            screenshot: 屏幕截图
            target: 要查找的元素描述
            
        Returns:
            找到的元素，未找到返回None
        """
        prompt = self.FIND_ELEMENT_PROMPT.format(target=target)
        messages = [Message("user", prompt)]
        
        response = self.llm.chat_with_vision(messages, [screenshot])
        
        try:
            content = response.content
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            
            data = json.loads(content.strip())
            
            if data.get("found") and "element" in data:
                elem = data["element"]
                return UIElement(
                    name=elem.get("name", target),
                    type=elem.get("type", "unknown"),
                    description=elem.get("description", ""),
                    x=int(elem.get("x", 0)),
                    y=int(elem.get("y", 0)),
                    width=int(elem.get("width", 0)),
                    height=int(elem.get("height", 0)),
                    clickable=elem.get("clickable", True),
                    text=elem.get("text")
                )
        except (json.JSONDecodeError, ValueError, TypeError):
            pass
        
        return None
    
    def plan_action(self, screenshot: Union[str, Image.Image, bytes],
                    task: str) -> Dict[str, Any]:
        """
        根据任务和当前屏幕，规划下一步操作
        
        Args:
            screenshot: 当前屏幕截图
            task: 要完成的任务描述
            
        Returns:
            操作指令字典
        """
        prompt = self.ACTION_PROMPT.format(task=task)
        messages = [Message("user", prompt)]
        
        response = self.llm.chat_with_vision(messages, [screenshot])
        
        try:
            content = response.content
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            
            return json.loads(content.strip())
        except json.JSONDecodeError:
            return {
                "analysis": response.content,
                "can_proceed": False,
                "action": {"type": "error"},
                "reason": "无法解析AI响应"
            }
    
    def describe_screen(self, screenshot: Union[str, Image.Image, bytes]) -> str:
        """
        获取屏幕的文字描述
        
        Args:
            screenshot: 屏幕截图
            
        Returns:
            屏幕描述文本
        """
        prompt = "请描述这张屏幕截图的内容，包括当前打开的应用、显示的内容、以及主要的可交互元素。"
        messages = [Message("user", prompt)]
        
        response = self.llm.chat_with_vision(messages, [screenshot])
        return response.content
    
    def get_click_position(self, screenshot: Union[str, Image.Image, bytes],
                           target: str) -> Optional[Tuple[int, int]]:
        """
        获取要点击的位置坐标
        
        Args:
            screenshot: 屏幕截图
            target: 点击目标描述
            
        Returns:
            (x, y) 坐标，未找到返回None
        """
        element = self.find_element(screenshot, target)
        if element:
            return element.center
        return None
