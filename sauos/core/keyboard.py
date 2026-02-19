"""
键盘控制模块
支持按键、组合键、文本输入
"""

import time
from typing import List, Optional, Union
from enum import Enum

try:
    import pyautogui
except ImportError:
    pyautogui = None


class Key(Enum):
    """常用按键枚举"""
    # 功能键
    ENTER = "enter"
    RETURN = "return"
    TAB = "tab"
    SPACE = "space"
    BACKSPACE = "backspace"
    DELETE = "delete"
    ESCAPE = "escape"
    ESC = "esc"
    
    # 方向键
    UP = "up"
    DOWN = "down"
    LEFT = "left"
    RIGHT = "right"
    
    # 修饰键
    SHIFT = "shift"
    CTRL = "ctrl"
    CONTROL = "ctrl"
    ALT = "alt"
    OPTION = "option"
    COMMAND = "command"
    CMD = "command"
    WIN = "win"
    
    # 功能键F1-F12
    F1 = "f1"
    F2 = "f2"
    F3 = "f3"
    F4 = "f4"
    F5 = "f5"
    F6 = "f6"
    F7 = "f7"
    F8 = "f8"
    F9 = "f9"
    F10 = "f10"
    F11 = "f11"
    F12 = "f12"
    
    # 其他
    HOME = "home"
    END = "end"
    PAGEUP = "pageup"
    PAGEDOWN = "pagedown"
    INSERT = "insert"
    CAPSLOCK = "capslock"
    NUMLOCK = "numlock"
    PRINTSCREEN = "printscreen"


class Keyboard:
    """键盘控制类"""
    
    def __init__(self, typing_interval: float = 0.05):
        """
        Args:
            typing_interval: 打字间隔
        """
        if pyautogui is None:
            raise ImportError("请安装pyautogui: pip install pyautogui")
        
        self.typing_interval = typing_interval
    
    def press(self, key: Union[str, Key], presses: int = 1, 
              interval: float = 0.1) -> "Keyboard":
        """
        按下并释放按键
        
        Args:
            key: 按键
            presses: 按键次数
            interval: 多次按键的间隔
        """
        key_name = key.value if isinstance(key, Key) else key
        pyautogui.press(key_name, presses=presses, interval=interval)
        return self
    
    def key_down(self, key: Union[str, Key]) -> "Keyboard":
        """按下按键（不释放）"""
        key_name = key.value if isinstance(key, Key) else key
        pyautogui.keyDown(key_name)
        return self
    
    def key_up(self, key: Union[str, Key]) -> "Keyboard":
        """释放按键"""
        key_name = key.value if isinstance(key, Key) else key
        pyautogui.keyUp(key_name)
        return self
    
    def hotkey(self, *keys: Union[str, Key]) -> "Keyboard":
        """
        按下组合键
        
        Args:
            keys: 按键列表，如 hotkey('ctrl', 'c')
        """
        key_names = [k.value if isinstance(k, Key) else k for k in keys]
        pyautogui.hotkey(*key_names)
        return self
    
    def type_text(self, text: str, interval: Optional[float] = None) -> "Keyboard":
        """
        输入文本
        
        Args:
            text: 要输入的文本
            interval: 字符间隔
        """
        interval = interval if interval is not None else self.typing_interval
        pyautogui.typewrite(text, interval=interval)
        return self
    
    def write(self, text: str, interval: Optional[float] = None) -> "Keyboard":
        """
        输入文本（支持中文和特殊字符）
        使用剪贴板方式
        
        Args:
            text: 要输入的文本
            interval: 字符间隔（仅用于ASCII）
        """
        # 检查是否包含非ASCII字符
        try:
            text.encode('ascii')
            # 纯ASCII，使用typewrite
            return self.type_text(text, interval)
        except UnicodeEncodeError:
            # 包含非ASCII字符，使用剪贴板
            import pyperclip
            pyperclip.copy(text)
            self.hotkey('command', 'v')  # macOS
            return self
    
    # 常用快捷键
    def copy(self) -> "Keyboard":
        """复制 (Cmd+C / Ctrl+C)"""
        import sys
        if sys.platform == "darwin":
            return self.hotkey("command", "c")
        return self.hotkey("ctrl", "c")
    
    def paste(self) -> "Keyboard":
        """粘贴 (Cmd+V / Ctrl+V)"""
        import sys
        if sys.platform == "darwin":
            return self.hotkey("command", "v")
        return self.hotkey("ctrl", "v")
    
    def cut(self) -> "Keyboard":
        """剪切 (Cmd+X / Ctrl+X)"""
        import sys
        if sys.platform == "darwin":
            return self.hotkey("command", "x")
        return self.hotkey("ctrl", "x")
    
    def undo(self) -> "Keyboard":
        """撤销 (Cmd+Z / Ctrl+Z)"""
        import sys
        if sys.platform == "darwin":
            return self.hotkey("command", "z")
        return self.hotkey("ctrl", "z")
    
    def redo(self) -> "Keyboard":
        """重做 (Cmd+Shift+Z / Ctrl+Y)"""
        import sys
        if sys.platform == "darwin":
            return self.hotkey("command", "shift", "z")
        return self.hotkey("ctrl", "y")
    
    def select_all(self) -> "Keyboard":
        """全选 (Cmd+A / Ctrl+A)"""
        import sys
        if sys.platform == "darwin":
            return self.hotkey("command", "a")
        return self.hotkey("ctrl", "a")
    
    def save(self) -> "Keyboard":
        """保存 (Cmd+S / Ctrl+S)"""
        import sys
        if sys.platform == "darwin":
            return self.hotkey("command", "s")
        return self.hotkey("ctrl", "s")
    
    def new_tab(self) -> "Keyboard":
        """新建标签页"""
        import sys
        if sys.platform == "darwin":
            return self.hotkey("command", "t")
        return self.hotkey("ctrl", "t")
    
    def close_tab(self) -> "Keyboard":
        """关闭标签页"""
        import sys
        if sys.platform == "darwin":
            return self.hotkey("command", "w")
        return self.hotkey("ctrl", "w")
    
    def switch_tab(self) -> "Keyboard":
        """切换标签页"""
        import sys
        if sys.platform == "darwin":
            return self.hotkey("command", "tab")
        return self.hotkey("alt", "tab")
    
    def enter(self) -> "Keyboard":
        """按回车键"""
        return self.press(Key.ENTER)
    
    def tab(self) -> "Keyboard":
        """按Tab键"""
        return self.press(Key.TAB)
    
    def escape(self) -> "Keyboard":
        """按Esc键"""
        return self.press(Key.ESCAPE)
    
    def backspace(self, count: int = 1) -> "Keyboard":
        """按退格键"""
        return self.press(Key.BACKSPACE, presses=count)
    
    def delete(self, count: int = 1) -> "Keyboard":
        """按删除键"""
        return self.press(Key.DELETE, presses=count)
    
    def arrow_up(self, count: int = 1) -> "Keyboard":
        """按上方向键"""
        return self.press(Key.UP, presses=count)
    
    def arrow_down(self, count: int = 1) -> "Keyboard":
        """按下方向键"""
        return self.press(Key.DOWN, presses=count)
    
    def arrow_left(self, count: int = 1) -> "Keyboard":
        """按左方向键"""
        return self.press(Key.LEFT, presses=count)
    
    def arrow_right(self, count: int = 1) -> "Keyboard":
        """按右方向键"""
        return self.press(Key.RIGHT, presses=count)
