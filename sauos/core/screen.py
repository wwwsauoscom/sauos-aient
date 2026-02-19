"""
屏幕截图模块
支持全屏截图、区域截图、多显示器截图
"""

import io
import sys
from typing import Optional, Tuple, List
from PIL import Image

try:
    import mss
    import mss.tools
except ImportError:
    mss = None


class Screen:
    """屏幕截图类"""
    
    def __init__(self):
        self._sct = None
    
    @property
    def sct(self):
        """懒加载mss实例"""
        if self._sct is None:
            if mss is None:
                raise ImportError("请安装mss库: pip install mss")
            self._sct = mss.mss()
        return self._sct
    
    def capture(self, region: Optional[Tuple[int, int, int, int]] = None, 
                monitor: int = 0) -> Image.Image:
        """
        截取屏幕
        
        Args:
            region: 截图区域 (x, y, width, height)，None表示全屏
            monitor: 显示器索引，0表示所有显示器，1表示第一个显示器
            
        Returns:
            PIL.Image对象
        """
        if region:
            x, y, width, height = region
            monitor_info = {"left": x, "top": y, "width": width, "height": height}
        else:
            monitor_info = self.sct.monitors[monitor]
        
        screenshot = self.sct.grab(monitor_info)
        return Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")
    
    def capture_full(self) -> Image.Image:
        """截取全部显示器"""
        return self.capture(monitor=0)
    
    def capture_primary(self) -> Image.Image:
        """截取主显示器"""
        return self.capture(monitor=1)
    
    def capture_region(self, x: int, y: int, width: int, height: int) -> Image.Image:
        """截取指定区域"""
        return self.capture(region=(x, y, width, height))
    
    def get_monitors(self) -> List[dict]:
        """获取所有显示器信息"""
        return self.sct.monitors
    
    def get_screen_size(self, monitor: int = 1) -> Tuple[int, int]:
        """获取屏幕尺寸"""
        mon = self.sct.monitors[monitor]
        return mon["width"], mon["height"]
    
    def save_screenshot(self, filepath: str, 
                       region: Optional[Tuple[int, int, int, int]] = None,
                       monitor: int = 1) -> str:
        """
        截图并保存到文件
        
        Args:
            filepath: 保存路径
            region: 截图区域
            monitor: 显示器索引
            
        Returns:
            保存的文件路径
        """
        img = self.capture(region=region, monitor=monitor)
        img.save(filepath)
        return filepath
    
    def to_bytes(self, image: Image.Image, format: str = "PNG") -> bytes:
        """将图像转换为字节"""
        buffer = io.BytesIO()
        image.save(buffer, format=format)
        return buffer.getvalue()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._sct:
            self._sct.close()
