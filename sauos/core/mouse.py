"""
鼠标控制模块
支持点击、移动、拖拽、滚动等操作
"""

import time
import random
from enum import Enum
from typing import Optional, Tuple, Callable

try:
    import pyautogui
    pyautogui.FAILSAFE = True  # 移动到左上角触发异常
    pyautogui.PAUSE = 0.1  # 操作间隔
except ImportError:
    pyautogui = None


class MouseButton(Enum):
    """鼠标按键"""
    LEFT = "left"
    RIGHT = "right"
    MIDDLE = "middle"


class Mouse:
    """鼠标控制类"""
    
    def __init__(self, move_duration: float = 0.2, click_interval: float = 0.1):
        """
        Args:
            move_duration: 默认移动持续时间
            click_interval: 默认点击间隔
        """
        if pyautogui is None:
            raise ImportError("请安装pyautogui: pip install pyautogui")
        
        self.move_duration = move_duration
        self.click_interval = click_interval
    
    @property
    def position(self) -> Tuple[int, int]:
        """获取当前鼠标位置"""
        return pyautogui.position()
    
    def move(self, x: int, y: int, duration: Optional[float] = None,
             tween: Callable = None) -> "Mouse":
        """
        移动鼠标到指定位置
        
        Args:
            x: 目标X坐标
            y: 目标Y坐标
            duration: 移动持续时间
            tween: 缓动函数
            
        Returns:
            self，支持链式调用
        """
        duration = duration if duration is not None else self.move_duration
        tween = tween or pyautogui.easeOutQuad
        pyautogui.moveTo(x, y, duration=duration, tween=tween)
        return self
    
    def move_relative(self, dx: int, dy: int, 
                      duration: Optional[float] = None) -> "Mouse":
        """相对移动鼠标"""
        duration = duration if duration is not None else self.move_duration
        pyautogui.moveRel(dx, dy, duration=duration)
        return self
    
    def click(self, x: Optional[int] = None, y: Optional[int] = None,
              button: MouseButton = MouseButton.LEFT,
              clicks: int = 1, interval: Optional[float] = None) -> "Mouse":
        """
        点击鼠标
        
        Args:
            x: 点击位置X坐标，None表示当前位置
            y: 点击位置Y坐标
            button: 鼠标按键
            clicks: 点击次数
            interval: 多次点击的间隔
            
        Returns:
            self
        """
        interval = interval if interval is not None else self.click_interval
        pyautogui.click(x=x, y=y, button=button.value, clicks=clicks, interval=interval)
        return self
    
    def left_click(self, x: Optional[int] = None, y: Optional[int] = None) -> "Mouse":
        """左键单击"""
        return self.click(x, y, MouseButton.LEFT)
    
    def right_click(self, x: Optional[int] = None, y: Optional[int] = None) -> "Mouse":
        """右键单击"""
        return self.click(x, y, MouseButton.RIGHT)
    
    def middle_click(self, x: Optional[int] = None, y: Optional[int] = None) -> "Mouse":
        """中键单击"""
        return self.click(x, y, MouseButton.MIDDLE)
    
    def double_click(self, x: Optional[int] = None, y: Optional[int] = None) -> "Mouse":
        """双击"""
        return self.click(x, y, MouseButton.LEFT, clicks=2)
    
    def triple_click(self, x: Optional[int] = None, y: Optional[int] = None) -> "Mouse":
        """三击（常用于选中整行）"""
        return self.click(x, y, MouseButton.LEFT, clicks=3)
    
    def drag(self, start_x: int, start_y: int, end_x: int, end_y: int,
             duration: float = 0.5, button: MouseButton = MouseButton.LEFT) -> "Mouse":
        """
        拖拽操作
        
        Args:
            start_x, start_y: 起始位置
            end_x, end_y: 结束位置
            duration: 拖拽持续时间
            button: 使用的鼠标按键
        """
        pyautogui.moveTo(start_x, start_y)
        pyautogui.drag(end_x - start_x, end_y - start_y, 
                       duration=duration, button=button.value)
        return self
    
    def drag_to(self, x: int, y: int, duration: float = 0.5,
                button: MouseButton = MouseButton.LEFT) -> "Mouse":
        """从当前位置拖拽到目标位置"""
        pyautogui.dragTo(x, y, duration=duration, button=button.value)
        return self
    
    def scroll(self, clicks: int, x: Optional[int] = None, 
               y: Optional[int] = None) -> "Mouse":
        """
        滚动鼠标滚轮
        
        Args:
            clicks: 滚动量，正数向上，负数向下
            x, y: 滚动位置
        """
        pyautogui.scroll(clicks, x=x, y=y)
        return self
    
    def scroll_up(self, clicks: int = 3) -> "Mouse":
        """向上滚动"""
        return self.scroll(clicks)
    
    def scroll_down(self, clicks: int = 3) -> "Mouse":
        """向下滚动"""
        return self.scroll(-clicks)
    
    def mouse_down(self, button: MouseButton = MouseButton.LEFT) -> "Mouse":
        """按下鼠标键"""
        pyautogui.mouseDown(button=button.value)
        return self
    
    def mouse_up(self, button: MouseButton = MouseButton.LEFT) -> "Mouse":
        """释放鼠标键"""
        pyautogui.mouseUp(button=button.value)
        return self
    
    def move_human_like(self, x: int, y: int, 
                        duration_range: Tuple[float, float] = (0.2, 0.5)) -> "Mouse":
        """
        模拟人类移动鼠标（带随机性）
        
        Args:
            x, y: 目标位置
            duration_range: 持续时间范围
        """
        duration = random.uniform(*duration_range)
        
        # 添加一些中间点
        current_x, current_y = self.position
        
        # 使用贝塞尔曲线或随机中间点
        mid_x = (current_x + x) // 2 + random.randint(-50, 50)
        mid_y = (current_y + y) // 2 + random.randint(-50, 50)
        
        pyautogui.moveTo(mid_x, mid_y, duration=duration/2, tween=pyautogui.easeInOutQuad)
        pyautogui.moveTo(x, y, duration=duration/2, tween=pyautogui.easeOutQuad)
        
        return self
    
    def click_human_like(self, x: int, y: int) -> "Mouse":
        """模拟人类点击（移动后点击，带随机延迟）"""
        self.move_human_like(x, y)
        time.sleep(random.uniform(0.05, 0.15))
        return self.left_click()
