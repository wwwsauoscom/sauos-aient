"""
自动化主类
提供统一的自动化操作接口
"""

import time
from typing import Optional, Tuple, Union, List, Callable
from PIL import Image

from .core.screen import Screen
from .core.mouse import Mouse, MouseButton
from .core.keyboard import Keyboard, Key
from .core.window import Window, WindowInfo
from .core.image import ImageMatcher, MatchResult


class Automation:
    """
    电脑自动化主类
    
    整合屏幕、鼠标、键盘、窗口操作的统一接口
    """
    
    def __init__(self, 
                 match_threshold: float = 0.8,
                 mouse_duration: float = 0.2,
                 typing_interval: float = 0.05):
        """
        初始化自动化实例
        
        Args:
            match_threshold: 图像匹配阈值
            mouse_duration: 鼠标移动默认时长
            typing_interval: 键盘输入间隔
        """
        self.screen = Screen()
        self.mouse = Mouse(move_duration=mouse_duration)
        self.keyboard = Keyboard(typing_interval=typing_interval)
        self.window = Window()
        self.image = ImageMatcher(threshold=match_threshold)
    
    # ==================== 屏幕操作 ====================
    
    def screenshot(self, region: Optional[Tuple[int, int, int, int]] = None) -> Image.Image:
        """截取屏幕"""
        return self.screen.capture(region=region)
    
    def save_screenshot(self, filepath: str, 
                       region: Optional[Tuple[int, int, int, int]] = None) -> str:
        """截图并保存"""
        return self.screen.save_screenshot(filepath, region=region)
    
    def get_screen_size(self) -> Tuple[int, int]:
        """获取屏幕尺寸"""
        return self.screen.get_screen_size()
    
    # ==================== 图像查找 ====================
    
    def find(self, template: Union[str, Image.Image],
             threshold: Optional[float] = None,
             region: Optional[Tuple[int, int, int, int]] = None) -> Optional[MatchResult]:
        """
        在屏幕上查找图像
        
        Args:
            template: 模板图像路径或PIL Image
            threshold: 匹配阈值
            region: 搜索区域
            
        Returns:
            匹配结果，未找到返回None
        """
        screenshot = self.screenshot(region)
        result = self.image.find(screenshot, template, threshold)
        
        # 如果指定了region，需要调整坐标
        if result and region:
            result.x += region[0]
            result.y += region[1]
        
        return result
    
    def find_all(self, template: Union[str, Image.Image],
                 threshold: Optional[float] = None,
                 region: Optional[Tuple[int, int, int, int]] = None,
                 max_results: int = 100) -> List[MatchResult]:
        """查找所有匹配位置"""
        screenshot = self.screenshot(region)
        results = self.image.find_all(screenshot, template, threshold, max_results)
        
        if region:
            for r in results:
                r.x += region[0]
                r.y += region[1]
        
        return results
    
    def wait_for(self, template: Union[str, Image.Image],
                 timeout: float = 10.0,
                 interval: float = 0.5,
                 threshold: Optional[float] = None) -> Optional[MatchResult]:
        """
        等待目标出现
        
        Args:
            template: 模板图像
            timeout: 超时时间（秒）
            interval: 检查间隔
            threshold: 匹配阈值
        """
        return self.image.wait_for(
            screenshot_func=self.screenshot,
            template=template,
            timeout=timeout,
            interval=interval,
            threshold=threshold
        )
    
    def wait_until_gone(self, template: Union[str, Image.Image],
                       timeout: float = 10.0,
                       interval: float = 0.5,
                       threshold: Optional[float] = None) -> bool:
        """等待目标消失"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            if not self.find(template, threshold):
                return True
            time.sleep(interval)
        return False
    
    def exists(self, template: Union[str, Image.Image],
               threshold: Optional[float] = None) -> bool:
        """检查目标是否存在"""
        return self.find(template, threshold) is not None
    
    # ==================== 点击操作 ====================
    
    def click(self, target: Union[Tuple[int, int], str, Image.Image, MatchResult],
              button: MouseButton = MouseButton.LEFT,
              clicks: int = 1) -> bool:
        """
        点击目标
        
        Args:
            target: 坐标、图像路径、PIL Image或MatchResult
            button: 鼠标按键
            clicks: 点击次数
            
        Returns:
            是否成功
        """
        x, y = self._resolve_target(target)
        if x is None:
            return False
        
        self.mouse.click(x, y, button, clicks)
        return True
    
    def left_click(self, target: Union[Tuple[int, int], str, Image.Image, MatchResult]) -> bool:
        """左键点击"""
        return self.click(target, MouseButton.LEFT)
    
    def right_click(self, target: Union[Tuple[int, int], str, Image.Image, MatchResult]) -> bool:
        """右键点击"""
        return self.click(target, MouseButton.RIGHT)
    
    def double_click(self, target: Union[Tuple[int, int], str, Image.Image, MatchResult]) -> bool:
        """双击"""
        return self.click(target, MouseButton.LEFT, clicks=2)
    
    def click_and_wait(self, target: Union[Tuple[int, int], str, Image.Image],
                       wait_for: Union[str, Image.Image],
                       timeout: float = 5.0) -> bool:
        """点击后等待目标出现"""
        if not self.click(target):
            return False
        return self.wait_for(wait_for, timeout) is not None
    
    # ==================== 输入操作 ====================
    
    def type_text(self, text: str, interval: Optional[float] = None) -> "Automation":
        """输入文本（仅支持ASCII）"""
        self.keyboard.type_text(text, interval)
        return self
    
    def write(self, text: str) -> "Automation":
        """输入文本（支持中文）"""
        self.keyboard.write(text)
        return self
    
    def press(self, key: Union[str, Key], count: int = 1) -> "Automation":
        """按键"""
        self.keyboard.press(key, presses=count)
        return self
    
    def hotkey(self, *keys: Union[str, Key]) -> "Automation":
        """组合键"""
        self.keyboard.hotkey(*keys)
        return self
    
    def enter(self) -> "Automation":
        """按回车"""
        self.keyboard.enter()
        return self
    
    def tab(self) -> "Automation":
        """按Tab"""
        self.keyboard.tab()
        return self
    
    def escape(self) -> "Automation":
        """按ESC"""
        self.keyboard.escape()
        return self
    
    # ==================== 拖拽操作 ====================
    
    def drag(self, start: Union[Tuple[int, int], str, Image.Image],
             end: Union[Tuple[int, int], str, Image.Image],
             duration: float = 0.5) -> bool:
        """拖拽操作"""
        start_x, start_y = self._resolve_target(start)
        end_x, end_y = self._resolve_target(end)
        
        if start_x is None or end_x is None:
            return False
        
        self.mouse.drag(start_x, start_y, end_x, end_y, duration)
        return True
    
    # ==================== 滚动操作 ====================
    
    def scroll(self, clicks: int, target: Optional[Union[Tuple[int, int], str, Image.Image]] = None) -> bool:
        """滚动"""
        if target:
            x, y = self._resolve_target(target)
            if x is None:
                return False
            self.mouse.scroll(clicks, x, y)
        else:
            self.mouse.scroll(clicks)
        return True
    
    def scroll_up(self, clicks: int = 3) -> "Automation":
        """向上滚动"""
        self.mouse.scroll_up(clicks)
        return self
    
    def scroll_down(self, clicks: int = 3) -> "Automation":
        """向下滚动"""
        self.mouse.scroll_down(clicks)
        return self
    
    # ==================== 窗口操作 ====================
    
    def get_active_window(self) -> Optional[WindowInfo]:
        """获取活动窗口"""
        return self.window.get_active_window()
    
    def find_window(self, title: str = None, app_name: str = None) -> List[WindowInfo]:
        """查找窗口"""
        return self.window.find_windows(title, app_name)
    
    def activate_window(self, app_name: str = None, title: str = None) -> bool:
        """激活窗口"""
        return self.window.activate(app_name, title)
    
    def activate_app(self, app_name: str) -> bool:
        """激活应用"""
        return self.window.activate(app_name=app_name)
    
    # ==================== 辅助方法 ====================
    
    def _resolve_target(self, target) -> Tuple[Optional[int], Optional[int]]:
        """解析目标为坐标"""
        if isinstance(target, tuple) and len(target) == 2:
            return target
        elif isinstance(target, MatchResult):
            return target.center
        elif isinstance(target, (str, Image.Image)):
            result = self.find(target)
            if result:
                return result.center
        return None, None
    
    def sleep(self, seconds: float) -> "Automation":
        """等待"""
        time.sleep(seconds)
        return self
    
    def wait(self, seconds: float) -> "Automation":
        """等待（sleep的别名）"""
        return self.sleep(seconds)
    
    # ==================== 快捷操作 ====================
    
    def copy(self) -> "Automation":
        """复制"""
        self.keyboard.copy()
        return self
    
    def paste(self) -> "Automation":
        """粘贴"""
        self.keyboard.paste()
        return self
    
    def cut(self) -> "Automation":
        """剪切"""
        self.keyboard.cut()
        return self
    
    def select_all(self) -> "Automation":
        """全选"""
        self.keyboard.select_all()
        return self
    
    def undo(self) -> "Automation":
        """撤销"""
        self.keyboard.undo()
        return self
    
    def save(self) -> "Automation":
        """保存"""
        self.keyboard.save()
        return self
    
    # ==================== 链式操作支持 ====================
    
    def move_to(self, target: Union[Tuple[int, int], str, Image.Image]) -> "Automation":
        """移动鼠标到目标"""
        x, y = self._resolve_target(target)
        if x is not None:
            self.mouse.move(x, y)
        return self
    
    def then_click(self, button: MouseButton = MouseButton.LEFT) -> "Automation":
        """然后点击"""
        self.mouse.click(button=button)
        return self
    
    def then_type(self, text: str) -> "Automation":
        """然后输入"""
        self.keyboard.write(text)
        return self
    
    def then_press(self, key: Union[str, Key]) -> "Automation":
        """然后按键"""
        self.keyboard.press(key)
        return self
    
    # ==================== 条件操作 ====================
    
    def if_exists(self, template: Union[str, Image.Image],
                  then_action: Callable[["Automation"], None],
                  else_action: Callable[["Automation"], None] = None) -> "Automation":
        """
        条件执行
        
        Args:
            template: 检查的目标
            then_action: 存在时执行的操作
            else_action: 不存在时执行的操作
        """
        if self.exists(template):
            then_action(self)
        elif else_action:
            else_action(self)
        return self
    
    def repeat(self, times: int, action: Callable[["Automation", int], None]) -> "Automation":
        """
        重复执行
        
        Args:
            times: 重复次数
            action: 执行的操作，接收(automation, index)参数
        """
        for i in range(times):
            action(self, i)
        return self
    
    def repeat_until(self, condition: Callable[["Automation"], bool],
                     action: Callable[["Automation"], None],
                     max_times: int = 100,
                     interval: float = 0.5) -> "Automation":
        """
        重复执行直到条件满足
        
        Args:
            condition: 条件函数
            action: 执行的操作
            max_times: 最大重复次数
            interval: 重复间隔
        """
        for _ in range(max_times):
            if condition(self):
                break
            action(self)
            time.sleep(interval)
        return self
