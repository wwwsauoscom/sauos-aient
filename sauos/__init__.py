"""
SAUOS - 电脑全自动化系统
Screen Automation Universal Operating System
"""

__version__ = "1.0.0"
__author__ = "SAUOS Team"

from .core.screen import Screen
from .core.mouse import Mouse
from .core.keyboard import Keyboard
from .core.window import Window
from .core.image import ImageMatcher
from .automation import Automation
from .scheduler import TaskScheduler

# AI模块延迟导入（需要额外依赖）
def get_ai_agent():
    """获取AIAgent类（需要安装httpx）"""
    from .ai.agent import AIAgent, AIAgentBuilder
    return AIAgent, AIAgentBuilder

def get_llm_client():
    """获取LLM客户端类"""
    from .ai.llm import OpenAIClient, ClaudeClient, OllamaClient, create_client
    return OpenAIClient, ClaudeClient, OllamaClient, create_client

__all__ = [
    "Screen",
    "Mouse", 
    "Keyboard",
    "Window",
    "ImageMatcher",
    "Automation",
    "TaskScheduler",
    "get_ai_agent",
    "get_llm_client",
]
