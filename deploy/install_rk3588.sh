#!/bin/bash
# ============================================================
# 糕点产线工业级智慧质检系统 - RK3588/RK3572 一键安装脚本
# 适用系统：Debian 11、Ubuntu 20.04（RK3588 官方镜像）
#
# 使用方法：
#   chmod +x install_rk3588.sh
#   sudo ./install_rk3588.sh
# ============================================================

set -e

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
echo "=============================================="
echo "  糕点质检系统 - RK3588/RK3572 边缘部署安装"
echo "  项目目录: $PROJECT_DIR"
echo "=============================================="

# 1. 检查是否为 ARM 架构
echo "[1/7] 检查硬件架构..."
ARCH=$(uname -m)
if [[ "$ARCH" != "aarch64" && "$ARCH" != "arm64" ]]; then
    echo "  [警告] 当前架构为 $ARCH，非 ARM64，可能不是 RK3588 设备"
    read -p "  是否继续？(y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
else
    echo "  架构: $ARCH (符合要求)"
fi

# 2. 安装系统依赖
echo "[2/7] 安装系统依赖..."
apt-get update -qq
apt-get install -y -qq python3 python3-pip python3-venv \
    libgl1-mesa-glx libglib2.0-0 libgstreamer1.0-0 \
    gstreamer1.0-plugins-base gstreamer1.0-plugins-good \
    gstreamer1.0-plugins-bad v4l-utils i2c-tools \
    2>/dev/null || true
echo "  系统依赖安装完成"

# 3. 创建虚拟环境
echo "[3/7] 创建 Python 虚拟环境..."
cd "$PROJECT_DIR"
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "  虚拟环境创建完成"
else
    echo "  虚拟环境已存在"
fi

# 4. 安装基础 Python 依赖
echo "[4/7] 安装 Python 基础依赖..."
source venv/bin/activate
pip install --upgrade pip -q
pip install -r requirements.txt -q
echo "  基础依赖安装完成"

# 5. 安装 RKNN 运行时（NPU 推理）
echo "[5/7] 安装 RKNN 运行时（NPU推理）..."
if pip install rknnlite2 --index-url https://pypi.rock-chips.com/simple/ -q 2>/dev/null; then
    echo "  RKNN 运行时安装成功"
else
    echo "  [警告] RKNN 运行时安装失败"
    echo "  可手动执行: pip install rknnlite2 --index-url https://pypi.rock-chips.com/simple/"
    echo "  或从瑞芯微官方 GitHub 下载 whl 包安装"
fi

# 6. 配置 GPIO 权限
echo "[6/7] 配置 GPIO 权限..."
if ! getent group gpio >/dev/null 2>&1; then
    groupadd -f gpio
fi
usermod -aG gpio "$SUDO_USER" 2>/dev/null || true
echo "  GPIO 权限已配置（用户: ${SUDO_USER:-root}）"

# 7. 安装 systemd 服务
echo "[7/7] 配置开机自启服务..."
SERVICE_FILE="$PROJECT_DIR/deploy/rk3588.service"
if [ -f "$SERVICE_FILE" ]; then
    # 替换路径占位符
    sed "s|{{PROJECT_DIR}}|$PROJECT_DIR|g" "$SERVICE_FILE" > /etc/systemd/system/pastry-inspection.service
    systemctl daemon-reload
    systemctl enable pastry-inspection.service 2>/dev/null || true
    echo "  systemd 服务已配置（开机自启）"
    echo "  启动: sudo systemctl start pastry-inspection"
    echo "  状态: sudo systemctl status pastry-inspection"
    echo "  停止: sudo systemctl stop pastry-inspection"
    echo "  日志: journalctl -u pastry-inspection -f"
fi

# 创建数据目录
mkdir -p data/snapshots data/logs data/models

echo ""
echo "=============================================="
echo "  RK3588 部署完成！"
echo "=============================================="
echo ""
echo "手动启动："
echo "  cd $PROJECT_DIR"
echo "  source venv/bin/activate"
echo "  python run.py --engine rknn"
echo ""
echo "配置文件: config.yaml"
echo "  - camera.source_type: gstreamer (MIPI摄像头)"
echo "  - detection.engine: rknn (NPU推理)"
echo "  - alarm.methods: gpio (声光报警)"
echo ""
