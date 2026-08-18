"""
检测器基类
定义统一的检测接口和数据结构。
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Tuple
import time


@dataclass
class DefectItem:
    """单个缺陷/检测目标"""
    label: str                    # 缺陷类别名称，如 "foreign_object"、"broken"
    label_cn: str                 # 中文名称，如 "异物"、"破损"
    confidence: float             # 置信度 0~1
    bbox: Tuple[int, int, int, int]  # 边界框 (x1, y1, x2, y2)
    area: int = 0                 # 缺陷区域面积（像素）
    extra: dict = field(default_factory=dict)  # 额外信息


@dataclass
class DetectionResult:
    """一帧图像的检测结果"""
    timestamp: float              # 时间戳
    is_defective: bool            # 是否判定为不合格
    defects: List[DefectItem]     # 检测到的缺陷列表
    fps: float = 0.0              # 检测帧率
    inference_time: float = 0.0   # 推理耗时（毫秒）
    frame_width: int = 0
    frame_height: int = 0

    def to_dict(self):
        """转为字典（用于JSON序列化）"""
        return {
            "timestamp": self.timestamp,
            "is_defective": self.is_defective,
            "defects": [
                {
                    "label": d.label,
                    "label_cn": d.label_cn,
                    "confidence": round(d.confidence, 4),
                    "bbox": list(d.bbox),
                    "area": d.area,
                    "extra": d.extra
                }
                for d in self.defects
            ],
            "fps": round(self.fps, 2),
            "inference_time": round(self.inference_time, 2),
            "frame_width": self.frame_width,
            "frame_height": self.frame_height
        }


class BaseDetector(ABC):
    """检测器抽象基类"""

    # 缺陷类别中文映射，子类可扩展
    LABEL_CN_MAP = {
        "foreign_object": "异物",
        "defect": "表面缺陷",
        "broken": "破损/缺角",
        "over_baked": "烤焦",
        "under_baked": "未烤熟",
        "size_anomaly": "尺寸异常",
        "color_anomaly": "颜色异常",
        "shape_anomaly": "形状异常",
    }

    def __init__(self, config):
        self.config = config
        self._last_inference_time = 0.0

    @abstractmethod
    def detect(self, frame):
        """
        对一帧图像执行检测

        参数:
            frame: numpy.ndarray, BGR 格式图像
        返回:
            DetectionResult
        """
        pass

    def get_label_cn(self, label):
        """获取缺陷类别的中文名称"""
        return self.LABEL_CN_MAP.get(label, label)

    def _make_result(self, frame, defects, inference_start):
        """构建检测结果（公共方法）"""
        import time
        now = time.time()
        inference_ms = (now - inference_start) * 1000
        self._last_inference_time = inference_ms

        h, w = frame.shape[:2] if frame is not None else (0, 0)
        fps = 1000.0 / inference_ms if inference_ms > 0 else 0.0

        return DetectionResult(
            timestamp=now,
            is_defective=len(defects) > 0,
            defects=defects,
            fps=fps,
            inference_time=inference_ms,
            frame_width=w,
            frame_height=h
        )
