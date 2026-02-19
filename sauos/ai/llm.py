"""
大模型接口模块
支持 OpenAI / Claude / 阿里百炼 / MiniMax / 火山引擎 / Ollama 等，随时切换
"""

import os
import json
import base64
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any, Union
from dataclasses import dataclass, field
from PIL import Image
import io

try:
    import httpx
except ImportError:
    httpx = None


# ==================== 数据结构 ====================

@dataclass
class Message:
    """消息"""
    role: str  # system, user, assistant
    content: Union[str, List[Dict]]
    
    def to_dict(self) -> Dict:
        return {"role": self.role, "content": self.content}


@dataclass
class LLMResponse:
    """LLM响应"""
    content: str
    model: str
    usage: Optional[Dict] = None
    raw_response: Optional[Dict] = None


# ==================== 基类 ====================

class LLMClient(ABC):
    """LLM客户端基类"""
    
    provider: str = "base"
    
    @abstractmethod
    def chat(self, messages: List[Message], **kwargs) -> LLMResponse:
        """发送对话请求"""
        pass
    
    @abstractmethod
    def chat_with_vision(self, messages: List[Message], 
                         images: List[Union[str, Image.Image, bytes]],
                         **kwargs) -> LLMResponse:
        """发送带图像的对话请求"""
        pass
    
    def _image_to_base64(self, image: Union[str, Image.Image, bytes]) -> str:
        """将图像转换为base64"""
        if isinstance(image, str):
            with open(image, "rb") as f:
                return base64.b64encode(f.read()).decode()
        elif isinstance(image, Image.Image):
            buffer = io.BytesIO()
            image.save(buffer, format="PNG")
            return base64.b64encode(buffer.getvalue()).decode()
        elif isinstance(image, bytes):
            return base64.b64encode(image).decode()
        else:
            raise TypeError(f"不支持的图像类型: {type(image)}")
    
    def _ensure_httpx(self):
        if httpx is None:
            raise ImportError("请安装httpx: pip install httpx")

    def __repr__(self):
        return f"<{self.__class__.__name__} provider={self.provider} model={getattr(self, 'model', '?')}>"


# ==================== OpenAI 兼容基类 ====================

class OpenAICompatibleClient(LLMClient):
    """
    OpenAI兼容API客户端基类
    
    阿里百炼、MiniMax、火山引擎、DeepSeek等都兼容OpenAI格式，
    只需配置不同的base_url和api_key即可
    """
    
    provider = "openai_compatible"
    
    def __init__(self, 
                 api_key: Optional[str] = None,
                 api_key_env: str = "OPENAI_API_KEY",
                 base_url: str = "https://api.openai.com/v1",
                 model: str = "gpt-4o",
                 vision_model: Optional[str] = None,
                 timeout: float = 60.0,
                 extra_headers: Optional[Dict] = None):
        """
        Args:
            api_key: API密钥
            api_key_env: API密钥环境变量名
            base_url: API基础URL
            model: 默认模型
            vision_model: 视觉模型（None则使用默认model）
            timeout: 请求超时时间
            extra_headers: 额外请求头
        """
        self._ensure_httpx()
        
        self.api_key = api_key or os.environ.get(api_key_env)
        if not self.api_key:
            raise ValueError(f"需要提供api_key或设置{api_key_env}环境变量")
        
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.vision_model = vision_model or model
        self.timeout = timeout
        self.extra_headers = extra_headers or {}
        self._client = httpx.Client(timeout=timeout)
    
    def _headers(self) -> Dict:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        headers.update(self.extra_headers)
        return headers
    
    def chat(self, messages: List[Message], 
             model: Optional[str] = None,
             temperature: float = 0.7,
             max_tokens: Optional[int] = None,
             **kwargs) -> LLMResponse:
        payload = {
            "model": model or self.model,
            "messages": [m.to_dict() for m in messages],
            "temperature": temperature,
            **kwargs
        }
        if max_tokens:
            payload["max_tokens"] = max_tokens
        
        response = self._client.post(
            f"{self.base_url}/chat/completions",
            headers=self._headers(),
            json=payload
        )
        response.raise_for_status()
        data = response.json()
        
        return LLMResponse(
            content=data["choices"][0]["message"]["content"],
            model=data.get("model", model or self.model),
            usage=data.get("usage"),
            raw_response=data
        )
    
    def chat_with_vision(self, messages: List[Message],
                         images: List[Union[str, Image.Image, bytes]],
                         model: Optional[str] = None,
                         detail: str = "auto",
                         **kwargs) -> LLMResponse:
        vision_messages = []
        for msg in messages:
            if msg.role == "user" and isinstance(msg.content, str):
                content = [{"type": "text", "text": msg.content}]
                for img in images:
                    img_base64 = self._image_to_base64(img)
                    content.append({
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{img_base64}",
                            "detail": detail
                        }
                    })
                vision_messages.append(Message(msg.role, content))
            else:
                vision_messages.append(msg)
        
        return self.chat(vision_messages, model=model or self.vision_model, **kwargs)
    
    def __del__(self):
        if hasattr(self, '_client'):
            self._client.close()


# ==================== 各平台实现 ====================

class OpenAIClient(OpenAICompatibleClient):
    """OpenAI API 客户端"""
    
    provider = "openai"
    
    def __init__(self, 
                 api_key: Optional[str] = None,
                 base_url: str = "https://api.openai.com/v1",
                 model: str = "gpt-4o",
                 timeout: float = 60.0):
        super().__init__(
            api_key=api_key,
            api_key_env="OPENAI_API_KEY",
            base_url=base_url,
            model=model,
            vision_model=model,
            timeout=timeout
        )


class AliBailianClient(OpenAICompatibleClient):
    """
    阿里百炼 (DashScope) 客户端
    兼容OpenAI格式
    
    模型: qwen-vl-max / qwen-vl-plus / qwen-max / qwen-plus / qwen-turbo
    文档: https://help.aliyun.com/zh/model-studio/
    """
    
    provider = "alibailian"
    
    def __init__(self,
                 api_key: Optional[str] = None,
                 base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1",
                 model: str = "qwen-max",
                 vision_model: str = "qwen-vl-max",
                 timeout: float = 60.0):
        """
        Args:
            api_key: 百炼API Key，默认从DASHSCOPE_API_KEY获取
            base_url: API地址
            model: 文本模型 (qwen-max/qwen-plus/qwen-turbo)
            vision_model: 视觉模型 (qwen-vl-max/qwen-vl-plus)
            timeout: 超时时间
        """
        super().__init__(
            api_key=api_key,
            api_key_env="DASHSCOPE_API_KEY",
            base_url=base_url,
            model=model,
            vision_model=vision_model,
            timeout=timeout
        )


class MiniMaxClient(OpenAICompatibleClient):
    """
    MiniMax 客户端
    兼容OpenAI格式
    
    模型: MiniMax-Text-01 / abab6.5s-chat / abab7-chat-preview
    文档: https://platform.minimaxi.com/document/
    """
    
    provider = "minimax"
    
    def __init__(self,
                 api_key: Optional[str] = None,
                 base_url: str = "https://api.minimax.chat/v1",
                 model: str = "MiniMax-Text-01",
                 vision_model: str = "MiniMax-VL-01",
                 timeout: float = 60.0):
        """
        Args:
            api_key: MiniMax API Key，默认从MINIMAX_API_KEY获取
            base_url: API地址
            model: 文本模型
            vision_model: 视觉模型
            timeout: 超时时间
        """
        super().__init__(
            api_key=api_key,
            api_key_env="MINIMAX_API_KEY",
            base_url=base_url,
            model=model,
            vision_model=vision_model,
            timeout=timeout
        )


class VolcEngineClient(OpenAICompatibleClient):
    """
    火山引擎 (豆包) 客户端
    兼容OpenAI格式
    
    模型: doubao-pro-32k / doubao-pro-128k / doubao-vision-pro-32k
    文档: https://www.volcengine.com/docs/82379/
    """
    
    provider = "volcengine"
    
    def __init__(self,
                 api_key: Optional[str] = None,
                 base_url: str = "https://ark.cn-beijing.volces.com/api/v3",
                 model: str = "doubao-pro-32k",
                 vision_model: str = "doubao-vision-pro-32k",
                 timeout: float = 60.0):
        """
        Args:
            api_key: 火山引擎API Key，默认从VOLC_API_KEY获取
            base_url: API地址
            model: 文本模型 (doubao-pro-32k/doubao-pro-128k)
            vision_model: 视觉模型 (doubao-vision-pro-32k)
            timeout: 超时时间
        
        注意: 火山引擎的model字段需要填写推理接入点ID (endpoint_id)
        """
        super().__init__(
            api_key=api_key,
            api_key_env="VOLC_API_KEY",
            base_url=base_url,
            model=model,
            vision_model=vision_model,
            timeout=timeout
        )


class DeepSeekClient(OpenAICompatibleClient):
    """
    DeepSeek 客户端
    兼容OpenAI格式
    
    模型: deepseek-chat / deepseek-reasoner
    文档: https://platform.deepseek.com/api-docs
    """
    
    provider = "deepseek"
    
    def __init__(self,
                 api_key: Optional[str] = None,
                 base_url: str = "https://api.deepseek.com/v1",
                 model: str = "deepseek-chat",
                 timeout: float = 60.0):
        super().__init__(
            api_key=api_key,
            api_key_env="DEEPSEEK_API_KEY",
            base_url=base_url,
            model=model,
            vision_model=model,
            timeout=timeout
        )


class ZhipuClient(OpenAICompatibleClient):
    """
    智谱AI (GLM) 客户端
    兼容OpenAI格式
    
    模型: glm-4v / glm-4 / glm-4-flash
    文档: https://open.bigmodel.cn/dev/api/
    """
    
    provider = "zhipu"
    
    def __init__(self,
                 api_key: Optional[str] = None,
                 base_url: str = "https://open.bigmodel.cn/api/paas/v4",
                 model: str = "glm-4",
                 vision_model: str = "glm-4v",
                 timeout: float = 60.0):
        super().__init__(
            api_key=api_key,
            api_key_env="ZHIPU_API_KEY",
            base_url=base_url,
            model=model,
            vision_model=vision_model,
            timeout=timeout
        )


class MoonshotClient(OpenAICompatibleClient):
    """
    月之暗面 (Kimi) 客户端
    兼容OpenAI格式
    
    模型: moonshot-v1-128k / moonshot-v1-32k / moonshot-v1-8k
    文档: https://platform.moonshot.cn/docs/
    """
    
    provider = "moonshot"
    
    def __init__(self,
                 api_key: Optional[str] = None,
                 base_url: str = "https://api.moonshot.cn/v1",
                 model: str = "moonshot-v1-32k",
                 timeout: float = 60.0):
        super().__init__(
            api_key=api_key,
            api_key_env="MOONSHOT_API_KEY",
            base_url=base_url,
            model=model,
            vision_model=model,
            timeout=timeout
        )


# ==================== Claude (非OpenAI兼容) ====================

class ClaudeClient(LLMClient):
    """Anthropic Claude API 客户端"""
    
    provider = "claude"
    
    def __init__(self,
                 api_key: Optional[str] = None,
                 base_url: str = "https://api.anthropic.com",
                 model: str = "claude-sonnet-4-20250514",
                 timeout: float = 60.0):
        self._ensure_httpx()
        
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("需要提供api_key或设置ANTHROPIC_API_KEY环境变量")
        
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout
        self._client = httpx.Client(timeout=timeout)
    
    def _headers(self) -> Dict:
        return {
            "x-api-key": self.api_key,
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01"
        }
    
    def chat(self, messages: List[Message],
             model: Optional[str] = None,
             temperature: float = 0.7,
             max_tokens: int = 4096,
             system: Optional[str] = None,
             **kwargs) -> LLMResponse:
        api_messages = []
        system_prompt = system
        
        for msg in messages:
            if msg.role == "system":
                system_prompt = msg.content if isinstance(msg.content, str) else str(msg.content)
            else:
                api_messages.append(msg.to_dict())
        
        payload = {
            "model": model or self.model,
            "messages": api_messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            **kwargs
        }
        if system_prompt:
            payload["system"] = system_prompt
        
        response = self._client.post(
            f"{self.base_url}/v1/messages",
            headers=self._headers(),
            json=payload
        )
        response.raise_for_status()
        data = response.json()
        
        return LLMResponse(
            content=data["content"][0]["text"],
            model=data["model"],
            usage=data.get("usage"),
            raw_response=data
        )
    
    def chat_with_vision(self, messages: List[Message],
                         images: List[Union[str, Image.Image, bytes]],
                         model: Optional[str] = None,
                         **kwargs) -> LLMResponse:
        vision_messages = []
        
        for msg in messages:
            if msg.role == "user" and isinstance(msg.content, str):
                content = []
                for img in images:
                    img_base64 = self._image_to_base64(img)
                    content.append({
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/png",
                            "data": img_base64
                        }
                    })
                content.append({"type": "text", "text": msg.content})
                vision_messages.append(Message(msg.role, content))
            else:
                vision_messages.append(msg)
        
        return self.chat(vision_messages, model=model, **kwargs)
    
    def __del__(self):
        if hasattr(self, '_client'):
            self._client.close()


# ==================== Ollama (本地模型) ====================

class OllamaClient(LLMClient):
    """Ollama 本地模型客户端"""
    
    provider = "ollama"
    
    def __init__(self,
                 base_url: str = "http://localhost:11434",
                 model: str = "llama3.2-vision",
                 timeout: float = 120.0):
        self._ensure_httpx()
        
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout
        self._client = httpx.Client(timeout=timeout)
    
    def chat(self, messages: List[Message],
             model: Optional[str] = None,
             temperature: float = 0.7,
             **kwargs) -> LLMResponse:
        payload = {
            "model": model or self.model,
            "messages": [m.to_dict() for m in messages],
            "stream": False,
            "options": {"temperature": temperature},
            **kwargs
        }
        
        response = self._client.post(
            f"{self.base_url}/api/chat",
            json=payload
        )
        response.raise_for_status()
        data = response.json()
        
        return LLMResponse(
            content=data["message"]["content"],
            model=data["model"],
            raw_response=data
        )
    
    def chat_with_vision(self, messages: List[Message],
                         images: List[Union[str, Image.Image, bytes]],
                         model: Optional[str] = None,
                         **kwargs) -> LLMResponse:
        image_data = [self._image_to_base64(img) for img in images]
        
        vision_messages = []
        for msg in messages:
            msg_dict = msg.to_dict()
            if msg.role == "user":
                msg_dict["images"] = image_data
            vision_messages.append(msg_dict)
        
        payload = {
            "model": model or self.model,
            "messages": vision_messages,
            "stream": False,
            **kwargs
        }
        
        response = self._client.post(
            f"{self.base_url}/api/chat",
            json=payload
        )
        response.raise_for_status()
        data = response.json()
        
        return LLMResponse(
            content=data["message"]["content"],
            model=data["model"],
            raw_response=data
        )
    
    def __del__(self):
        if hasattr(self, '_client'):
            self._client.close()


# ==================== 注册表 & 工厂 ====================

# 所有可用的提供商
PROVIDERS: Dict[str, type] = {
    # 国际
    "openai": OpenAIClient,
    "claude": ClaudeClient,
    "anthropic": ClaudeClient,
    "deepseek": DeepSeekClient,
    # 国内
    "alibailian": AliBailianClient,
    "dashscope": AliBailianClient,
    "qwen": AliBailianClient,
    "minimax": MiniMaxClient,
    "volcengine": VolcEngineClient,
    "doubao": VolcEngineClient,
    "zhipu": ZhipuClient,
    "glm": ZhipuClient,
    "moonshot": MoonshotClient,
    "kimi": MoonshotClient,
    # 本地
    "ollama": OllamaClient,
}


def create_client(provider: str = "openai", **kwargs) -> LLMClient:
    """
    创建LLM客户端 - 工厂函数
    
    Args:
        provider: 提供商名称
        **kwargs: 传递给客户端的参数
        
    支持的provider:
        国际: openai, claude/anthropic, deepseek
        国内: alibailian/dashscope/qwen, minimax, volcengine/doubao, zhipu/glm, moonshot/kimi
        本地: ollama
        
    示例:
        # OpenAI
        client = create_client("openai", model="gpt-4o")
        
        # 阿里百炼
        client = create_client("alibailian", model="qwen-max")
        
        # 火山引擎
        client = create_client("volcengine", model="<your-endpoint-id>")
        
        # MiniMax
        client = create_client("minimax", model="MiniMax-Text-01")
        
        # Ollama本地
        client = create_client("ollama", model="llama3.2-vision")
    """
    key = provider.lower()
    if key not in PROVIDERS:
        available = sorted(set(PROVIDERS.keys()))
        raise ValueError(f"不支持的提供商: {provider}\n可选: {available}")
    
    return PROVIDERS[key](**kwargs)


def register_provider(name: str, client_class: type):
    """
    注册自定义提供商
    
    Args:
        name: 提供商名称
        client_class: 客户端类（需继承LLMClient）
        
    示例:
        class MyClient(OpenAICompatibleClient):
            provider = "my_provider"
            def __init__(self, **kwargs):
                super().__init__(
                    api_key_env="MY_API_KEY",
                    base_url="https://my-api.example.com/v1",
                    **kwargs
                )
        
        register_provider("my_provider", MyClient)
    """
    if not issubclass(client_class, LLMClient):
        raise TypeError(f"{client_class} 必须继承 LLMClient")
    PROVIDERS[name.lower()] = client_class


def list_providers() -> Dict[str, str]:
    """列出所有可用的提供商及其说明"""
    seen = set()
    result = {}
    for name, cls in sorted(PROVIDERS.items()):
        if cls not in seen:
            seen.add(cls)
            doc = (cls.__doc__ or "").strip().split("\n")[0]
            result[name] = doc
        else:
            # 别名
            for primary, pcls in PROVIDERS.items():
                if pcls == cls and primary != name:
                    result[name] = f"(别名 → {primary})"
                    break
    return result
