"""
图像识别模块
支持模板匹配、多尺度匹配、颜色识别
"""

import os
from typing import Optional, Tuple, List, Union
from dataclasses import dataclass

import numpy as np
from PIL import Image

try:
    import cv2
except ImportError:
    cv2 = None


@dataclass
class MatchResult:
    """匹配结果"""
    x: int
    y: int
    width: int
    height: int
    confidence: float
    
    @property
    def center(self) -> Tuple[int, int]:
        """返回中心点坐标"""
        return (self.x + self.width // 2, self.y + self.height // 2)
    
    @property
    def region(self) -> Tuple[int, int, int, int]:
        """返回区域 (x, y, width, height)"""
        return (self.x, self.y, self.width, self.height)


class ImageMatcher:
    """图像匹配器"""
    
    def __init__(self, threshold: float = 0.8):
        """
        Args:
            threshold: 默认匹配阈值 (0-1)
        """
        if cv2 is None:
            raise ImportError("请安装opencv-python: pip install opencv-python")
        self.threshold = threshold
    
    def _to_cv2(self, image: Union[Image.Image, np.ndarray, str]) -> np.ndarray:
        """将图像转换为OpenCV格式"""
        if isinstance(image, str):
            if not os.path.exists(image):
                raise FileNotFoundError(f"图像文件不存在: {image}")
            return cv2.imread(image)
        elif isinstance(image, Image.Image):
            return cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        elif isinstance(image, np.ndarray):
            return image
        else:
            raise TypeError(f"不支持的图像类型: {type(image)}")
    
    def find(self, screenshot: Union[Image.Image, np.ndarray, str],
             template: Union[Image.Image, np.ndarray, str],
             threshold: Optional[float] = None,
             method: Optional[int] = None) -> Optional[MatchResult]:
        """
        在截图中查找模板图像
        
        Args:
            screenshot: 屏幕截图
            template: 模板图像
            threshold: 匹配阈值，None使用默认值
            method: OpenCV模板匹配方法
            
        Returns:
            匹配结果，未找到返回None
        """
        threshold = threshold or self.threshold
        if method is None:
            method = cv2.TM_CCOEFF_NORMED
        
        screen_img = self._to_cv2(screenshot)
        template_img = self._to_cv2(template)
        
        # 转为灰度图
        screen_gray = cv2.cvtColor(screen_img, cv2.COLOR_BGR2GRAY)
        template_gray = cv2.cvtColor(template_img, cv2.COLOR_BGR2GRAY)
        
        h, w = template_gray.shape
        
        # 模板匹配
        result = cv2.matchTemplate(screen_gray, template_gray, method)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
        
        # 对于TM_SQDIFF和TM_SQDIFF_NORMED，最小值是最佳匹配
        if method in [cv2.TM_SQDIFF, cv2.TM_SQDIFF_NORMED]:
            confidence = 1 - min_val
            location = min_loc
        else:
            confidence = max_val
            location = max_loc
        
        if confidence >= threshold:
            return MatchResult(
                x=location[0],
                y=location[1],
                width=w,
                height=h,
                confidence=confidence
            )
        return None
    
    def find_all(self, screenshot: Union[Image.Image, np.ndarray, str],
                 template: Union[Image.Image, np.ndarray, str],
                 threshold: Optional[float] = None,
                 max_results: int = 100) -> List[MatchResult]:
        """
        查找所有匹配的位置
        
        Args:
            screenshot: 屏幕截图
            template: 模板图像
            threshold: 匹配阈值
            max_results: 最大结果数量
            
        Returns:
            匹配结果列表
        """
        threshold = threshold or self.threshold
        
        screen_img = self._to_cv2(screenshot)
        template_img = self._to_cv2(template)
        
        screen_gray = cv2.cvtColor(screen_img, cv2.COLOR_BGR2GRAY)
        template_gray = cv2.cvtColor(template_img, cv2.COLOR_BGR2GRAY)
        
        h, w = template_gray.shape
        
        result = cv2.matchTemplate(screen_gray, template_gray, cv2.TM_CCOEFF_NORMED)
        locations = np.where(result >= threshold)
        
        matches = []
        for pt in zip(*locations[::-1]):
            confidence = result[pt[1], pt[0]]
            matches.append(MatchResult(
                x=pt[0],
                y=pt[1],
                width=w,
                height=h,
                confidence=float(confidence)
            ))
        
        # 非极大值抑制，去除重叠结果
        matches = self._nms(matches, overlap_threshold=0.5)
        
        # 按置信度排序
        matches.sort(key=lambda m: m.confidence, reverse=True)
        
        return matches[:max_results]
    
    def find_multiscale(self, screenshot: Union[Image.Image, np.ndarray, str],
                        template: Union[Image.Image, np.ndarray, str],
                        scales: List[float] = None,
                        threshold: Optional[float] = None) -> Optional[MatchResult]:
        """
        多尺度匹配，支持不同大小的目标
        
        Args:
            screenshot: 屏幕截图
            template: 模板图像
            scales: 缩放比例列表，默认[0.5, 0.75, 1.0, 1.25, 1.5]
            threshold: 匹配阈值
            
        Returns:
            最佳匹配结果
        """
        if scales is None:
            scales = [0.5, 0.75, 1.0, 1.25, 1.5]
        
        threshold = threshold or self.threshold
        template_img = self._to_cv2(template)
        
        best_match = None
        best_confidence = 0
        
        for scale in scales:
            # 缩放模板
            new_width = int(template_img.shape[1] * scale)
            new_height = int(template_img.shape[0] * scale)
            if new_width < 1 or new_height < 1:
                continue
            
            scaled_template = cv2.resize(template_img, (new_width, new_height))
            
            match = self.find(screenshot, scaled_template, threshold)
            if match and match.confidence > best_confidence:
                best_match = match
                best_confidence = match.confidence
        
        return best_match
    
    def find_color(self, screenshot: Union[Image.Image, np.ndarray, str],
                   color: Tuple[int, int, int],
                   tolerance: int = 10) -> List[Tuple[int, int]]:
        """
        查找指定颜色的像素位置
        
        Args:
            screenshot: 屏幕截图
            color: RGB颜色值
            tolerance: 颜色容差
            
        Returns:
            匹配像素坐标列表
        """
        screen_img = self._to_cv2(screenshot)
        screen_rgb = cv2.cvtColor(screen_img, cv2.COLOR_BGR2RGB)
        
        lower = np.array([max(0, c - tolerance) for c in color])
        upper = np.array([min(255, c + tolerance) for c in color])
        
        mask = cv2.inRange(screen_rgb, lower, upper)
        locations = np.where(mask > 0)
        
        return list(zip(locations[1], locations[0]))
    
    def _nms(self, matches: List[MatchResult], 
             overlap_threshold: float = 0.5) -> List[MatchResult]:
        """非极大值抑制"""
        if not matches:
            return []
        
        # 按置信度排序
        matches = sorted(matches, key=lambda m: m.confidence, reverse=True)
        
        keep = []
        while matches:
            current = matches.pop(0)
            keep.append(current)
            
            matches = [m for m in matches 
                      if self._iou(current, m) < overlap_threshold]
        
        return keep
    
    def _iou(self, m1: MatchResult, m2: MatchResult) -> float:
        """计算两个区域的IoU"""
        x1 = max(m1.x, m2.x)
        y1 = max(m1.y, m2.y)
        x2 = min(m1.x + m1.width, m2.x + m2.width)
        y2 = min(m1.y + m1.height, m2.y + m2.height)
        
        if x2 <= x1 or y2 <= y1:
            return 0.0
        
        intersection = (x2 - x1) * (y2 - y1)
        area1 = m1.width * m1.height
        area2 = m2.width * m2.height
        union = area1 + area2 - intersection
        
        return intersection / union if union > 0 else 0.0
    
    def wait_for(self, screenshot_func, template: Union[Image.Image, np.ndarray, str],
                 timeout: float = 10.0, interval: float = 0.5,
                 threshold: Optional[float] = None) -> Optional[MatchResult]:
        """
        等待目标出现
        
        Args:
            screenshot_func: 截图函数
            template: 模板图像
            timeout: 超时时间（秒）
            interval: 检查间隔（秒）
            threshold: 匹配阈值
            
        Returns:
            匹配结果，超时返回None
        """
        import time
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            screenshot = screenshot_func()
            match = self.find(screenshot, template, threshold)
            if match:
                return match
            time.sleep(interval)
        
        return None
