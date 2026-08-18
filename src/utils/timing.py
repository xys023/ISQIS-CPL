"""
帧率统计工具
"""
import time
from collections import deque


class FPSCounter:
    """滑动窗口帧率计数器"""

    def __init__(self, window_size=100):
        self.window_size = window_size
        self.timestamps = deque(maxlen=window_size)

    def tick(self):
        """记录一帧"""
        self.timestamps.append(time.time())

    @property
    def fps(self):
        """获取当前平均帧率"""
        if len(self.timestamps) < 2:
            return 0.0
        delta = self.timestamps[-1] - self.timestamps[0]
        if delta <= 0:
            return 0.0
        return (len(self.timestamps) - 1) / delta
