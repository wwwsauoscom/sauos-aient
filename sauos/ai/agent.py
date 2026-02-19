"""
AI Agent 模块
智能自动化控制器，使用大模型理解屏幕并执行任务
"""

import time
import logging
from typing import Optional, List, Dict, Any, Callable
from dataclasses import dataclass, field
from enum import Enum

from ..automation import Automation
from ..core.keyboard import Key
from .llm import LLMClient, Message
from .vision import VisionAnalyzer, UIElement


class ActionType(Enum):
    """动作类型"""
    CLICK = "click"
    TYPE = "type"
    SCROLL = "scroll"
    HOTKEY = "hotkey"
    WAIT = "wait"
    DONE = "done"
    ERROR = "error"


@dataclass
class Action:
    """执行动作"""
    type: ActionType
    target: Optional[str] = None
    x: Optional[int] = None
    y: Optional[int] = None
    text: Optional[str] = None
    keys: Optional[List[str]] = None
    direction: Optional[str] = None
    duration: Optional[float] = None
    reason: str = ""


@dataclass 
class StepResult:
    """步骤执行结果"""
    step: int
    action: Action
    success: bool
    screenshot_path: Optional[str] = None
    error: Optional[str] = None
    duration: float = 0.0


@dataclass
class TaskResult:
    """任务执行结果"""
    task: str
    success: bool
    steps: List[StepResult] = field(default_factory=list)
    total_duration: float = 0.0
    final_message: str = ""


class AIAgent:
    """
    AI智能体
    
    使用大模型视觉能力理解屏幕，自动规划和执行操作
    """
    
    def __init__(self,
                 llm_client: LLMClient,
                 automation: Optional[Automation] = None,
                 max_steps: int = 50,
                 step_delay: float = 1.0,
                 save_screenshots: bool = False,
                 screenshot_dir: str = "./screenshots"):
        """
        初始化AI Agent
        
        Args:
            llm_client: LLM客户端
            automation: 自动化实例，None则自动创建
            max_steps: 最大执行步数
            step_delay: 每步之间的延迟（秒）
            save_screenshots: 是否保存每步截图
            screenshot_dir: 截图保存目录
        """
        self.llm = llm_client
        self.automation = automation or Automation()
        self.vision = VisionAnalyzer(llm_client)
        
        self.max_steps = max_steps
        self.step_delay = step_delay
        self.save_screenshots = save_screenshots
        self.screenshot_dir = screenshot_dir
        
        self._logger = logging.getLogger(__name__)
        self._running = False
        self._cancelled = False
        
        # 回调函数
        self.on_step: Optional[Callable[[int, Action], None]] = None
        self.on_screenshot: Optional[Callable[[int, Any], None]] = None
    
    def run(self, task: str) -> TaskResult:
        """
        执行任务
        
        Args:
            task: 任务描述，如"打开浏览器搜索Python教程"
            
        Returns:
            任务执行结果
        """
        self._running = True
        self._cancelled = False
        
        result = TaskResult(task=task, success=False)
        start_time = time.time()
        
        self._logger.info(f"开始执行任务: {task}")
        
        for step in range(self.max_steps):
            if self._cancelled:
                result.final_message = "任务被取消"
                break
            
            step_start = time.time()
            
            # 1. 截取屏幕
            screenshot = self.automation.screenshot()
            
            if self.save_screenshots:
                import os
                os.makedirs(self.screenshot_dir, exist_ok=True)
                screenshot_path = f"{self.screenshot_dir}/step_{step:03d}.png"
                screenshot.save(screenshot_path)
            else:
                screenshot_path = None
            
            if self.on_screenshot:
                self.on_screenshot(step, screenshot)
            
            # 2. 让AI规划下一步
            plan = self.vision.plan_action(screenshot, task)
            
            self._logger.debug(f"Step {step} plan: {plan}")
            
            # 3. 解析动作
            action = self._parse_action(plan)
            
            if self.on_step:
                self.on_step(step, action)
            
            # 4. 检查是否完成或出错
            if action.type == ActionType.DONE:
                result.success = True
                result.final_message = plan.get("reason", "任务完成")
                self._logger.info(f"任务完成: {result.final_message}")
                break
            
            if action.type == ActionType.ERROR or not plan.get("can_proceed", True):
                result.final_message = plan.get("reason", "无法继续执行")
                self._logger.error(f"任务失败: {result.final_message}")
                break
            
            # 5. 执行动作
            step_result = StepResult(
                step=step,
                action=action,
                success=True,
                screenshot_path=screenshot_path
            )
            
            try:
                self._execute_action(action)
                self._logger.info(f"Step {step}: {action.type.value} - {action.reason}")
            except Exception as e:
                step_result.success = False
                step_result.error = str(e)
                self._logger.error(f"Step {step} failed: {e}")
            
            step_result.duration = time.time() - step_start
            result.steps.append(step_result)
            
            # 等待UI响应
            time.sleep(self.step_delay)
        
        else:
            result.final_message = f"达到最大步数限制({self.max_steps})"
        
        result.total_duration = time.time() - start_time
        self._running = False
        
        return result
    
    def _parse_action(self, plan: Dict[str, Any]) -> Action:
        """解析AI返回的动作"""
        action_data = plan.get("action", {})
        action_type_str = action_data.get("type", "error")
        
        try:
            action_type = ActionType(action_type_str)
        except ValueError:
            action_type = ActionType.ERROR
        
        return Action(
            type=action_type,
            target=action_data.get("target"),
            x=action_data.get("x"),
            y=action_data.get("y"),
            text=action_data.get("text"),
            keys=action_data.get("keys"),
            direction=action_data.get("direction"),
            duration=action_data.get("duration"),
            reason=plan.get("reason", "")
        )
    
    def _execute_action(self, action: Action):
        """执行动作"""
        if action.type == ActionType.CLICK:
            if action.x is not None and action.y is not None:
                self.automation.click((action.x, action.y))
            else:
                raise ValueError("点击操作需要坐标")
        
        elif action.type == ActionType.TYPE:
            if action.text:
                self.automation.write(action.text)
            else:
                raise ValueError("输入操作需要文本")
        
        elif action.type == ActionType.SCROLL:
            direction = action.direction or "down"
            if direction == "up":
                self.automation.scroll_up(5)
            else:
                self.automation.scroll_down(5)
        
        elif action.type == ActionType.HOTKEY:
            if action.keys:
                self.automation.hotkey(*action.keys)
            else:
                raise ValueError("快捷键操作需要按键列表")
        
        elif action.type == ActionType.WAIT:
            duration = action.duration or 1.0
            time.sleep(duration)
    
    def click(self, target: str) -> bool:
        """
        智能点击指定目标
        
        Args:
            target: 点击目标描述
            
        Returns:
            是否成功
        """
        screenshot = self.automation.screenshot()
        position = self.vision.get_click_position(screenshot, target)
        
        if position:
            self.automation.click(position)
            return True
        return False
    
    def find_and_click(self, target: str, timeout: float = 10.0) -> bool:
        """
        查找并点击目标，支持等待
        
        Args:
            target: 点击目标描述
            timeout: 超时时间
        """
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            if self.click(target):
                return True
            time.sleep(0.5)
        
        return False
    
    def type_at(self, target: str, text: str) -> bool:
        """
        在指定位置输入文本
        
        Args:
            target: 输入框描述
            text: 要输入的文本
        """
        if self.click(target):
            time.sleep(0.2)
            self.automation.write(text)
            return True
        return False
    
    def analyze_screen(self):
        """分析当前屏幕"""
        screenshot = self.automation.screenshot()
        return self.vision.analyze_screen(screenshot)
    
    def describe_screen(self) -> str:
        """描述当前屏幕"""
        screenshot = self.automation.screenshot()
        return self.vision.describe_screen(screenshot)
    
    def ask(self, question: str) -> str:
        """
        根据当前屏幕回答问题
        
        Args:
            question: 问题
            
        Returns:
            回答
        """
        screenshot = self.automation.screenshot()
        messages = [Message("user", question)]
        response = self.llm.chat_with_vision(messages, [screenshot])
        return response.content
    
    def cancel(self):
        """取消当前任务"""
        self._cancelled = True
    
    @property
    def is_running(self) -> bool:
        """是否正在运行"""
        return self._running


class AIAgentBuilder:
    """AI Agent 构建器"""
    
    def __init__(self):
        self._llm_client = None
        self._automation = None
        self._max_steps = 50
        self._step_delay = 1.0
        self._save_screenshots = False
        self._screenshot_dir = "./screenshots"
    
    def with_openai(self, api_key: str = None, model: str = "gpt-4o", 
                    base_url: str = None) -> "AIAgentBuilder":
        """使用OpenAI"""
        from .llm import OpenAIClient
        kwargs = {"model": model}
        if api_key:
            kwargs["api_key"] = api_key
        if base_url:
            kwargs["base_url"] = base_url
        self._llm_client = OpenAIClient(**kwargs)
        return self
    
    def with_claude(self, api_key: str = None, 
                    model: str = "claude-sonnet-4-20250514") -> "AIAgentBuilder":
        """使用Claude"""
        from .llm import ClaudeClient
        kwargs = {"model": model}
        if api_key:
            kwargs["api_key"] = api_key
        self._llm_client = ClaudeClient(**kwargs)
        return self
    
    def with_ollama(self, model: str = "llama3.2-vision",
                    base_url: str = "http://localhost:11434") -> "AIAgentBuilder":
        """使用Ollama本地模型"""
        from .llm import OllamaClient
        self._llm_client = OllamaClient(model=model, base_url=base_url)
        return self
    
    def with_alibailian(self, api_key: str = None, model: str = "qwen-max",
                        vision_model: str = "qwen-vl-max") -> "AIAgentBuilder":
        """使用阿里百炼"""
        from .llm import AliBailianClient
        kwargs = {"model": model, "vision_model": vision_model}
        if api_key:
            kwargs["api_key"] = api_key
        self._llm_client = AliBailianClient(**kwargs)
        return self
    
    def with_minimax(self, api_key: str = None, model: str = "MiniMax-Text-01",
                     vision_model: str = "MiniMax-VL-01") -> "AIAgentBuilder":
        """使用MiniMax"""
        from .llm import MiniMaxClient
        kwargs = {"model": model, "vision_model": vision_model}
        if api_key:
            kwargs["api_key"] = api_key
        self._llm_client = MiniMaxClient(**kwargs)
        return self
    
    def with_volcengine(self, api_key: str = None, model: str = "doubao-pro-32k",
                        vision_model: str = "doubao-vision-pro-32k") -> "AIAgentBuilder":
        """使用火山引擎(豆包)"""
        from .llm import VolcEngineClient
        kwargs = {"model": model, "vision_model": vision_model}
        if api_key:
            kwargs["api_key"] = api_key
        self._llm_client = VolcEngineClient(**kwargs)
        return self
    
    def with_deepseek(self, api_key: str = None, 
                      model: str = "deepseek-chat") -> "AIAgentBuilder":
        """使用DeepSeek"""
        from .llm import DeepSeekClient
        kwargs = {"model": model}
        if api_key:
            kwargs["api_key"] = api_key
        self._llm_client = DeepSeekClient(**kwargs)
        return self
    
    def with_zhipu(self, api_key: str = None, model: str = "glm-4",
                   vision_model: str = "glm-4v") -> "AIAgentBuilder":
        """使用智谱AI"""
        from .llm import ZhipuClient
        kwargs = {"model": model, "vision_model": vision_model}
        if api_key:
            kwargs["api_key"] = api_key
        self._llm_client = ZhipuClient(**kwargs)
        return self
    
    def with_moonshot(self, api_key: str = None, 
                      model: str = "moonshot-v1-32k") -> "AIAgentBuilder":
        """使用月之暗面(Kimi)"""
        from .llm import MoonshotClient
        kwargs = {"model": model}
        if api_key:
            kwargs["api_key"] = api_key
        self._llm_client = MoonshotClient(**kwargs)
        return self
    
    def with_provider(self, provider: str, **kwargs) -> "AIAgentBuilder":
        """使用指定提供商（通用方法）"""
        from .llm import create_client
        self._llm_client = create_client(provider, **kwargs)
        return self
    
    def with_config(self, provider: str = None) -> "AIAgentBuilder":
        """从配置文件加载"""
        from .config import ConfigManager
        mgr = ConfigManager().load()
        if provider:
            mgr.set_active(provider)
        self._llm_client = mgr.client
        return self
    
    def with_llm(self, llm_client: LLMClient) -> "AIAgentBuilder":
        """使用自定义LLM客户端"""
        self._llm_client = llm_client
        return self
    
    def max_steps(self, steps: int) -> "AIAgentBuilder":
        """设置最大步数"""
        self._max_steps = steps
        return self
    
    def step_delay(self, delay: float) -> "AIAgentBuilder":
        """设置步骤延迟"""
        self._step_delay = delay
        return self
    
    def save_screenshots(self, save: bool = True, 
                         directory: str = "./screenshots") -> "AIAgentBuilder":
        """保存截图"""
        self._save_screenshots = save
        self._screenshot_dir = directory
        return self
    
    def build(self) -> AIAgent:
        """构建Agent"""
        if self._llm_client is None:
            raise ValueError(
                "需要指定LLM客户端。可选:\n"
                "  .with_openai()       - OpenAI GPT\n"
                "  .with_claude()       - Anthropic Claude\n"
                "  .with_alibailian()   - 阿里百炼 (通义千问)\n"
                "  .with_minimax()      - MiniMax\n"
                "  .with_volcengine()   - 火山引擎 (豆包)\n"
                "  .with_deepseek()     - DeepSeek\n"
                "  .with_zhipu()        - 智谱AI (GLM)\n"
                "  .with_moonshot()     - 月之暗面 (Kimi)\n"
                "  .with_ollama()       - Ollama 本地模型\n"
                "  .with_provider(name) - 通用切换\n"
                "  .with_config()       - 从配置文件加载"
            )
        
        return AIAgent(
            llm_client=self._llm_client,
            automation=self._automation,
            max_steps=self._max_steps,
            step_delay=self._step_delay,
            save_screenshots=self._save_screenshots,
            screenshot_dir=self._screenshot_dir
        )
