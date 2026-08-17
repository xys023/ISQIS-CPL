#!/usr/bin/env python3
"""端到端功能测试：启动demo模式服务，测试所有API端点"""
import os
import sys
import time
import json
import urllib.request

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

PORT = 8300
BASE = f"http://localhost:{PORT}"

def test_endpoint(path, timeout=5):
    try:
        with urllib.request.urlopen(f"{BASE}{path}", timeout=timeout) as resp:
            data = resp.read()
            return resp.status, data
    except Exception as e:
        return 0, str(e).encode()

def main():
    print("=" * 50)
    print("  端到端功能测试")
    print("=" * 50)

    # 导入并启动
    from src.config import get_config
    from src.inspection import QualityInspector
    from src.web import WebServer

    config = get_config(os.path.join(PROJECT_ROOT, "config.yaml"))
    config.set("detection.engine", "demo")
    config.set("web.port", PORT)
    config.set("web.host", "127.0.0.1")

    inspector = QualityInspector(config)
    inspector.start()
    web = WebServer(config, inspector)
    web.start(blocking=False)

    # 等待启动
    time.sleep(3)

    all_pass = True

    # 测试首页
    status, _ = test_endpoint("/")
    print(f"[首页] HTTP {status} {'✓' if status==200 else '✗'}")
    all_pass &= status == 200

    # 测试系统信息
    status, data = test_endpoint("/api/system")
    if status == 200:
        info = json.loads(data)
        print(f"[系统信息] {info.get('name')} 引擎:{info.get('engine')} ✓")
    else:
        print(f"[系统信息] HTTP {status} ✗")
        all_pass = False

    # 等待检测运行
    time.sleep(3)

    # 测试统计
    status, data = test_endpoint("/api/stats")
    if status == 200:
        stats = json.loads(data)
        print(f"[统计] 总数:{stats['total']} 合格:{stats['passed']} 不合格:{stats['defective']} FPS:{stats['avg_fps']} ✓")
    else:
        print(f"[统计] HTTP {status} ✗")
        all_pass = False

    # 测试检测结果
    status, data = test_endpoint("/api/result")
    if status == 200:
        result = json.loads(data)
        print(f"[检测结果] 不合格:{result['is_defective']} 缺陷数:{len(result['defects'])} 推理:{result['inference_time']:.1f}ms ✓")
    else:
        print(f"[检测结果] HTTP {status} ✗")
        all_pass = False

    # 测试视频流（短时间读取）
    try:
        req = urllib.request.urlopen(f"{BASE}/video_feed", timeout=3)
        chunk = req.read(2048)
        req.close()
        has_frame = b"image/jpeg" in chunk
        print(f"[视频流] 收到{len(chunk)}字节 {'✓' if has_frame else '✗'}")
        all_pass &= has_frame
    except Exception as e:
        print(f"[视频流] 异常: {e} ✗")
        all_pass = False

    # 测试静态资源
    status, _ = test_endpoint("/static/css/style.css")
    print(f"[CSS] HTTP {status} {'✓' if status==200 else '✗'}")
    all_pass &= status == 200

    status, _ = test_endpoint("/static/js/dashboard.js")
    print(f"[JS] HTTP {status} {'✓' if status==200 else '✗'}")
    all_pass &= status == 200

    # 测试配置API
    status, data = test_endpoint("/api/config")
    if status == 200:
        cfg = json.loads(data)
        print(f"[配置] 引擎:{cfg['detection']['engine']} ✓")
    else:
        print(f"[配置] HTTP {status} ✗")
        all_pass = False

    # 清理
    inspector.stop()

    print("\n" + "=" * 50)
    if all_pass:
        print("  所有端到端测试通过！")
    else:
        print("  部分测试失败，请检查！")
    print("=" * 50)
    return 0 if all_pass else 1

if __name__ == "__main__":
    sys.exit(main())
