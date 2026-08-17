"""
RK3588 GStreamer 硬解码摄像头模块
使用 GStreamer 管道实现 MIPI CSI 摄像头或 USB 摄像头的硬件加速采集。
仅在 RK3588/RK3572 硬件上使用，x86 笔记本请使用 WebCamera。
"""
import cv2
import numpy as np
from .base import BaseCamera


class GStreamerCamera(BaseCamera):
    """GStreamer 管道摄像头（RK3588 硬件加速）"""

    def __init__(self, config):
        super().__init__(config)
        self._cap = None
        self._pipeline = config.get(
            "camera.gstreamer_pipe",
            "v4l2src device=/dev/video0 ! video/x-raw,width=1280,height=720,framerate=30/1 ! videoconvert ! appsink"
        )

    def open(self):
        """通过 GStreamer 管道打开摄像头"""
        self._cap = cv2.VideoCapture(self._pipeline, cv2.CAP_GSTREAMER)
        if not self._cap.isOpened():
            raise RuntimeError(
                f"GStreamer 管道打开失败，请确认:\n"
                f"1. 已安装 gstreamer1.0 相关插件\n"
                f"2. 摄像头设备 /dev/video0 存在\n"
                f"3. 管道: {self._pipeline}"
            )

    def close(self):
        if self._cap is not None:
            self._cap.release()
            self._cap = None

    def read(self):
        if self._cap is None or not self._cap.isOpened():
            return False, None
        success, frame = self._cap.read()
        if not success or frame is None:
            return False, None
        self.set_frame(frame)
        return True, frame
