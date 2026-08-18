"""
RKNN 检测器（RK3588/RK3572 NPU 推理）
使用瑞芯微 rknnlite2 运行时，在 NPU 上执行 INT8 量化模型推理。
仅在 RK3588/RK3572 硬件上可用，x86 平台会自动降级。

模型转换：使用 deploy/convert_to_rknn.py 将 YOLOv8 .pt/.onnx 转为 .rknn
"""
import os
import time
import numpy as np
from .base import BaseDetector, DetectionResult, DefectItem


class RKNNDetector(BaseDetector):
    """RKNN NPU 检测器（RK3588/RK3572）"""

    def __init__(self, config):
        super().__init__(config)
        rc = config.get("detection.rknn", {})
        self.model_path = rc.get("model_path", "data/models/best.rknn")
        self.conf_threshold = rc.get("conf_threshold", 0.5)
        self.iou_threshold = rc.get("iou_threshold", 0.45)
        self.input_size = rc.get("input_size", 640)
        self.class_names = rc.get("class_names", {0: "foreign_object"})
        self._rknn = None
        self._available = False
        self._load_model()

    def _load_model(self):
        """加载 RKNN 模型"""
        if not os.path.exists(self.model_path):
            print(f"[警告] RKNN 模型不存在: {self.model_path}")
            return

        try:
            from rknnlite.api import RKNNLite
            self._rknn = RKNNLite()
            ret = self._rknn.load_rknn(self.model_path)
            if ret != 0:
                print(f"[错误] RKNN 模型加载失败，错误码: {ret}")
                return
            ret = self._rknn.init_runtime()
            if ret != 0:
                print(f"[错误] RKNN 运行时初始化失败，错误码: {ret}")
                return
            self._available = True
            print(f"[信息] RKNN 模型加载成功: {self.model_path}")
        except ImportError:
            print("[警告] 未安装 rknnlite2，当前平台非 RK3588/RK3572 或未安装运行时")
            print("[提示] 在 RK3588 上执行: pip install rknnlite2")
        except Exception as e:
            print(f"[错误] RKNN 初始化异常: {e}")

    def detect(self, frame):
        """RKNN NPU 推理"""
        t0 = time.time()
        defects = []

        if frame is None or not self._available:
            return self._make_result(frame, defects, t0)

        try:
            # 预处理：resize + 归一化 + BGR2RGB
            img = self._preprocess(frame)
            # NPU 推理
            outputs = self._rknn.inference(inputs=[img])
            # 后处理：解析检测框
            defects = self._postprocess(outputs, frame.shape[:2])
        except Exception as e:
            print(f"[错误] RKNN 推理异常: {e}")

        return self._make_result(frame, defects, t0)

    def _preprocess(self, frame):
        """图像预处理：适配 YOLO 输入"""
        import cv2
        img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = cv2.resize(img, (self.input_size, self.input_size))
        img = img.astype(np.float32) / 255.0
        # HWC -> NCHW
        img = np.transpose(img, (2, 0, 1))
        img = np.expand_dims(img, axis=0)
        return img

    def _postprocess(self, outputs, orig_shape):
        """
        YOLOv8 输出后处理
        注意：具体输出格式取决于模型转换时的设置，此处提供通用实现。
        如果转换时保留了后处理层，outputs[0] 直接为 [batch, num_dets, 6]
        """
        defects = []
        if not outputs or len(outputs) == 0:
            return defects

        output = outputs[0]
        orig_h, orig_w = orig_shape

        # 尝试两种输出格式
        if output.ndim == 3 and output.shape[2] == 6:
            # 格式: [1, num_dets, 6] -> [x1, y1, x2, y2, conf, cls]
            dets = output[0]
        elif output.ndim == 3:
            # 格式: [1, 4+num_classes, num_anchors] -> 需要转置
            dets = np.transpose(output[0], (1, 0))
        else:
            return defects

        for det in dets:
            if len(det) < 6:
                continue
            x1, y1, x2, y2, conf, cls = det[:6]
            if conf < self.conf_threshold:
                continue
            # 坐标缩放回原图
            scale_x = orig_w / self.input_size
            scale_y = orig_h / self.input_size
            x1, x2 = int(x1 * scale_x), int(x2 * scale_x)
            y1, y2 = int(y1 * scale_y), int(y2 * scale_y)
            cls_id = int(cls)
            label = self.class_names.get(cls_id, f"class_{cls_id}")
            defects.append(DefectItem(
                label=label,
                label_cn=self.get_label_cn(label),
                confidence=float(conf),
                bbox=(x1, y1, x2, y2),
                area=(x2 - x1) * (y2 - y1)
            ))

        # NMS
        defects = self._nms(defects)
        return defects

    def _nms(self, defects):
        """非极大值抑制"""
        if not defects:
            return defects
        boxes = np.array([d.bbox for d in defects], dtype=np.float32)
        scores = np.array([d.confidence for d in defects])

        try:
            import cv2
            indices = cv2.dnn.NMSBoxes(
                boxes.tolist(), scores.tolist(),
                self.conf_threshold, self.iou_threshold
            )
            if isinstance(indices, np.ndarray):
                indices = indices.flatten()
            return [defects[i] for i in indices]
        except Exception:
            return defects

    def release(self):
        """释放 RKNN 资源"""
        if self._rknn is not None:
            try:
                self._rknn.release()
            except Exception:
                pass
            self._rknn = None

    @property
    def is_available(self):
        return self._available
