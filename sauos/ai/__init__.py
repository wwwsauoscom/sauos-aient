"""
AI 模块
提供大模型接口和智能自动化能力
支持: OpenAI / Claude / 阿里百炼 / MiniMax / 火山引擎 / DeepSeek / 智谱 / 月之暗面 / Ollama
"""

from .llm import (
    LLMClient,
    OpenAICompatibleClient,
    OpenAIClient,
    ClaudeClient,
    OllamaClient,
    AliBailianClient,
    MiniMaxClient,
    VolcEngineClient,
    DeepSeekClient,
    ZhipuClient,
    MoonshotClient,
    create_client,
    register_provider,
    list_providers,
    PROVIDERS,
    Message,
    LLMResponse,
)
from .vision import VisionAnalyzer
from .agent import AIAgent, AIAgentBuilder
from .config import ConfigManager, Config

__all__ = [
    # 基类
    "LLMClient",
    "OpenAICompatibleClient",
    "Message",
    "LLMResponse",
    # 客户端
    "OpenAIClient",
    "ClaudeClient",
    "OllamaClient",
    "AliBailianClient",
    "MiniMaxClient",
    "VolcEngineClient",
    "DeepSeekClient",
    "ZhipuClient",
    "MoonshotClient",
    # 工厂
    "create_client",
    "register_provider",
    "list_providers",
    "PROVIDERS",
    # AI功能
    "VisionAnalyzer",
    "AIAgent",
    "AIAgentBuilder",
    # 配置
    "ConfigManager",
    "Config",
]
