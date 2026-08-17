from .base import BaseCamera
from .webcam import WebCamera
from .gstreamer import GStreamerCamera
from .video_file import VideoFileCamera

__all__ = ["BaseCamera", "WebCamera", "GStreamerCamera", "VideoFileCamera", "create_camera"]


def create_camera(config):
    """
    工厂方法：根据配置创建对应的摄像头实例

    参数:
        config: ConfigManager 实例或配置字典
    返回:
        BaseCamera 子类实例
    """
    source_type = config.get("camera.source_type", "webcam")

    if source_type == "webcam":
        return WebCamera(config)
    elif source_type == "gstreamer":
        return GStreamerCamera(config)
    elif source_type == "video":
        return VideoFileCamera(config)
    else:
        raise ValueError(f"不支持的摄像头类型: {source_type}")
