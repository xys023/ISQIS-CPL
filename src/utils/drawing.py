"""
检测结果可视化绘制模块
在画面上绘制检测框、标签、ROI区域、状态信息等。
"""
import cv2
import numpy as np


# 缺陷类型对应的颜色 (BGR)
DEFECT_COLORS = {
    "foreign_object": (0, 0, 255),    # 红色 - 异物（最严重）
    "broken": (0, 165, 255),          # 橙色 - 破损
    "over_baked": (0, 0, 139),        # 深红 - 烤焦
    "under_baked": (255, 255, 0),     # 青色 - 未烤熟
    "defect": (0, 255, 255),          # 黄色 - 表面缺陷
    "size_anomaly": (255, 0, 255),    # 紫色 - 尺寸异常
    "color_anomaly": (128, 0, 128),   # 紫色 - 颜色异常
    "shape_anomaly": (0, 128, 255),   # 橙红 - 形状异常
}


def draw_detection_overlay(frame, result, config=None):
    """
    在帧上绘制检测结果叠加层

    参数:
        frame: 原始 BGR 图像
        result: DetectionResult
        config: 配置对象（用于读取 ROI 设置）
    返回:
        标注后的图像
    """
    if frame is None:
        return None

    annotated = frame.copy()
    h, w = annotated.shape[:2]

    # 1. 绘制 ROI 区域
    if config and config.get("roi.enabled", False):
        x1 = int(config.get("roi.x1", 0.1) * w)
        y1 = int(config.get("roi.y1", 0.1) * h)
        x2 = int(config.get("roi.x2", 0.9) * w)
        y2 = int(config.get("roi.y2", 0.9) * h)
        cv2.rectangle(annotated, (x1, y1), (x2, y2), (0, 255, 0), 2)
        cv2.putText(
            annotated, "ROI", (x1 + 5, y1 + 20),
            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1
        )

    # 2. 绘制检测框
    if result and result.defects:
        for d in result.defects:
            color = DEFECT_COLORS.get(d.label, (0, 0, 255))
            x1, y1, x2, y2 = d.bbox
            # 边界框
            cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)
            # 标签背景
            label = f"{d.label_cn} {d.confidence:.0%}"
            (tw, th), _ = cv2.getTextSize(
                label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2
            )
            cv2.rectangle(
                annotated, (x1, y1 - th - 8), (x1 + tw + 10, y1),
                color, -1
            )
            # 标签文字
            cv2.putText(
                annotated, label, (x1 + 5, y1 - 5),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2
            )

    # 3. 顶部状态栏
    status_color = (0, 0, 255) if (result and result.is_defective) else (0, 255, 0)
    status_text = "不合格" if (result and result.is_defective) else "合格"

    # 半透明状态栏背景
    overlay = annotated.copy()
    cv2.rectangle(overlay, (0, 0), (w, 40), (20, 20, 20), -1)
    cv2.addWeighted(overlay, 0.7, annotated, 0.3, 0, annotated)

    cv2.putText(
        annotated, f"状态: {status_text}", (15, 28),
        cv2.FONT_HERSHEY_SIMPLEX, 0.7, status_color, 2
    )
    if result:
        fps_text = f"FPS: {result.fps:.1f}"
        cv2.putText(
            annotated, fps_text, (w - 130, 28),
            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 2
        )
        infer_text = f"{result.inference_time:.1f}ms"
        cv2.putText(
            annotated, infer_text, (w - 230, 28),
            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 2
        )

    return annotated
