"""
演示模拟器
在无实物糕点/无摄像头环境下，合成带缺陷的演示画面。
用于与企业对接需求时的系统演示，避免"空跑"尴尬。

模拟内容：
- 生成模拟的传送带背景
- 随机生成金黄色糕点（圆形/椭圆形）
- 随机注入缺陷：异物（头发状线条）、破损、烤焦斑点、尺寸异常
- 检测引擎对合成画面执行真实检测流程
"""
import cv2
import numpy as np
import time
import random
from .base import BaseDetector, DetectionResult, DefectItem


class DemoSimulator(BaseDetector):
    """演示模拟器：合成画面 + 真实检测"""

    def __init__(self, config):
        super().__init__(config)
        self._frame_count = 0
        self._defect_injection_rate = 0.15  # 每个糕点15%概率注入缺陷（更真实）
        random.seed(42)
        # 基准糕点尺寸（大部分糕点应接近此尺寸，避免规则法误报尺寸异常）
        self._base_pw = 120
        self._base_ph = 90

    def generate_frame(self, width=1280, height=720):
        """
        生成一帧模拟产线画面
        返回: (frame, ground_truth_defects)
        """
        self._frame_count += 1

        # 传送带背景（不锈钢金属质感，中灰色）
        frame = np.ones((height, width, 3), dtype=np.uint8) * 110
        # 添加传送带纹理（横向条纹）
        for y in range(0, height, 40):
            cv2.line(frame, (0, y), (width, y), (120, 120, 120), 2)

        # 生成 3~5 个模拟糕点
        num_pastries = random.randint(3, 5)
        ground_truth = []

        for i in range(num_pastries):
            cx = random.randint(width // 5, width * 4 // 5)
            cy = random.randint(height // 4, height * 3 // 4)
            # 基准尺寸 ±10% 随机波动（正常糕点尺寸差异）
            pw = int(self._base_pw * random.uniform(0.9, 1.1))
            ph = int(self._base_ph * random.uniform(0.9, 1.1))

            # 决定是否注入缺陷
            has_defect = random.random() < self._defect_injection_rate
            defect_type = None

            if has_defect:
                defect_type = random.choice([
                    "foreign_object", "broken", "over_baked", "size_anomaly"
                ])

            # 绘制糕点（金黄色椭圆）
            color = (30, 160, 210)  # BGR 金黄色
            if defect_type == "over_baked":
                color = (20, 80, 120)  # 烤焦深色
            if defect_type == "size_anomaly":
                pw = int(self._base_pw * 0.45)  # 明显偏小
                ph = int(self._base_ph * 0.45)

            cv2.ellipse(frame, (cx, cy), (pw // 2, ph // 2), 0, 0, 360, color, -1)
            # 高光
            cv2.ellipse(frame, (cx - pw // 6, cy - ph // 6),
                       (pw // 4, ph // 5), 0, 0, 360, (80, 200, 240), -1)

            if defect_type == "broken":
                # 模拟缺角：在糕点上画一个黑色三角形缺口
                pts = np.array([
                    [cx + pw // 4, cy - ph // 4],
                    [cx + pw // 2, cy],
                    [cx + pw // 3, cy + ph // 4]
                ], np.int32)
                cv2.fillPoly(frame, [pts], (110, 110, 110))

            if defect_type == "foreign_object":
                # 模拟头发：深色曲线
                pts = []
                for t in np.linspace(0, 1, 20):
                    hx = int(cx - pw // 3 + t * pw * 0.8)
                    hy = int(cy + np.sin(t * 6) * 8)
                    pts.append([hx, hy])
                pts = np.array(pts, np.int32)
                cv2.polylines(frame, [pts], False, (15, 15, 15), 2)

            bbox = (cx - pw // 2, cy - ph // 2, cx + pw // 2, cy + ph // 2)
            if defect_type:
                ground_truth.append((defect_type, bbox))

        return frame, ground_truth

    def detect(self, frame):
        """
        演示模式：如果传入的 frame 为空，生成模拟画面并检测
        """
        t0 = time.time()

        if frame is None:
            frame, _ = self.generate_frame()

        # 使用规则法对模拟画面执行真实检测
        from .rule_based import RuleBasedDetector
        if not hasattr(self, '_rule_detector'):
            self._rule_detector = RuleBasedDetector(self.config)

        result = self._rule_detector.detect(frame)
        # 附加模拟帧到结果
        result._demo_frame = frame
        return result
