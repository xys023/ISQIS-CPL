from .base import BaseDetector, DetectionResult, DefectItem
from .rule_based import RuleBasedDetector
from .yolo_detector import YOLODetector
from .rknn_detector import RKNNDetector
from .demo_simulator import DemoSimulator

__all__ = [
    "BaseDetector", "DetectionResult", "DefectItem",
    "RuleBasedDetector", "YOLODetector", "RKNNDetector", "DemoSimulator",
    "create_detector"
]


def create_detector(config):
    """
    工厂方法：根据配置创建检测器实例

    参数:
        config: ConfigManager 实例
    返回:
        BaseDetector 子类实例
    """
    engine = config.get("detection.engine", "rule_based")

    if engine == "rule_based":
        return RuleBasedDetector(config)
    elif engine == "yolo":
        return YOLODetector(config)
    elif engine == "rknn":
        return RKNNDetector(config)
    elif engine == "demo":
        return DemoSimulator(config)
    else:
        raise ValueError(f"不支持的检测引擎: {engine}")
