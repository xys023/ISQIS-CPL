"""
规则法视觉质检检测器（开箱即用，无需训练）

检测原理：
1. 通过颜色空间分割提取糕点目标（糕点通常为金黄色/棕色系）
2. 对每个糕点目标进行多维度质检：
   - 颜色异常：表面颜色偏离基准（烤焦/未烤熟）
   - 形状完整度：轮廓凹凸比、圆形度判断破损缺角
   - 尺寸异常：相对标准尺寸偏差过大
   - 异物检测：深色细长轮廓（头发等）
   - 表面缺陷：斑点、焦斑、空洞

适用场景：初期演示、无训练数据时的快速部署。
精度上限低于深度学习方案，建议后期采集数据训练 YOLO 模型替换。
"""
import cv2
import numpy as np
import time
from .base import BaseDetector, DetectionResult, DefectItem


class RuleBasedDetector(BaseDetector):
    """基于传统图像处理的规则法质检"""

    def __init__(self, config):
        super().__init__(config)
        rb = config.get("detection.rule_based", {})
        self.min_object_area = rb.get("min_object_area", 500)
        self.max_object_area = rb.get("max_object_area", 200000)
        self.color_dev_threshold = rb.get("color_deviation_threshold", 30)
        self.shape_threshold = rb.get("shape_completeness_threshold", 0.75)
        self.size_dev_percent = rb.get("size_deviation_percent", 25)
        self.foreign_min_area = rb.get("foreign_object_min_area", 20)
        self.foreign_hsv_lower = np.array(rb.get("foreign_object_hsv_lower", [0, 0, 0]))
        self.foreign_hsv_upper = np.array(rb.get("foreign_object_hsv_upper", [180, 255, 60]))
        self.surface_defect_min_area = rb.get("surface_defect_min_area", 30)

        # 糕点基准颜色（HSV）— 金黄色烘焙食品的典型范围
        # 这些值会在运行时根据实际画面自适应调整
        self._reference_hsv_mean = None
        self._reference_size = None
        self._calibration_frame_count = 0

    def detect(self, frame):
        """执行规则法检测"""
        t0 = time.time()
        defects = []

        if frame is None:
            return self._make_result(frame, defects, t0)

        h, w = frame.shape[:2]

        # 1. 转换到 HSV 颜色空间（对光照变化更鲁棒）
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

        # 2. 分割糕点区域（金黄色系）
        pastry_mask = self._segment_pastry(hsv)

        # 3. 形态学操作去噪
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        pastry_mask = cv2.morphologyEx(pastry_mask, cv2.MORPH_CLOSE, kernel)
        pastry_mask = cv2.morphologyEx(pastry_mask, cv2.MORPH_OPEN, kernel)

        # 4. 查找糕点轮廓
        contours, _ = cv2.findContours(pastry_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        pastry_contours = []
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if self.min_object_area <= area <= self.max_object_area:
                pastry_contours.append((cnt, area))

        # 按面积降序，取最大的几个作为糕点
        pastry_contours.sort(key=lambda x: x[1], reverse=True)
        pastry_contours = pastry_contours[:10]  # 最多检测10个糕点

        # 5. 自适应校准基准（前几帧用于学习正常糕点的颜色和尺寸）
        if self._calibration_frame_count < 30 and len(pastry_contours) > 0:
            self._calibrate(hsv, pastry_contours)
            self._calibration_frame_count += 1

        # 6. 对每个糕点执行质检
        for cnt, area in pastry_contours:
            x, y, cw, ch = cv2.boundingRect(cnt)
            bbox = (x, y, x + cw, y + ch)

            # 6a. 形状完整度检测
            shape_score = self._check_shape(cnt, area)
            if shape_score < self.shape_threshold:
                defects.append(DefectItem(
                    label="shape_anomaly",
                    label_cn=self.get_label_cn("shape_anomaly"),
                    confidence=1.0 - shape_score,
                    bbox=bbox,
                    area=area,
                    extra={"completeness": round(shape_score, 3)}
                ))

            # 6b. 尺寸异常检测
            if self._reference_size is not None:
                size_ratio = area / self._reference_size
                if abs(size_ratio - 1.0) * 100 > self.size_dev_percent:
                    defects.append(DefectItem(
                        label="size_anomaly",
                        label_cn=self.get_label_cn("size_anomaly"),
                        confidence=min(abs(size_ratio - 1.0), 1.0),
                        bbox=bbox,
                        area=area,
                        extra={"size_ratio": round(size_ratio, 3)}
                    ))

            # 6c. 颜色异常检测（烤焦/未烤熟）
            color_defect = self._check_color(hsv, cnt, bbox)
            if color_defect:
                defects.append(color_defect)

            # 6d. 表面缺陷检测（斑点/焦斑/空洞）
            surface_defects = self._check_surface_defects(frame, hsv, cnt, bbox)
            defects.extend(surface_defects)

        # 7. 异物检测（独立于糕点分割，检测深色细长物体）
        foreign_defects = self._detect_foreign_objects(hsv, frame, pastry_mask)
        defects.extend(foreign_defects)

        return self._make_result(frame, defects, t0)

    def _segment_pastry(self, hsv):
        """
        基于颜色分割糕点区域
        糕点通常为金黄色到棕色，HSV范围较宽
        """
        # 金黄色/棕色范围（H: 10~35, S: 50~255, V: 80~255）
        lower1 = np.array([5, 50, 60])
        upper1 = np.array([35, 255, 255])
        mask1 = cv2.inRange(hsv, lower1, upper1)

        # 较深的棕色（烤色较深的糕点）
        lower2 = np.array([0, 30, 40])
        upper2 = np.array([15, 255, 100])
        mask2 = cv2.inRange(hsv, lower2, upper2)

        mask = cv2.bitwise_or(mask1, mask2)
        return mask

    def _calibrate(self, hsv, pastry_contours):
        """自适应校准：学习正常糕点的基准颜色和尺寸"""
        areas = [area for _, area in pastry_contours]
        if areas:
            median_area = float(np.median(areas))
            if self._reference_size is None:
                self._reference_size = median_area
            else:
                self._reference_size = self._reference_size * 0.9 + median_area * 0.1

        # 学习基准颜色
        for cnt, area in pastry_contours[:3]:
            mask = np.zeros(hsv.shape[:2], dtype=np.uint8)
            cv2.drawContours(mask, [cnt], -1, 255, -1)
            mean_hsv = cv2.mean(hsv, mask=mask)[:3]
            if self._reference_hsv_mean is None:
                self._reference_hsv_mean = np.array(mean_hsv)
            else:
                self._reference_hsv_mean = (
                    self._reference_hsv_mean * 0.9 + np.array(mean_hsv) * 0.1
                )

    def _check_shape(self, contour, area):
        """
        形状完整度检测
        使用圆形度 + 凸包面积比综合评估
        返回 0~1，1为完美
        """
        if area <= 0:
            return 0.0

        # 圆形度：4πA / P²，圆形=1，越不规则越小
        perimeter = cv2.arcLength(contour, True)
        if perimeter <= 0:
            return 0.0
        circularity = 4 * np.pi * area / (perimeter ** 2)
        circularity = min(circularity, 1.0)

        # 凸包面积比：轮廓面积 / 凸包面积，缺角会降低此值
        hull = cv2.convexHull(contour)
        hull_area = cv2.contourArea(hull)
        if hull_area <= 0:
            hull_ratio = 0.0
        else:
            hull_ratio = area / hull_area

        # 综合评分（凸包比对缺角更敏感，权重更高）
        score = circularity * 0.3 + hull_ratio * 0.7
        return min(max(score, 0.0), 1.0)

    def _check_color(self, hsv, contour, bbox):
        """颜色异常检测：偏离基准颜色过多判定为烤焦或未烤熟"""
        if self._reference_hsv_mean is None:
            return None

        mask = np.zeros(hsv.shape[:2], dtype=np.uint8)
        cv2.drawContours(mask, [contour], -1, 255, -1)
        mean_hsv = np.array(cv2.mean(hsv, mask=mask)[:3])

        # 计算颜色距离（HSV空间加权，H分量权重更高）
        diff = np.abs(mean_hsv - self._reference_hsv_mean)
        # H是环形，取最小差值
        diff[0] = min(diff[0], 180 - diff[0])
        weighted_dist = diff[0] * 1.5 + diff[1] * 0.5 + diff[2] * 0.8

        if weighted_dist > self.color_dev_threshold:
            # 判断是烤焦（V偏低/S偏高）还是未烤熟（V偏高/S偏低）
            if mean_hsv[2] < self._reference_hsv_mean[2] - 20:
                label = "over_baked"
            elif mean_hsv[1] < self._reference_hsv_mean[1] - 30:
                label = "under_baked"
            else:
                label = "color_anomaly"

            confidence = min(weighted_dist / 100.0, 1.0)
            return DefectItem(
                label=label,
                label_cn=self.get_label_cn(label),
                confidence=confidence,
                bbox=bbox,
                area=int(cv2.contourArea(contour)),
                extra={"color_distance": round(weighted_dist, 2)}
            )
        return None

    def _check_surface_defects(self, frame, hsv, contour, bbox):
        """表面缺陷检测：在糕点区域内查找深色斑点（焦斑/空洞）"""
        defects = []
        x, y, x2, y2 = bbox
        if x2 - x <= 0 or y2 - y <= 0:
            return defects

        # 创建糕点掩码
        mask = np.zeros(hsv.shape[:2], dtype=np.uint8)
        cv2.drawContours(mask, [contour], -1, 255, -1)

        # 在糕点区域内检测深色斑点（焦斑/空洞）
        roi_hsv = hsv[y:y2, x:x2]
        roi_mask = mask[y:y2, x:x2]

        # 深色区域（V值低）
        dark_mask = cv2.inRange(roi_hsv, np.array([0, 0, 0]), np.array([180, 255, 50]))
        dark_mask = cv2.bitwise_and(dark_mask, roi_mask)

        # 形态学去噪
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        dark_mask = cv2.morphologyEx(dark_mask, cv2.MORPH_OPEN, kernel)

        spot_contours, _ = cv2.findContours(dark_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for sc in spot_contours:
            s_area = cv2.contourArea(sc)
            if s_area >= self.surface_defect_min_area:
                sx, sy, sw, sh = cv2.boundingRect(sc)
                defects.append(DefectItem(
                    label="defect",
                    label_cn=self.get_label_cn("defect"),
                    confidence=min(s_area / 200.0, 1.0),
                    bbox=(x + sx, y + sy, x + sx + sw, y + sy + sh),
                    area=int(s_area),
                    extra={"type": "dark_spot"}
                ))

        return defects

    def _detect_foreign_objects(self, hsv, frame, pastry_mask):
        """
        异物检测：检测深色细长轮廓（头发、塑料丝等）
        策略：仅在糕点表面及其附近区域检测深色异物，排除传送带背景
        """
        defects = []

        # 深色区域掩码
        dark_mask = cv2.inRange(hsv, self.foreign_hsv_lower, self.foreign_hsv_upper)

        # 仅在糕点区域+小范围边缘检测异物（头发通常落在糕点上）
        # 膨胀糕点掩码，覆盖糕点边缘附近
        kernel_margin = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (25, 25))
        pastry_search_area = cv2.dilate(pastry_mask, kernel_margin, iterations=1)

        # 只在糕点搜索区域内查找深色异物
        foreign_mask = cv2.bitwise_and(dark_mask, pastry_search_area)

        # 形态学去噪
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        foreign_mask = cv2.morphologyEx(foreign_mask, cv2.MORPH_OPEN, kernel)

        contours, _ = cv2.findContours(foreign_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area < self.foreign_min_area:
                continue

            # 细长比检测：头发通常长宽比 > 3
            rect = cv2.minAreaRect(cnt)
            (rw, rh) = rect[1]
            if rw <= 0 or rh <= 0:
                continue
            aspect_ratio = max(rw, rh) / min(rw, rh)

            # 细长物体 or 面积较大的深色异物
            if aspect_ratio > 2.5 or area > self.foreign_min_area * 3:
                x, y, cw, ch = cv2.boundingRect(cnt)
                confidence = min(aspect_ratio / 10.0 + area / 500.0, 1.0)
                defects.append(DefectItem(
                    label="foreign_object",
                    label_cn=self.get_label_cn("foreign_object"),
                    confidence=max(confidence, 0.5),
                    bbox=(x, y, x + cw, y + ch),
                    area=int(area),
                    extra={"aspect_ratio": round(aspect_ratio, 2)}
                ))

        return defects
