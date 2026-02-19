"""
统一配置管理模块
支持配置文件加载、模型切换
"""

import os
import json
from typing import Optional, Dict, Any
from dataclasses import dataclass, field, asdict
from pathlib import Path

from .llm import LLMClient, create_client, PROVIDERS


# 默认配置文件路径
DEFAULT_CONFIG_PATH = os.path.expanduser("~/.sauos/config.json")


@dataclass
class ProviderConfig:
    """单个提供商配置"""
    provider: str
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    model: Optional[str] = None
    vision_model: Optional[str] = None
    timeout: float = 60.0
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Config:
    """全局配置"""
    # 当前使用的提供商
    active_provider: str = "openai"
    
    # 各提供商配置
    providers: Dict[str, ProviderConfig] = field(default_factory=lambda: {
        "openai": ProviderConfig(
            provider="openai",
            model="gpt-4o"
        ),
        "claude": ProviderConfig(
            provider="claude",
            model="claude-sonnet-4-20250514"
        ),
        "alibailian": ProviderConfig(
            provider="alibailian",
            model="qwen-max",
            vision_model="qwen-vl-max"
        ),
        "minimax": ProviderConfig(
            provider="minimax",
            model="MiniMax-Text-01",
            vision_model="MiniMax-VL-01"
        ),
        "volcengine": ProviderConfig(
            provider="volcengine",
            model="doubao-pro-32k",
            vision_model="doubao-vision-pro-32k"
        ),
        "deepseek": ProviderConfig(
            provider="deepseek",
            model="deepseek-chat"
        ),
        "zhipu": ProviderConfig(
            provider="zhipu",
            model="glm-4",
            vision_model="glm-4v"
        ),
        "moonshot": ProviderConfig(
            provider="moonshot",
            model="moonshot-v1-32k"
        ),
        "ollama": ProviderConfig(
            provider="ollama",
            base_url="http://10.10.0.20:11434",
            model="qwen3:8b",
            vision_model="moondream:1.8b",
            timeout=120.0
        ),
    })


class ConfigManager:
    """
    配置管理器
    
    支持从文件加载配置、一键切换模型提供商
    """
    
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or DEFAULT_CONFIG_PATH
        self.config = Config()
        self._clients: Dict[str, LLMClient] = {}
    
    def load(self, config_path: Optional[str] = None) -> "ConfigManager":
        """从文件加载配置"""
        path = config_path or self.config_path
        
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            self.config.active_provider = data.get("active_provider", "openai")
            
            for name, prov_data in data.get("providers", {}).items():
                self.config.providers[name] = ProviderConfig(**prov_data)
        
        return self
    
    def save(self, config_path: Optional[str] = None) -> str:
        """保存配置到文件"""
        path = config_path or self.config_path
        
        os.makedirs(os.path.dirname(path), exist_ok=True)
        
        data = {
            "active_provider": self.config.active_provider,
            "providers": {
                name: asdict(prov) 
                for name, prov in self.config.providers.items()
            }
        }
        
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        return path
    
    def set_active(self, provider: str) -> "ConfigManager":
        """切换当前活跃提供商"""
        if provider not in self.config.providers:
            available = list(self.config.providers.keys())
            raise ValueError(f"未配置的提供商: {provider}，已配置: {available}")
        
        self.config.active_provider = provider
        return self
    
    def set_provider(self, name: str, 
                     api_key: Optional[str] = None,
                     base_url: Optional[str] = None,
                     model: Optional[str] = None,
                     vision_model: Optional[str] = None,
                     **kwargs) -> "ConfigManager":
        """设置提供商配置"""
        if name in self.config.providers:
            prov = self.config.providers[name]
            if api_key:
                prov.api_key = api_key
            if base_url:
                prov.base_url = base_url
            if model:
                prov.model = model
            if vision_model:
                prov.vision_model = vision_model
        else:
            self.config.providers[name] = ProviderConfig(
                provider=name,
                api_key=api_key,
                base_url=base_url,
                model=model,
                vision_model=vision_model,
                **kwargs
            )
        
        # 清除缓存的客户端
        self._clients.pop(name, None)
        return self
    
    def get_client(self, provider: Optional[str] = None) -> LLMClient:
        """
        获取LLM客户端
        
        Args:
            provider: 提供商名称，None使用当前活跃的
        """
        name = provider or self.config.active_provider
        
        # 缓存
        if name in self._clients:
            return self._clients[name]
        
        if name not in self.config.providers:
            raise ValueError(f"未配置的提供商: {name}")
        
        prov = self.config.providers[name]
        
        # 构建参数
        kwargs = {}
        if prov.api_key:
            kwargs["api_key"] = prov.api_key
        if prov.base_url:
            kwargs["base_url"] = prov.base_url
        if prov.model:
            kwargs["model"] = prov.model
        if prov.timeout:
            kwargs["timeout"] = prov.timeout
        
        # vision_model只有OpenAI兼容客户端支持
        if prov.vision_model and prov.provider not in ("claude", "ollama"):
            kwargs["vision_model"] = prov.vision_model
        
        kwargs.update(prov.extra)
        
        client = create_client(prov.provider, **kwargs)
        self._clients[name] = client
        return client
    
    @property
    def client(self) -> LLMClient:
        """当前活跃的客户端"""
        return self.get_client()
    
    def switch(self, provider: str) -> LLMClient:
        """切换并返回新的客户端"""
        self.set_active(provider)
        return self.get_client()
    
    def list_configured(self) -> Dict[str, Dict]:
        """列出所有已配置的提供商"""
        result = {}
        for name, prov in self.config.providers.items():
            result[name] = {
                "provider": prov.provider,
                "model": prov.model,
                "vision_model": prov.vision_model,
                "active": name == self.config.active_provider,
                "has_key": bool(prov.api_key or self._has_env_key(prov.provider))
            }
        return result
    
    def _has_env_key(self, provider: str) -> bool:
        """检查环境变量中是否有对应API Key"""
        env_map = {
            "openai": "OPENAI_API_KEY",
            "claude": "ANTHROPIC_API_KEY",
            "alibailian": "DASHSCOPE_API_KEY",
            "minimax": "MINIMAX_API_KEY",
            "volcengine": "VOLC_API_KEY",
            "deepseek": "DEEPSEEK_API_KEY",
            "zhipu": "ZHIPU_API_KEY",
            "moonshot": "MOONSHOT_API_KEY",
        }
        env_name = env_map.get(provider)
        return bool(env_name and os.environ.get(env_name))
    
    def print_status(self):
        """打印配置状态"""
        configured = self.list_configured()
        
        print(f"\n{'='*55}")
        print(f"  SAUOS 大模型配置状态")
        print(f"{'='*55}")
        print(f"  当前活跃: {self.config.active_provider}")
        print(f"{'─'*55}")
        
        for name, info in configured.items():
            active = " <<" if info["active"] else ""
            key_status = "Key已配置" if info["has_key"] else "Key未配置"
            model = info["model"] or "默认"
            
            print(f"  {name:<14} | {model:<24} | {key_status}{active}")
        
        print(f"{'='*55}\n")
