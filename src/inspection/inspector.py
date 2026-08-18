"""
质检主流程模块
协调摄像头采集、ROI裁剪、检测推理、结果输出的完整流水线。
支持多线程运行，为 Web 端提供最新帧和检测结果。
"""
import cv2
import time
import threading
import numpy as np
from collections import deque

from ..camera import create_camera
from ..detection import create_detector
from ..output.alarm import AlarmManager
from ..output.logger import DetectionLogger
from ..output.exporter import DataExporter
from ..utils.drawing import draw_detection_overlay


class QualityInspector:
    """
    糕点质检主控制器

    职责：
    1. 管理摄像头生命周期
    2. 按帧执行检测流水线
    3. 维护统计数据（合格率、缺陷分布等）
    4. 协调报警、日志、截图等输出
    5. 为 Web 端提供线程安全的帧和结果访问
    """

    def __init__(self, config):
        self.config = config
        self.camera = create_camera(config)
        self.detector = create_detector(config)
        self.alarm = AlarmManager(config)
        self.logger = DetectionLogger(config)
        self.exporter = DataExporter(config)

        # 运行状态
        self._running = False
        self._paused = False
        self._thread = None

        # 最新帧和结果（线程安全）
        self._latest_frame = None
        self._latest_result = None
        self._latest_annotated_frame = None
        self._lock = threading.Lock()

        # 统计数据
        self._stats = {
            "total": 0,
            "defective": 0,
            "passed": 0,
            "defect_types": {},
            "fps_history": deque(maxlen=100),
            "start_time": None,
        }

        # ROI 配置
        self.roi_enabled = config.get("roi.enabled", True)
        self.roi = [
            config.get("roi.x1", 0.1),
            config.get("roi.y1", 0.1),
            config.get("roi.x2", 0.9),
            config.get("roi.y2", 0.9),
        ]

        self.detect_interval = config.get("detection.detect_interval", 1)
        self._frame_counter = 0
        self._camera_available = True  # 摄像头是否可用

    def start(self):
        """启动质检流水线（后台线程）"""
        if self._running:
            return
        # 尝试打开摄像头，失败时在演示模式下降级为纯模拟
        try:
            self.camera.start()
            self._camera_available = True
        except Exception as e:
            self._camera_available = False
            engine = self.config.get("detection.engine", "")
            if engine == "demo":
                print(f"[警告] 摄像头不可用: {e}")
                print("[信息] 演示模式：将使用合成画面运行")
            else:
                raise  # 非演示模式下摄像头不可用则报错

        self._running = True
        self._paused = False
        self._stats["start_time"] = time.time()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        print("[信息] 质检流水线已启动")

    def stop(self):
        """停止质检流水线"""
        self._running = False
        if self._thread is not None:
            self._thread.join(timeout=5)
            self._thread = None
        self.camera.stop()
        self.alarm.stop()
        self.logger.close()
        print("[信息] 质检流水线已停止")

    def pause(self):
        self._paused = True

    def resume(self):
        self._paused = False

    def _run(self):
        """主循环：持续采集-检测-输出"""
        while self._running:
            if self._paused:
                time.sleep(0.1)
                continue

            frame = None
            # 1. 采集帧
            if self._camera_available:
                success, frame = self.camera.read()
                if not success or frame is None:
                    frame = None

            # 摄像头不可用或读取失败时，演示模式生成模拟帧
            if frame is None:
                if self.config.get("detection.engine") == "demo":
                    frame = self.detector.generate_frame()[0]
                if frame is None:
                    time.sleep(0.05)
                    continue

            self._frame_counter += 1

            # 2. 裁剪 ROI
            work_frame = self._crop_roi(frame)

            # 3. 检测（按间隔跳帧）
            if self._frame_counter % self.detect_interval == 0:
                result = self.detector.detect(work_frame)
                # 坐标映射回原图
                result = self._map_result_to_original(result, frame.shape)

                # 4. 更新统计
                self._update_stats(result)

                # 5. 输出处理
                if result.is_defective:
                    self.alarm.trigger(result)
                    if self.config.get("logging.save_defect_snapshot", True):
                        self.exporter.save_snapshot(frame, result)
                self.logger.log(result)

                # 6. 保存最新结果
                with self._lock:
                    self._latest_result = result
                    self._latest_frame = frame
                    self._latest_annotated_frame = draw_detection_overlay(
                        frame, result, self.config
                    )
            else:
                # 非检测帧：仅更新画面
                with self._lock:
                    self._latest_frame = frame
                    if self._latest_result is not None:
                        self._latest_annotated_frame = draw_detection_overlay(
                            frame, self._latest_result, self.config
                        )

    def _crop_roi(self, frame):
        """裁剪感兴趣区域"""
        if not self.roi_enabled:
            return frame
        h, w = frame.shape[:2]
        x1 = int(self.roi[0] * w)
        y1 = int(self.roi[1] * h)
        x2 = int(self.roi[2] * w)
        y2 = int(self.roi[3] * h)
        return frame[y1:y2, x1:x2].copy()

    def _map_result_to_original(self, result, orig_shape):
        """将 ROI 内的检测坐标映射回原图坐标"""
        if not self.roi_enabled:
            return result
        h, w = orig_shape[:2]
        offset_x = int(self.roi[0] * w)
        offset_y = int(self.roi[1] * h)
        for d in result.defects:
            x1, y1, x2, y2 = d.bbox
            d.bbox = (x1 + offset_x, y1 + offset_y, x2 + offset_x, y2 + offset_y)
        return result

    def _update_stats(self, result):
        """更新统计数据"""
        self._stats["total"] += 1
        if result.is_defective:
            self._stats["defective"] += 1
            for d in result.defects:
                label_cn = d.label_cn
                self._stats["defect_types"][label_cn] = (
                    self._stats["defect_types"].get(label_cn, 0) + 1
                )
        else:
            self._stats["passed"] += 1
        if result.fps > 0:
            self._stats["fps_history"].append(result.fps)

    def get_latest(self):
        """获取最新帧和检测结果（线程安全）"""
        with self._lock:
            return self._latest_frame, self._latest_result, self._latest_annotated_frame

    def get_annotated_frame(self):
        """获取带标注的最新帧"""
        with self._lock:
            return self._latest_annotated_frame

    def get_stats(self):
        """获取当前统计数据"""
        total = self._stats["total"]
        defective = self._stats["defective"]
        passed = self._stats["passed"]
        pass_rate = (passed / total * 100) if total > 0 else 0.0
        avg_fps = (
            sum(self._stats["fps_history"]) / len(self._stats["fps_history"])
            if self._stats["fps_history"] else 0.0
        )
        runtime = time.time() - self._stats["start_time"] if self._stats["start_time"] else 0

        return {
            "total": total,
            "defective": defective,
            "passed": passed,
            "pass_rate": round(pass_rate, 2),
            "defect_rate": round(100 - pass_rate, 2),
            "defect_types": dict(self._stats["defect_types"]),
            "avg_fps": round(avg_fps, 2),
            "camera_fps": round(self.camera.actual_fps, 2),
            "runtime_seconds": round(runtime, 1),
            "running": self._running,
            "paused": self._paused,
        }

    def reset_stats(self):
        """重置统计数据"""
        self._stats = {
            "total": 0,
            "defective": 0,
            "passed": 0,
            "defect_types": {},
            "fps_history": deque(maxlen=100),
            "start_time": time.time(),
        }

    def update_roi(self, x1, y1, x2, y2):
        """动态更新 ROI"""
        self.roi = [x1, y1, x2, y2]

    def update_config(self, key, value):
        """动态更新配置"""
        self.config.set(key, value)
        # 部分参数需要即时生效
        if key == "roi.enabled":
            self.roi_enabled = value
        elif key == "detection.detect_interval":
            self.detect_interval = value
