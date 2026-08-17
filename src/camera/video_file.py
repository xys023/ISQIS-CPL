"""
视频文件输入模块
用于无摄像头环境下的演示和测试，循环播放视频文件。
"""
import cv2
import numpy as np
from .base import BaseCamera


class VideoFileCamera(BaseCamera):
    """视频文件摄像头（循环播放，用于演示）"""

    def __init__(self, config):
        super().__init__(config)
        self._cap = None
        # device 字段填视频文件路径
        self._video_path = config.get("camera.device", "demo.mp4")
        self._loop = True

    def open(self):
        import os
        if not os.path.exists(self._video_path):
            raise FileNotFoundError(f"视频文件不存在: {self._video_path}")
        self._cap = cv2.VideoCapture(self._video_path)
        if not self._cap.isOpened():
            raise RuntimeError(f"无法打开视频文件: {self._video_path}")
        # 读取视频实际参数
        self.width = int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.height = int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    def close(self):
        if self._cap is not None:
            self._cap.release()
            self._cap = None

    def read(self):
        if self._cap is None or not self._cap.isOpened():
            return False, None
        success, frame = self._cap.read()
        if not success or frame is None:
            if self._loop:
                # 循环播放：回到开头
                self._cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                success, frame = self._cap.read()
                if not success:
                    return False, None
            else:
                return False, None
        self.set_frame(frame)
        return True, frame
