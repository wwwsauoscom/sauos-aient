"""
任务调度器
支持任务定义、顺序执行、条件执行、循环执行
"""

import time
import logging
from typing import Optional, List, Callable, Any, Dict
from dataclasses import dataclass, field
from enum import Enum
from concurrent.futures import ThreadPoolExecutor
import threading

from .automation import Automation


class TaskStatus(Enum):
    """任务状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"


@dataclass
class TaskResult:
    """任务执行结果"""
    task_name: str
    status: TaskStatus
    result: Any = None
    error: Optional[Exception] = None
    duration: float = 0.0
    
    @property
    def success(self) -> bool:
        return self.status == TaskStatus.COMPLETED


@dataclass
class Task:
    """任务定义"""
    name: str
    action: Callable[[Automation], Any]
    condition: Optional[Callable[[Automation], bool]] = None
    retry_count: int = 0
    retry_delay: float = 1.0
    timeout: Optional[float] = None
    on_success: Optional[Callable[[TaskResult], None]] = None
    on_failure: Optional[Callable[[TaskResult], None]] = None
    
    def __post_init__(self):
        self.status = TaskStatus.PENDING


class TaskScheduler:
    """
    任务调度器
    
    支持任务编排、条件执行、错误处理
    """
    
    def __init__(self, automation: Optional[Automation] = None):
        """
        初始化调度器
        
        Args:
            automation: Automation实例，None则自动创建
        """
        self.automation = automation or Automation()
        self.tasks: List[Task] = []
        self.results: List[TaskResult] = []
        self._running = False
        self._cancelled = False
        self._logger = logging.getLogger(__name__)
    
    def add(self, name: str, action: Callable[[Automation], Any],
            condition: Optional[Callable[[Automation], bool]] = None,
            retry_count: int = 0,
            retry_delay: float = 1.0,
            timeout: Optional[float] = None) -> "TaskScheduler":
        """
        添加任务
        
        Args:
            name: 任务名称
            action: 任务动作，接收Automation实例
            condition: 执行条件，返回False则跳过
            retry_count: 重试次数
            retry_delay: 重试延迟（秒）
            timeout: 超时时间（秒）
        """
        task = Task(
            name=name,
            action=action,
            condition=condition,
            retry_count=retry_count,
            retry_delay=retry_delay,
            timeout=timeout
        )
        self.tasks.append(task)
        return self
    
    def add_click(self, name: str, target, **kwargs) -> "TaskScheduler":
        """添加点击任务"""
        return self.add(name, lambda auto: auto.click(target), **kwargs)
    
    def add_type(self, name: str, text: str, **kwargs) -> "TaskScheduler":
        """添加输入任务"""
        return self.add(name, lambda auto: auto.write(text), **kwargs)
    
    def add_wait(self, name: str, seconds: float) -> "TaskScheduler":
        """添加等待任务"""
        return self.add(name, lambda auto: auto.sleep(seconds))
    
    def add_wait_for(self, name: str, template, timeout: float = 10.0, **kwargs) -> "TaskScheduler":
        """添加等待目标任务"""
        return self.add(name, lambda auto: auto.wait_for(template, timeout), **kwargs)
    
    def add_screenshot(self, name: str, filepath: str, **kwargs) -> "TaskScheduler":
        """添加截图任务"""
        return self.add(name, lambda auto: auto.save_screenshot(filepath), **kwargs)
    
    def add_hotkey(self, name: str, *keys, **kwargs) -> "TaskScheduler":
        """添加快捷键任务"""
        return self.add(name, lambda auto: auto.hotkey(*keys), **kwargs)
    
    def run(self, stop_on_error: bool = False) -> List[TaskResult]:
        """
        执行所有任务
        
        Args:
            stop_on_error: 遇到错误是否停止
            
        Returns:
            任务结果列表
        """
        self._running = True
        self._cancelled = False
        self.results = []
        
        for task in self.tasks:
            if self._cancelled:
                self._logger.info(f"任务调度已取消")
                break
            
            result = self._execute_task(task)
            self.results.append(result)
            
            if not result.success and stop_on_error:
                self._logger.error(f"任务 '{task.name}' 失败，停止执行")
                break
        
        self._running = False
        return self.results
    
    def _execute_task(self, task: Task) -> TaskResult:
        """执行单个任务"""
        start_time = time.time()
        
        # 检查条件
        if task.condition and not task.condition(self.automation):
            self._logger.info(f"任务 '{task.name}' 条件不满足，跳过")
            return TaskResult(
                task_name=task.name,
                status=TaskStatus.SKIPPED,
                duration=time.time() - start_time
            )
        
        # 执行任务（带重试）
        last_error = None
        for attempt in range(task.retry_count + 1):
            try:
                self._logger.info(f"执行任务 '{task.name}'" + 
                                 (f" (重试 {attempt})" if attempt > 0 else ""))
                
                result_value = task.action(self.automation)
                
                result = TaskResult(
                    task_name=task.name,
                    status=TaskStatus.COMPLETED,
                    result=result_value,
                    duration=time.time() - start_time
                )
                
                if task.on_success:
                    task.on_success(result)
                
                return result
                
            except Exception as e:
                last_error = e
                self._logger.warning(f"任务 '{task.name}' 执行失败: {e}")
                
                if attempt < task.retry_count:
                    time.sleep(task.retry_delay)
        
        # 所有重试都失败
        result = TaskResult(
            task_name=task.name,
            status=TaskStatus.FAILED,
            error=last_error,
            duration=time.time() - start_time
        )
        
        if task.on_failure:
            task.on_failure(result)
        
        return result
    
    def cancel(self):
        """取消执行"""
        self._cancelled = True
    
    @property
    def is_running(self) -> bool:
        """是否正在执行"""
        return self._running
    
    def clear(self) -> "TaskScheduler":
        """清空任务列表"""
        self.tasks = []
        self.results = []
        return self
    
    def get_summary(self) -> Dict[str, Any]:
        """获取执行摘要"""
        total = len(self.results)
        completed = sum(1 for r in self.results if r.status == TaskStatus.COMPLETED)
        failed = sum(1 for r in self.results if r.status == TaskStatus.FAILED)
        skipped = sum(1 for r in self.results if r.status == TaskStatus.SKIPPED)
        total_duration = sum(r.duration for r in self.results)
        
        return {
            "total_tasks": total,
            "completed": completed,
            "failed": failed,
            "skipped": skipped,
            "success_rate": completed / total if total > 0 else 0,
            "total_duration": total_duration,
            "results": self.results
        }
    
    def print_summary(self):
        """打印执行摘要"""
        summary = self.get_summary()
        print(f"\n{'='*50}")
        print(f"任务执行摘要")
        print(f"{'='*50}")
        print(f"总任务数: {summary['total_tasks']}")
        print(f"完成: {summary['completed']}")
        print(f"失败: {summary['failed']}")
        print(f"跳过: {summary['skipped']}")
        print(f"成功率: {summary['success_rate']*100:.1f}%")
        print(f"总耗时: {summary['total_duration']:.2f}秒")
        print(f"{'='*50}")
        
        for result in self.results:
            status_icon = "✓" if result.success else ("○" if result.status == TaskStatus.SKIPPED else "✗")
            print(f"  {status_icon} {result.task_name} ({result.duration:.2f}s)")
            if result.error:
                print(f"    错误: {result.error}")


class WorkflowBuilder:
    """
    工作流构建器
    
    提供更友好的任务编排DSL
    """
    
    def __init__(self, automation: Optional[Automation] = None):
        self.scheduler = TaskScheduler(automation)
        self._step_count = 0
    
    def _next_name(self, prefix: str = "步骤") -> str:
        self._step_count += 1
        return f"{prefix}_{self._step_count}"
    
    def click(self, target, name: str = None) -> "WorkflowBuilder":
        """点击"""
        self.scheduler.add_click(name or self._next_name("点击"), target)
        return self
    
    def type(self, text: str, name: str = None) -> "WorkflowBuilder":
        """输入文本"""
        self.scheduler.add_type(name or self._next_name("输入"), text)
        return self
    
    def wait(self, seconds: float, name: str = None) -> "WorkflowBuilder":
        """等待"""
        self.scheduler.add_wait(name or self._next_name("等待"), seconds)
        return self
    
    def wait_for(self, template, timeout: float = 10.0, name: str = None) -> "WorkflowBuilder":
        """等待目标出现"""
        self.scheduler.add_wait_for(name or self._next_name("等待目标"), template, timeout)
        return self
    
    def screenshot(self, filepath: str, name: str = None) -> "WorkflowBuilder":
        """截图"""
        self.scheduler.add_screenshot(name or self._next_name("截图"), filepath)
        return self
    
    def hotkey(self, *keys, name: str = None) -> "WorkflowBuilder":
        """快捷键"""
        self.scheduler.add_hotkey(name or self._next_name("快捷键"), *keys)
        return self
    
    def custom(self, action: Callable[[Automation], Any], name: str = None) -> "WorkflowBuilder":
        """自定义操作"""
        self.scheduler.add(name or self._next_name("自定义"), action)
        return self
    
    def run(self, stop_on_error: bool = False) -> List[TaskResult]:
        """执行工作流"""
        return self.scheduler.run(stop_on_error)
    
    def summary(self):
        """打印摘要"""
        self.scheduler.print_summary()
