#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
糕点产线工业级智慧质检系统 - 主启动入口

使用方法：
    python run.py                  # 使用默认配置启动
    python run.py --config xxx.yaml # 指定配置文件
    python run.py --demo           # 演示模式（无摄像头时使用）
    python run.py --engine rule_based  # 指定检测引擎

启动后访问：http://localhost:8080
"""
import os
import sys
import argparse
import signal

# 确保项目根目录在 Python 路径中
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)

from src.config import get_config
from src.inspection import QualityInspector
from src.web import WebServer


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="糕点产线工业级智慧质检系统",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python run.py                          # 默认启动
  python run.py --demo                   # 演示模式（合成画面）
  python run.py --engine yolo            # 使用YOLO模型
  python run.py --camera 1               # 使用第2号摄像头
  python run.py --port 9000              # 指定Web端口
        """
    )
    parser.add_argument("--config", type=str, default=None,
                        help="配置文件路径（默认: config.yaml）")
    parser.add_argument("--demo", action="store_true",
                        help="演示模式：合成模拟画面，无需摄像头")
    parser.add_argument("--engine", type=str, default=None,
                        choices=["rule_based", "yolo", "rknn", "demo"],
                        help="检测引擎类型")
    parser.add_argument("--camera", type=str, default=None,
                        help="摄像头设备编号或视频文件路径")
    parser.add_argument("--port", type=int, default=None,
                        help="Web服务端口")
    parser.add_argument("--host", type=str, default=None,
                        help="Web服务监听地址")
    return parser.parse_args()


def main():
    args = parse_args()

    # 加载配置
    config_path = args.config or os.path.join(PROJECT_ROOT, "config.yaml")
    config = get_config(config_path)

    # 命令行参数覆盖配置
    if args.demo:
        config.set("detection.engine", "demo")
        config.set("camera.source_type", "webcam")  # 演示模式也尝试开摄像头，失败则用合成帧
    if args.engine:
        config.set("detection.engine", args.engine)
    if args.camera:
        # 尝试转为数字（设备编号），失败则作为文件路径
        try:
            config.set("camera.device", int(args.camera))
        except ValueError:
            config.set("camera.device", args.camera)
            config.set("camera.source_type", "video")
    if args.port:
        config.set("web.port", args.port)
    if args.host:
        config.set("web.host", args.host)

    # 打印启动信息
    print("=" * 60)
    print(f"  {config.get('system.name', '糕点质检系统')} v{config.get('system.version', '1.0.0')}")
    print(f"  {config.get('system.company', '')}")
    print("=" * 60)
    print(f"  检测引擎: {config.get('detection.engine')}")
    print(f"  摄像头类型: {config.get('camera.source_type')}")
    print(f"  摄像头设备: {config.get('camera.device')}")
    print(f"  Web地址: http://{config.get('web.host')}:{config.get('web.port')}")
    print("=" * 60)

    # 创建质检实例
    inspector = QualityInspector(config)

    # 优雅退出处理
    def signal_handler(sig, frame):
        print("\n[信息] 收到退出信号，正在停止系统...")
        inspector.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # 启动质检流水线
    try:
        inspector.start()
    except Exception as e:
        print(f"[错误] 质检系统启动失败: {e}")
        print("[提示] 如果摄像头不可用，请使用 --demo 参数启动演示模式")
        sys.exit(1)

    # 启动 Web 服务（阻塞模式）
    web_server = WebServer(config, inspector)
    try:
        web_server.start(blocking=True)
    except KeyboardInterrupt:
        print("\n[信息] 用户中断，正在停止系统...")
    finally:
        inspector.stop()


if __name__ == "__main__":
    main()
