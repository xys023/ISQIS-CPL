"""
USB 摄像头 / 笔记本摄像头采集模块
基于 OpenCV VideoCapture，支持 UVC 免驱摄像头。
适用于笔记本演示环境和 USB 工业相机。
"""
import cv2
import numpy as np
from .base import BaseCamera


class WebCamera(BaseCamera):
    """USB/笔记本摄像头"""

    def __init__(self, config):
        super().__init__(config)
        self._cap = None
        self._device = config.get("camera.device", 0)

    def open(self):
        """打开摄像头"""
        # 优先使用 DirectShow（Windows），Linux/Mac 自动降级
        if isinstance(self._device, int):
            self._cap = cv2.VideoCapture(self._device, cv2.CAP_DSHOW)
            if not self._cap.isOpened():
                # 回退到默认后端
                self._cap = cv2.VideoCapture(self._device)
        else:
            # 设备路径或视频文件
            self._cap = cv2.VideoCapture(self._device)

        if not self._cap.isOpened():
            raise RuntimeError(f"无法打开摄像头: {self._device}")

        # 设置分辨率
        self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        self._cap.set(cv2.CAP_PROP_FPS, self.fps)

        # 自动曝光设置
        auto_exp = self.config.get("camera.auto_exposure", 1)
        self._cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, auto_exp)
        if auto_exp == 0:
            self._cap.set(cv2.CAP_PROP_EXPOSURE, self.config.get("camera.exposure", 20))

        # 读取实际分辨率（摄像头可能不支持设定值）
        actual_w = int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        actual_h = int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        if actual_w > 0 and actual_h > 0:
            self.width, self.height = actual_w, actual_h

    def close(self):
        """关闭摄像头"""
        if self._cap is not None:
            self._cap.release()
            self._cap = None

    def read(self):
        """读取一帧"""
        if self._cap is None or not self._cap.isOpened():
            return False, None

        success, frame = self._cap.read()
        if not success or frame is None:
            return False, None

        # 旋转处理
        frame = self._rotate(frame)
        self.set_frame(frame)
        return True, frame

    def _rotate(self, frame):
        """按配置旋转图像"""
        if self.rotation == 90:
            return cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)
        elif self.rotation == 180:
            return cv2.rotate(frame, cv2.ROTATE_180)
        elif self.rotation == 270:
            return cv2.rotate(frame, cv2.ROTATE_90_COUNTERCLOCKWISE)
        return frame
