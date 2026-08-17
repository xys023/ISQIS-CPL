"""
摄像头基类
定义统一的摄像头接口，所有摄像头实现必须继承此类。
"""
import time
import threading
from abc import ABC, abstractmethod


class BaseCamera(ABC):
    """摄像头抽象基类"""

    def __init__(self, config):
        self.config = config
        self.width = config.get("camera.width", 1280)
        self.height = config.get("camera.height", 720)
        self.fps = config.get("camera.fps", 30)
        self.rotation = config.get("camera.rotation", 0)
        self._running = False
        self._frame = None
        self._frame_lock = threading.Lock()
        self._last_frame_time = 0
        self._frame_count = 0
        self._actual_fps = 0.0

    @abstractmethod
    def open(self):
        """打开摄像头/视频源"""
        pass

    @abstractmethod
    def close(self):
        """关闭摄像头/视频源"""
        pass

    @abstractmethod
    def read(self):
        """
        读取一帧图像
        返回: (success: bool, frame: numpy.ndarray or None)
        """
        pass

    def start(self):
        """启动摄像头（默认同步模式，子类可覆盖为异步采集）"""
        self.open()
        self._running = True

    def stop(self):
        """停止摄像头"""
        self._running = False
        self.close()

    def get_frame(self):
        """获取最新一帧（线程安全）"""
        with self._frame_lock:
            return self._frame

    def set_frame(self, frame):
        """设置最新一帧（线程安全）"""
        with self._frame_lock:
            self._frame = frame
            self._frame_count += 1
            now = time.time()
            if self._last_frame_time > 0:
                delta = now - self._last_frame_time
                if delta > 0:
                    # 平滑计算实际帧率
                    instant_fps = 1.0 / delta
                    self._actual_fps = self._actual_fps * 0.9 + instant_fps * 0.1
            self._last_frame_time = now

    @property
    def actual_fps(self):
        return self._actual_fps

    @property
    def is_running(self):
        return self._running

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()
