#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
冒烟测试：验证系统核心模块能否正常加载和运行
不依赖摄像头，使用合成图像测试检测流程。

运行方式：
    python tests/test_smoke.py
"""
import os
import sys
import time

# 项目根目录
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)


def test_config():
    """测试配置加载"""
    print("[测试] 配置加载...")
    from src.config import get_config
    config = get_config(os.path.join(PROJECT_ROOT, "config.yaml"))
    assert config.get("system.name") is not None
    assert config.get("detection.engine") is not None
    print("  ✓ 配置加载成功")
    return config


def test_rule_based_detector(config):
    """测试规则法检测器"""
    print("[测试] 规则法检测器...")
    import numpy as np
    from src.detection import RuleBasedDetector

    detector = RuleBasedDetector(config)

    # 生成模拟糕点画面
    frame = np.ones((480, 640, 3), dtype=np.uint8) * 45
    # 画一个金黄色椭圆（模拟糕点）
    import cv2
    cv2.ellipse(frame, (320, 240), (80, 60), 0, 0, 360, (30, 160, 210), -1)

    # 预热（校准需要几帧）
    for _ in range(5):
        detector.detect(frame)

    result = detector.detect(frame)
    assert result is not None
    assert result.frame_width == 640
    assert result.frame_height == 480
    print(f"  ✓ 检测完成，耗时: {result.inference_time:.2f}ms, FPS: {result.fps:.1f}")
    return detector


def test_drawing():
    """测试可视化绘制"""
    print("[测试] 可视化绘制...")
    import numpy as np
    import cv2
    from src.detection import DetectionResult, DefectItem
    from src.utils.drawing import draw_detection_overlay

    frame = np.ones((480, 640, 3), dtype=np.uint8) * 45
    result = DetectionResult(
        timestamp=time.time(),
        is_defective=True,
        defects=[
            DefectItem(
                label="foreign_object",
                label_cn="异物",
                confidence=0.95,
                bbox=(100, 100, 200, 200)
            )
        ]
    )
    annotated = draw_detection_overlay(frame, result)
    assert annotated is not None
    assert annotated.shape == frame.shape
    print("  ✓ 可视化绘制成功")


def test_demo_simulator(config):
    """测试演示模拟器"""
    print("[测试] 演示模拟器...")
    from src.detection import DemoSimulator

    sim = DemoSimulator(config)
    frame, ground_truth = sim.generate_frame(640, 480)
    assert frame is not None
    assert frame.shape == (480, 640, 3)
    print(f"  ✓ 模拟画面生成成功，尺寸: {frame.shape}")
    return sim


def test_logger(config):
    """测试日志记录"""
    print("[测试] 日志记录...")
    from src.output.logger import DetectionLogger
    from src.detection import DetectionResult

    logger = DetectionLogger(config)
    result = DetectionResult(
        timestamp=time.time(),
        is_defective=False,
        defects=[]
    )
    logger.log(result)
    logger.close()
    print("  ✓ 日志记录成功")


def test_web_app(config):
    """测试 Flask 应用创建"""
    print("[测试] Flask 应用创建...")
    from src.web import create_app
    app = create_app(config)
    assert app is not None
    # 测试路由存在
    rules = [rule.rule for rule in app.url_map.iter_rules()]
    assert "/" in rules
    assert "/video_feed" in rules
    assert "/api/stats" in rules
    print(f"  ✓ Flask 应用创建成功，路由数: {len(rules)}")


def main():
    print("=" * 50)
    print("  糕点质检系统 - 冒烟测试")
    print("=" * 50)

    try:
        config = test_config()
        test_rule_based_detector(config)
        test_drawing()
        test_demo_simulator(config)
        test_logger(config)
        test_web_app(config)

        print("\n" + "=" * 50)
        print("  所有测试通过！系统可以正常运行。")
        print("=" * 50)
        return 0
    except Exception as e:
        print(f"\n[失败] 测试异常: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
