"""
检测日志记录模块
将每次检测结果写入 CSV 文件，支持按天自动分割。
"""
import os
import csv
import time
import threading
from datetime import datetime


class DetectionLogger:
    """检测结果 CSV 日志记录器"""

    def __init__(self, config):
        self.config = config
        self.enabled = config.get("logging.save_log", True)
        self.log_dir = config.get("logging.log_dir", "data/logs")
        self.retention_days = config.get("logging.retention_days", 30)
        self._lock = threading.Lock()
        self._current_file = None
        self._current_date = None
        self._csv_writer = None
        self._file_handle = None

        if self.enabled:
            os.makedirs(self.log_dir, exist_ok=True)
            self._ensure_file()

    def _ensure_file(self):
        """确保当前日期的日志文件已打开"""
        today = datetime.now().strftime("%Y-%m-%d")
        if self._current_date != today:
            self._close_file()
            filename = f"detection_{today}.csv"
            filepath = os.path.join(self.log_dir, filename)
            file_exists = os.path.exists(filepath)
            self._file_handle = open(filepath, "a", newline="", encoding="utf-8-sig")
            self._csv_writer = csv.writer(self._file_handle)
            if not file_exists:
                # 写入表头
                self._csv_writer.writerow([
                    "时间戳", "日期时间", "是否不合格", "缺陷数量",
                    "缺陷类型", "置信度", "边界框", "推理耗时(ms)", "帧率"
                ])
            self._current_date = today
            self._current_file = filepath

    def _close_file(self):
        if self._file_handle is not None:
            self._file_handle.close()
            self._file_handle = None
            self._csv_writer = None

    def log(self, result):
        """记录一条检测结果"""
        if not self.enabled:
            return
        with self._lock:
            try:
                self._ensure_file()
                dt = datetime.fromtimestamp(result.timestamp)
                defect_types = ";".join([d.label_cn for d in result.defects])
                confidences = ";".join([f"{d.confidence:.2f}" for d in result.defects])
                bboxes = ";".join([
                    f"[{d.bbox[0]},{d.bbox[1]},{d.bbox[2]},{d.bbox[3]}]"
                    for d in result.defects
                ])
                self._csv_writer.writerow([
                    result.timestamp,
                    dt.strftime("%Y-%m-%d %H:%M:%S"),
                    "是" if result.is_defective else "否",
                    len(result.defects),
                    defect_types,
                    confidences,
                    bboxes,
                    f"{result.inference_time:.2f}",
                    f"{result.fps:.2f}"
                ])
                self._file_handle.flush()
            except Exception as e:
                print(f"[错误] 日志写入失败: {e}")

    def close(self):
        with self._lock:
            self._close_file()

    def cleanup_old_logs(self):
        """清理超过保留天数的日志文件"""
        if self.retention_days <= 0:
            return
        cutoff = time.time() - self.retention_days * 86400
        try:
            for fname in os.listdir(self.log_dir):
                if fname.startswith("detection_") and fname.endswith(".csv"):
                    fpath = os.path.join(self.log_dir, fname)
                    if os.path.getmtime(fpath) < cutoff:
                        os.remove(fpath)
                        print(f"[信息] 已清理过期日志: {fname}")
        except Exception as e:
            print(f"[警告] 日志清理失败: {e}")
