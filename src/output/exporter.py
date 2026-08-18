"""
数据导出模块
- 不合格品截图保存
- 检测数据导出（CSV/JSON）
- 统计报表生成
"""
import os
import cv2
import json
import time
import threading
from datetime import datetime


class DataExporter:
    """数据导出与截图管理"""

    def __init__(self, config):
        self.config = config
        self.snapshot_dir = config.get("logging.snapshot_dir", "data/snapshots")
        self.snapshot_format = config.get("logging.snapshot_format", "jpg")
        self._lock = threading.Lock()
        os.makedirs(self.snapshot_dir, exist_ok=True)

    def save_snapshot(self, frame, result):
        """保存不合格品截图（带检测标注）"""
        if frame is None:
            return None
        with self._lock:
            try:
                # 按日期分子目录
                today = datetime.now().strftime("%Y-%m-%d")
                day_dir = os.path.join(self.snapshot_dir, today)
                os.makedirs(day_dir, exist_ok=True)

                # 文件名：时间戳_缺陷类型
                ts = datetime.now().strftime("%H%M%S_%f")[:-3]
                defect_types = "_".join(
                    sorted(set(d.label for d in result.defects))
                )[:30]
                filename = f"{ts}_{defect_types}.{self.snapshot_format}"
                filepath = os.path.join(day_dir, filename)

                # 在截图上标注
                annotated = frame.copy()
                for d in result.defects:
                    x1, y1, x2, y2 = d.bbox
                    cv2.rectangle(annotated, (x1, y1), (x2, y2), (0, 0, 255), 2)
                    label = f"{d.label_cn} {d.confidence:.0%}"
                    cv2.putText(
                        annotated, label, (x1, y1 - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2
                    )

                ext = ".jpg" if self.snapshot_format == "jpg" else ".png"
                cv2.imwrite(filepath, annotated)
                return filepath
            except Exception as e:
                print(f"[错误] 截图保存失败: {e}")
                return None

    def export_stats_json(self, stats, output_path=None):
        """导出统计数据为 JSON"""
        if output_path is None:
            output_path = os.path.join(
                self.snapshot_dir,
                f"stats_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            )
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(stats, f, ensure_ascii=False, indent=2)
        return output_path

    def list_snapshots(self, date=None, limit=50):
        """列出截图文件"""
        if date:
            day_dir = os.path.join(self.snapshot_dir, date)
        else:
            day_dir = self.snapshot_dir

        if not os.path.exists(day_dir):
            return []

        files = []
        for root, _, filenames in os.walk(day_dir):
            for fn in filenames:
                if fn.endswith((".jpg", ".png")):
                    fpath = os.path.join(root, fn)
                    files.append({
                        "name": fn,
                        "path": fpath,
                        "size": os.path.getsize(fpath),
                        "time": os.path.getmtime(fpath)
                    })
        files.sort(key=lambda x: x["time"], reverse=True)
        return files[:limit]
