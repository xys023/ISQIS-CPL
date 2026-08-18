"""
YOLO 深度学习检测器
支持 ultralytics YOLOv8 模型（.pt / .onnx 格式）。
需要用户自行训练模型并放置到 data/models/ 目录。
未安装 ultralytics 或模型不存在时，自动降级为规则法。
"""
import os
import time
import numpy as np
from .base import BaseDetector, DetectionResult, DefectItem


class YOLODetector(BaseDetector):
    """YOLOv8 检测器"""

    def __init__(self, config):
        super().__init__(config)
        yc = config.get("detection.yolo", {})
        self.model_path = yc.get("model_path", "data/models/best.pt")
        self.conf_threshold = yc.get("conf_threshold", 0.5)
        self.iou_threshold = yc.get("iou_threshold", 0.45)
        self.input_size = yc.get("input_size", 640)
        self.class_names = yc.get("class_names", {0: "foreign_object"})
        self._model = None
        self._ultralytics_available = False
        self._load_model()

    def _load_model(self):
        """加载 YOLO 模型"""
        if not os.path.exists(self.model_path):
            print(f"[警告] YOLO 模型文件不存在: {self.model_path}")
            print("[提示] 请训练模型后放置到该路径，或在 config.yaml 中将 engine 改为 rule_based")
            return

        try:
            from ultralytics import YOLO
            self._model = YOLO(self.model_path)
            self._ultralytics_available = True
            print(f"[信息] YOLO 模型加载成功: {self.model_path}")
        except ImportError:
            print("[警告] 未安装 ultralytics，无法使用 YOLO 检测")
            print("[提示] 执行: pip install ultralytics")
        except Exception as e:
            print(f"[错误] YOLO 模型加载失败: {e}")

    def detect(self, frame):
        """YOLO 推理"""
        t0 = time.time()
        defects = []

        if frame is None:
            return self._make_result(frame, defects, t0)

        if not self._ultralytics_available or self._model is None:
            # 降级：返回空结果（上层可选择回退到规则法）
            return self._make_result(frame, defects, t0)

        try:
            results = self._model(
                frame,
                conf=self.conf_threshold,
                iou=self.iou_threshold,
                imgsz=self.input_size,
                verbose=False
            )

            for result in results:
                if result.boxes is not None:
                    for box in result.boxes:
                        cls_id = int(box.cls[0])
                        conf = float(box.conf[0])
                        x1, y1, x2, y2 = map(int, box.xyxy[0])
                        label = self.class_names.get(cls_id, f"class_{cls_id}")
                        defects.append(DefectItem(
                            label=label,
                            label_cn=self.get_label_cn(label),
                            confidence=conf,
                            bbox=(x1, y1, x2, y2),
                            area=(x2 - x1) * (y2 - y1)
                        ))
        except Exception as e:
            print(f"[错误] YOLO 推理异常: {e}")

        return self._make_result(frame, defects, t0)

    @property
    def is_available(self):
        return self._ultralytics_available and self._model is not None
