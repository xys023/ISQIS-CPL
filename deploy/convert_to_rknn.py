#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YOLOv8 模型转 RKNN 格式脚本（在 x86 电脑上运行）

用途：将训练好的 YOLOv8 模型（.pt）转换为 RK3588/RK3572 NPU 可推理的 .rknn 格式

使用前提：
1. 在 x86 电脑上安装 rknn-toolkit2（不是 rknnlite2！）
   pip install rknn-toolkit2 -i https://pypi.rock-chips.com/simple/
2. 已有训练好的 YOLOv8 模型（.pt 格式）
3. 使用 ultralytics 导出 ONNX：
   yolo export model=best.pt format=onnx opset=12 imgsz=640

使用方法：
    python convert_to_rknn.py --onnx best.onnx --output best.rknn
    python convert_to_rknn.py --pt best.pt --output best.rknn

注意：
- 本脚本必须在 x86 电脑上运行（RK3588 上只能推理不能转换）
- 转换后将 .rknn 文件放到 RK3588 的 data/models/ 目录
"""
import os
import argparse
import sys


def convert_onnx_to_rknn(onnx_path, output_path, dataset_path=None):
    """
    将 ONNX 模型转换为 RKNN 格式

    参数:
        onnx_path: ONNX 模型路径
        output_path: 输出 RKNN 路径
        dataset_path: 量化数据集路径（文本文件，每行一张图片路径）
    """
    try:
        from rknn.api import RKNN
    except ImportError:
        print("[错误] 未安装 rknn-toolkit2")
        print("  安装命令: pip install rknn-toolkit2 -i https://pypi.rock-chips.com/simple/")
        print("  注意：必须在 x86 电脑上安装，RK3588 上安装的是 rknnlite2（仅推理）")
        sys.exit(1)

    if not os.path.exists(onnx_path):
        print(f"[错误] ONNX 文件不存在: {onnx_path}")
        sys.exit(1)

    rknn = RKNN(verbose=True)

    # 1. 配置
    print("[1/4] 配置 RKNN...")
    rknn.config(
        mean_values=[[0, 0, 0]],
        std_values=[[255, 255, 255]],
        target_platform="rk3588",  # RK3572 也用 rk3588 目标平台
        quant_img_RGB2BGR=False,
        optimization_level=3,
    )

    # 2. 加载 ONNX
    print("[2/4] 加载 ONNX 模型...")
    ret = rknn.load_onnx(model=onnx_path)
    if ret != 0:
        print(f"[错误] ONNX 加载失败，错误码: {ret}")
        sys.exit(1)

    # 3. 构建（量化）
    print("[3/4] 构建 RKNN 模型（INT8量化）...")
    if dataset_path and os.path.exists(dataset_path):
        print(f"  使用量化数据集: {dataset_path}")
        ret = rknn.build(do_quantization=True, dataset=dataset_path)
    else:
        print("  [警告] 未提供量化数据集，使用默认量化（精度可能降低）")
        print("  建议准备 100~300 张产线图片作为量化数据集")
        ret = rknn.build(do_quantization=False)

    if ret != 0:
        print(f"[错误] 模型构建失败，错误码: {ret}")
        sys.exit(1)

    # 4. 导出
    print(f"[4/4] 导出 RKNN 模型: {output_path}")
    ret = rknn.export_rknn(output_path)
    if ret != 0:
        print(f"[错误] 导出失败，错误码: {ret}")
        sys.exit(1)

    rknn.release()
    print(f"\n[成功] 模型转换完成: {output_path}")
    print(f"  文件大小: {os.path.getsize(output_path) / 1024 / 1024:.2f} MB")
    print("\n下一步：")
    print(f"  1. 将 {output_path} 复制到 RK3588 的 data/models/ 目录")
    print(f"  2. 修改 config.yaml: detection.engine: rknn")
    print(f"  3. 修改 config.yaml: detection.rknn.model_path: data/models/{os.path.basename(output_path)}")


def export_pt_to_onnx(pt_path, onnx_path, imgsz=640):
    """使用 ultralytics 将 .pt 导出为 ONNX"""
    try:
        from ultralytics import YOLO
    except ImportError:
        print("[错误] 未安装 ultralytics")
        print("  安装命令: pip install ultralytics")
        sys.exit(1)

    print(f"  导出 {pt_path} -> {onnx_path}")
    model = YOLO(pt_path)
    model.export(format="onnx", opset=12, imgsz=imgsz, simplify=True)
    # ultralytics 导出的文件名通常是 best.onnx
    generated = pt_path.replace(".pt", ".onnx")
    if generated != onnx_path and os.path.exists(generated):
        os.rename(generated, onnx_path)
    return onnx_path


def main():
    parser = argparse.ArgumentParser(description="YOLOv8 模型转 RKNN 格式")
    parser.add_argument("--pt", type=str, help="YOLOv8 .pt 模型路径")
    parser.add_argument("--onnx", type=str, help="ONNX 模型路径（如果已有ONNX）")
    parser.add_argument("--output", type=str, default="best.rknn", help="输出 RKNN 路径")
    parser.add_argument("--dataset", type=str, help="量化数据集文件路径")
    parser.add_argument("--imgsz", type=int, default=640, help="模型输入尺寸")
    args = parser.parse_args()

    if not args.pt and not args.onnx:
        parser.error("必须提供 --pt 或 --onnx 参数")

    # 如果提供 .pt，先导出为 ONNX
    onnx_path = args.onnx
    if args.pt:
        onnx_path = args.pt.replace(".pt", ".onnx")
        if not os.path.exists(onnx_path):
            export_pt_to_onnx(args.pt, onnx_path, args.imgsz)

    convert_onnx_to_rknn(onnx_path, args.output, args.dataset)


if __name__ == "__main__":
    main()
