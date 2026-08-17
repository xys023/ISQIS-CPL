# 糕点产线工业级智慧质检系统

> 广西科技师范学院 × 广西家乐轩食品有限公司 联合开发

## 项目简介

本系统是一套面向糕点生产产线的工业级 AI 视觉质检系统，通过摄像头实时采集产线图像，自动检测糕点中的异物（头发等）、破损、烤焦、尺寸异常等缺陷，替代传统人工目检，提升质检效率和一致性。

## 核心特性

- **开箱即用**：内置规则法检测引擎，无需训练即可运行
- **多平台支持**：笔记本电脑（Windows/Linux）+ RK3588/RK3572 边缘设备
- **可扩展架构**：支持 YOLOv8 深度学习模型和 RKNN NPU 加速推理
- **工业级界面**：Web 监控大屏，实时视频流 + 统计数据 + 缺陷分布
- **完整输出**：声光报警、检测日志、不合格品截图
- **演示模式**：无摄像头时自动生成模拟画面，方便需求对接

## 快速开始

### 1. 安装依赖

```bash
# Windows: 双击 deploy/install_laptop.bat
# Linux:
chmod +x deploy/install_laptop.sh
./deploy/install_laptop.sh
```

### 2. 启动系统

```bash
# Windows: 双击 deploy/start_windows.bat
# Linux:
source venv/bin/activate
python run.py
```

### 3. 访问监控页面

打开浏览器访问：http://localhost:8080

### 演示模式（无摄像头）

```bash
python run.py --demo
```

## 项目结构

```
pastry_quality_inspection/
├── run.py                    # 主启动入口
├── config.yaml               # 配置文件
├── requirements.txt          # Python依赖
├── README.md                 # 项目说明
├── src/
│   ├── config.py             # 配置管理
│   ├── camera/               # 摄像头采集模块
│   │   ├── base.py           # 摄像头基类
│   │   ├── webcam.py         # USB/笔记本摄像头
│   │   ├── gstreamer.py      # RK3588 GStreamer硬解码
│   │   └── video_file.py     # 视频文件输入
│   ├── detection/            # 检测引擎模块
│   │   ├── base.py           # 检测器基类
│   │   ├── rule_based.py     # 规则法质检（开箱即用）
│   │   ├── yolo_detector.py  # YOLO深度学习检测
│   │   ├── rknn_detector.py  # RKNN NPU检测
│   │   └── demo_simulator.py # 演示模拟器
│   ├── inspection/           # 质检主流程
│   │   └── inspector.py      # 质检控制器
│   ├── web/                  # Web服务与前端
│   │   ├── app.py            # Flask应用
│   │   └── static/           # 前端静态文件
│   ├── output/               # 输出模块
│   │   ├── alarm.py          # 报警管理
│   │   ├── logger.py         # 检测日志
│   │   └── exporter.py       # 数据导出/截图
│   └── utils/                # 工具模块
│       ├── drawing.py        # 可视化绘制
│       └── timing.py         # 帧率统计
├── data/
│   ├── snapshots/            # 不合格品截图
│   ├── logs/                 # 检测日志
│   └── models/               # AI模型文件
├── deploy/                   # 部署脚本
│   ├── install_laptop.sh     # 笔记本一键安装(Linux)
│   ├── install_laptop.bat    # 笔记本一键安装(Windows)
│   ├── start_windows.bat     # Windows启动脚本
│   ├── install_rk3588.sh     # RK3588一键安装
│   ├── rk3588.service        # systemd服务
│   └── convert_to_rknn.py    # 模型转换脚本
├── docs/                     # 文档
│   ├── 部署教程.md           # 小白级部署教程
│   ├── 硬件选型指南.md       # 硬件选型参考
│   └── 模型训练指南.md       # AI模型训练指导
└── tests/
    └── test_smoke.py         # 冒烟测试
```

## 检测引擎说明

| 引擎 | 说明 | 精度 | 速度 | 适用阶段 |
|------|------|------|------|----------|
| rule_based | 规则法，颜色/形状/轮廓分析 | 中等 | 快 | 初期演示、无训练数据 |
| yolo | YOLOv8深度学习 | 高 | 中 | 笔记本/工控机部署 |
| rknn | RK3588 NPU推理 | 高 | 很快 | 产线实际部署 |
| demo | 合成模拟画面 | - | - | 无实物演示 |

## 技术栈

- **后端**：Python 3.9+ / Flask / OpenCV
- **前端**：原生 HTML/CSS/JavaScript（工业深色主题）
- **AI推理**：Ultralytics YOLOv8 / RKNN Lite 2
- **硬件平台**：x86 笔记本 / RK3588 / RK3576

## 文档

- [部署教程](docs/部署教程.md) - 零基础部署指南
- [硬件选型指南](docs/硬件选型指南.md) - 硬件采购参考
- [模型训练指南](docs/模型训练指南.md) - AI模型训练与部署

## 许可证

本项目为校企合作开发项目，仅供广西科技师范学院与广西家乐轩食品有限公司内部使用。
