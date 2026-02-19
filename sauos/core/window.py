"""
窗口管理模块
支持窗口查找、激活、移动、调整大小等操作
"""

import sys
import subprocess
from typing import Optional, List, Tuple
from dataclasses import dataclass


@dataclass
class WindowInfo:
    """窗口信息"""
    title: str
    app_name: str
    pid: int
    x: int
    y: int
    width: int
    height: int
    is_visible: bool = True
    
    @property
    def bounds(self) -> Tuple[int, int, int, int]:
        """返回窗口边界 (x, y, width, height)"""
        return (self.x, self.y, self.width, self.height)
    
    @property
    def center(self) -> Tuple[int, int]:
        """返回窗口中心点"""
        return (self.x + self.width // 2, self.y + self.height // 2)


class Window:
    """窗口管理类"""
    
    def __init__(self):
        self._platform = sys.platform
    
    def get_active_window(self) -> Optional[WindowInfo]:
        """获取当前活动窗口"""
        if self._platform == "darwin":
            return self._get_active_window_macos()
        elif self._platform == "win32":
            return self._get_active_window_windows()
        else:
            return self._get_active_window_linux()
    
    def _get_active_window_macos(self) -> Optional[WindowInfo]:
        """macOS获取活动窗口"""
        try:
            script = '''
            tell application "System Events"
                set frontApp to first application process whose frontmost is true
                set appName to name of frontApp
                set appPID to unix id of frontApp
                try
                    set frontWindow to first window of frontApp
                    set windowTitle to name of frontWindow
                    set windowBounds to position of frontWindow & size of frontWindow
                on error
                    set windowTitle to ""
                    set windowBounds to {0, 0, 0, 0}
                end try
            end tell
            return appName & "|" & appPID & "|" & windowTitle & "|" & (item 1 of windowBounds) & "|" & (item 2 of windowBounds) & "|" & (item 3 of windowBounds) & "|" & (item 4 of windowBounds)
            '''
            result = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                parts = result.stdout.strip().split("|")
                if len(parts) >= 7:
                    return WindowInfo(
                        title=parts[2],
                        app_name=parts[0],
                        pid=int(parts[1]),
                        x=int(parts[3]),
                        y=int(parts[4]),
                        width=int(parts[5]),
                        height=int(parts[6])
                    )
        except Exception:
            pass
        return None
    
    def _get_active_window_windows(self) -> Optional[WindowInfo]:
        """Windows获取活动窗口"""
        try:
            import ctypes
            from ctypes import wintypes
            
            user32 = ctypes.windll.user32
            hwnd = user32.GetForegroundWindow()
            
            # 获取窗口标题
            length = user32.GetWindowTextLengthW(hwnd)
            buff = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buff, length + 1)
            title = buff.value
            
            # 获取进程ID
            pid = wintypes.DWORD()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            
            # 获取窗口位置和大小
            rect = wintypes.RECT()
            user32.GetWindowRect(hwnd, ctypes.byref(rect))
            
            return WindowInfo(
                title=title,
                app_name="",
                pid=pid.value,
                x=rect.left,
                y=rect.top,
                width=rect.right - rect.left,
                height=rect.bottom - rect.top
            )
        except Exception:
            pass
        return None
    
    def _get_active_window_linux(self) -> Optional[WindowInfo]:
        """Linux获取活动窗口"""
        try:
            # 使用xdotool
            result = subprocess.run(
                ["xdotool", "getactivewindow"],
                capture_output=True,
                text=True
            )
            if result.returncode != 0:
                return None
            
            window_id = result.stdout.strip()
            
            # 获取窗口信息
            name_result = subprocess.run(
                ["xdotool", "getwindowname", window_id],
                capture_output=True,
                text=True
            )
            
            geom_result = subprocess.run(
                ["xdotool", "getwindowgeometry", "--shell", window_id],
                capture_output=True,
                text=True
            )
            
            pid_result = subprocess.run(
                ["xdotool", "getwindowpid", window_id],
                capture_output=True,
                text=True
            )
            
            # 解析geometry
            geom = {}
            for line in geom_result.stdout.strip().split("\n"):
                if "=" in line:
                    key, value = line.split("=")
                    geom[key] = int(value)
            
            return WindowInfo(
                title=name_result.stdout.strip(),
                app_name="",
                pid=int(pid_result.stdout.strip()) if pid_result.returncode == 0 else 0,
                x=geom.get("X", 0),
                y=geom.get("Y", 0),
                width=geom.get("WIDTH", 0),
                height=geom.get("HEIGHT", 0)
            )
        except Exception:
            pass
        return None
    
    def find_windows(self, title: str = None, app_name: str = None) -> List[WindowInfo]:
        """
        查找窗口
        
        Args:
            title: 窗口标题（支持部分匹配）
            app_name: 应用名称
        """
        if self._platform == "darwin":
            return self._find_windows_macos(title, app_name)
        return []
    
    def _find_windows_macos(self, title: str = None, 
                            app_name: str = None) -> List[WindowInfo]:
        """macOS查找窗口"""
        windows = []
        try:
            script = '''
            set windowList to ""
            tell application "System Events"
                repeat with proc in (every application process whose visible is true)
                    set appName to name of proc
                    set appPID to unix id of proc
                    try
                        repeat with win in (every window of proc)
                            set winName to name of win
                            set winPos to position of win
                            set winSize to size of win
                            set windowList to windowList & appName & "|" & appPID & "|" & winName & "|" & (item 1 of winPos) & "|" & (item 2 of winPos) & "|" & (item 1 of winSize) & "|" & (item 2 of winSize) & "\\n"
                        end repeat
                    end try
                end repeat
            end tell
            return windowList
            '''
            result = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                for line in result.stdout.strip().split("\n"):
                    if not line:
                        continue
                    parts = line.split("|")
                    if len(parts) >= 7:
                        win = WindowInfo(
                            title=parts[2],
                            app_name=parts[0],
                            pid=int(parts[1]),
                            x=int(parts[3]),
                            y=int(parts[4]),
                            width=int(parts[5]),
                            height=int(parts[6])
                        )
                        
                        # 过滤
                        if title and title.lower() not in win.title.lower():
                            continue
                        if app_name and app_name.lower() not in win.app_name.lower():
                            continue
                        
                        windows.append(win)
        except Exception:
            pass
        
        return windows
    
    def activate(self, app_name: str = None, title: str = None) -> bool:
        """
        激活窗口
        
        Args:
            app_name: 应用名称
            title: 窗口标题
        """
        if self._platform == "darwin":
            return self._activate_macos(app_name, title)
        elif self._platform == "win32":
            return self._activate_windows(title)
        else:
            return self._activate_linux(title)
    
    def _activate_macos(self, app_name: str = None, title: str = None) -> bool:
        """macOS激活窗口"""
        try:
            if app_name:
                script = f'tell application "{app_name}" to activate'
                result = subprocess.run(["osascript", "-e", script], capture_output=True)
                return result.returncode == 0
        except Exception:
            pass
        return False
    
    def _activate_windows(self, title: str = None) -> bool:
        """Windows激活窗口"""
        try:
            import ctypes
            user32 = ctypes.windll.user32
            
            def callback(hwnd, lparam):
                if user32.IsWindowVisible(hwnd):
                    length = user32.GetWindowTextLengthW(hwnd)
                    buff = ctypes.create_unicode_buffer(length + 1)
                    user32.GetWindowTextW(hwnd, buff, length + 1)
                    if title and title.lower() in buff.value.lower():
                        user32.SetForegroundWindow(hwnd)
                        return False
                return True
            
            WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
            user32.EnumWindows(WNDENUMPROC(callback), 0)
            return True
        except Exception:
            pass
        return False
    
    def _activate_linux(self, title: str = None) -> bool:
        """Linux激活窗口"""
        try:
            if title:
                result = subprocess.run(
                    ["xdotool", "search", "--name", title, "windowactivate"],
                    capture_output=True
                )
                return result.returncode == 0
        except Exception:
            pass
        return False
    
    def move(self, x: int, y: int, app_name: str = None) -> bool:
        """移动窗口"""
        if self._platform == "darwin":
            try:
                if app_name:
                    script = f'''
                    tell application "System Events"
                        tell process "{app_name}"
                            set position of window 1 to {{{x}, {y}}}
                        end tell
                    end tell
                    '''
                    result = subprocess.run(["osascript", "-e", script], capture_output=True)
                    return result.returncode == 0
            except Exception:
                pass
        return False
    
    def resize(self, width: int, height: int, app_name: str = None) -> bool:
        """调整窗口大小"""
        if self._platform == "darwin":
            try:
                if app_name:
                    script = f'''
                    tell application "System Events"
                        tell process "{app_name}"
                            set size of window 1 to {{{width}, {height}}}
                        end tell
                    end tell
                    '''
                    result = subprocess.run(["osascript", "-e", script], capture_output=True)
                    return result.returncode == 0
            except Exception:
                pass
        return False
    
    def minimize(self, app_name: str = None) -> bool:
        """最小化窗口"""
        if self._platform == "darwin" and app_name:
            try:
                script = f'''
                tell application "System Events"
                    tell process "{app_name}"
                        set value of attribute "AXMinimized" of window 1 to true
                    end tell
                end tell
                '''
                result = subprocess.run(["osascript", "-e", script], capture_output=True)
                return result.returncode == 0
            except Exception:
                pass
        return False
    
    def maximize(self, app_name: str = None) -> bool:
        """最大化窗口"""
        if self._platform == "darwin" and app_name:
            try:
                script = f'''
                tell application "System Events"
                    tell process "{app_name}"
                        set value of attribute "AXFullScreen" of window 1 to true
                    end tell
                end tell
                '''
                result = subprocess.run(["osascript", "-e", script], capture_output=True)
                return result.returncode == 0
            except Exception:
                pass
        return False
    
    def close(self, app_name: str = None) -> bool:
        """关闭窗口"""
        if self._platform == "darwin" and app_name:
            try:
                script = f'''
                tell application "System Events"
                    tell process "{app_name}"
                        click button 1 of window 1
                    end tell
                end tell
                '''
                result = subprocess.run(["osascript", "-e", script], capture_output=True)
                return result.returncode == 0
            except Exception:
                pass
        return False
