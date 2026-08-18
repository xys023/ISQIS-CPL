"""
Flask Web 应用模块
提供：
- 实时 MJPEG 视频流（带检测标注）
- REST API：统计数据、配置管理、截图列表、系统控制
- 工业级监控大屏前端
"""
import os
import cv2
import time
import threading
from flask import Flask, Response, jsonify, request, send_from_directory, render_template_string

from ..config import get_config
from ..inspection import QualityInspector


# 全局实例（由 WebServer 初始化）
_inspector = None
_config = None


def create_app(config=None, inspector=None):
    """创建 Flask 应用"""
    global _inspector, _config
    _config = config or get_config()
    _inspector = inspector

    app = Flask(
        __name__,
        static_folder=os.path.join(os.path.dirname(__file__), "static"),
        static_url_path="/static",
    )
    app.config["JSON_AS_ASCII"] = False

    # ---------- 页面路由 ----------
    @app.route("/")
    def index():
        """监控大屏主页"""
        return send_from_directory(app.static_folder, "index.html")

    # ---------- 视频流 ----------
    @app.route("/video_feed")
    def video_feed():
        """MJPEG 视频流"""
        return Response(
            _generate_frames(),
            mimetype="multipart/x-mixed-replace; boundary=frame",
        )

    # ---------- REST API ----------
    @app.route("/api/stats")
    def api_stats():
        """获取实时统计数据"""
        if _inspector:
            return jsonify(_inspector.get_stats())
        return jsonify({"error": "系统未启动"}), 503

    @app.route("/api/result")
    def api_result():
        """获取最新检测结果"""
        if _inspector:
            _, result, _ = _inspector.get_latest()
            if result:
                return jsonify(result.to_dict())
        return jsonify({"defects": [], "is_defective": False})

    @app.route("/api/config", methods=["GET"])
    def api_get_config():
        """获取当前配置"""
        return jsonify(_config.all)

    @app.route("/api/config", methods=["POST"])
    def api_set_config():
        """更新配置（部分字段支持热更新）"""
        data = request.get_json()
        if not data:
            return jsonify({"error": "无效请求"}), 400
        for key, value in data.items():
            _config.set(key, value)
            if _inspector:
                _inspector.update_config(key, value)
        return jsonify({"status": "ok"})

    @app.route("/api/config/save", methods=["POST"])
    def api_save_config():
        """保存配置到文件"""
        try:
            _config.save()
            return jsonify({"status": "ok", "message": "配置已保存"})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/api/control", methods=["POST"])
    def api_control():
        """系统控制：启动/停止/暂停/恢复/重置统计"""
        data = request.get_json() or {}
        action = data.get("action")
        if not _inspector:
            return jsonify({"error": "系统未初始化"}), 503

        if action == "pause":
            _inspector.pause()
        elif action == "resume":
            _inspector.resume()
        elif action == "reset_stats":
            _inspector.reset_stats()
        else:
            return jsonify({"error": f"未知操作: {action}"}), 400
        return jsonify({"status": "ok", "action": action})

    @app.route("/api/snapshots")
    def api_snapshots():
        """获取不合格品截图列表"""
        if _inspector:
            date = request.args.get("date")
            limit = int(request.args.get("limit", 20))
            snapshots = _inspector.exporter.list_snapshots(date=date, limit=limit)
            return jsonify(snapshots)
        return jsonify([])

    @app.route("/api/snapshot/<path:filepath>")
    def api_snapshot_image(filepath):
        """获取截图文件"""
        # 安全限制：只允许访问 snapshot 目录
        safe_dir = os.path.abspath(_config.get("logging.snapshot_dir", "data/snapshots"))
        full_path = os.path.abspath(filepath)
        if not full_path.startswith(safe_dir):
            return jsonify({"error": "非法路径"}), 403
        if os.path.exists(full_path):
            return send_from_directory(
                os.path.dirname(full_path),
                os.path.basename(full_path)
            )
        return jsonify({"error": "文件不存在"}), 404

    @app.route("/api/system")
    def api_system():
        """系统信息"""
        return jsonify({
            "name": _config.get("system.name", "糕点质检系统"),
            "version": _config.get("system.version", "1.0.0"),
            "company": _config.get("system.company", ""),
            "engine": _config.get("detection.engine", "rule_based"),
            "camera_type": _config.get("camera.source_type", "webcam"),
            "web_port": _config.get("web.port", 8080),
        })

    return app


def _generate_frames():
    """MJPEG 帧生成器"""
    jpeg_quality = _config.get("web.jpeg_quality", 85) if _config else 85
    while True:
        if _inspector:
            frame = _inspector.get_annotated_frame()
            if frame is not None:
                # 编码为 JPEG
                encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), jpeg_quality]
                _, buffer = cv2.imencode(".jpg", frame, encode_param)
                frame_bytes = buffer.tobytes()
                yield (
                    b"--frame\r\n"
                    b"Content-Type: image/jpeg\r\n\r\n" + frame_bytes + b"\r\n"
                )
                continue
        # 无帧时返回占位图
        time.sleep(0.1)
        placeholder = _make_placeholder()
        yield (
            b"--frame\r\n"
            b"Content-Type: image/jpeg\r\n\r\n" + placeholder + b"\r\n"
        )


def _make_placeholder():
    """生成等待画面占位图"""
    import numpy as np
    img = np.zeros((480, 640, 3), dtype=np.uint8)
    img[:] = (30, 30, 30)
    cv2.putText(
        img, "Waiting for camera...", (150, 240),
        cv2.FONT_HERSHEY_SIMPLEX, 1, (100, 100, 100), 2
    )
    _, buffer = cv2.imencode(".jpg", img)
    return buffer.tobytes()


class WebServer:
    """Web 服务器封装"""

    def __init__(self, config, inspector):
        self.config = config
        self.inspector = inspector
        self.app = create_app(config, inspector)
        self._thread = None

    def start(self, blocking=False):
        """启动 Web 服务"""
        host = self.config.get("web.host", "0.0.0.0")
        port = self.config.get("web.port", 8080)
        debug = self.config.get("web.debug", False)

        if blocking:
            self.app.run(host=host, port=port, debug=debug, threaded=True)
        else:
            self._thread = threading.Thread(
                target=self.app.run,
                kwargs={"host": host, "port": port, "debug": False, "threaded": True},
                daemon=True,
            )
            self._thread.start()
            print(f"[信息] Web 服务已启动: http://{host}:{port}")
