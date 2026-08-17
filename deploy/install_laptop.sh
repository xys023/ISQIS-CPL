#!/bin/bash
# ============================================================
# 糕点产线工业级智慧质检系统 - 笔记本电脑一键安装脚本
# 适用系统：Ubuntu 20.04/22.04、Debian 11/12
# Windows 用户请参考 docs/部署教程.md 的 Windows 章节
#
# 使用方法：
#   chmod +x install_laptop.sh
#   ./install_laptop.sh
# ============================================================

set -e

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
echo "=============================================="
echo "  糕点质检系统 - 笔记本环境安装"
echo "  项目目录: $PROJECT_DIR"
echo "=============================================="

# 1. 检查 Python 版本
echo "[1/5] 检查 Python 环境..."
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    echo "  检测到 Python $PYTHON_VERSION"
    if python3 -c "import sys; exit(0 if sys.version_info >= (3,9) else 1)"; then
        echo "  Python 版本符合要求 (>=3.9)"
    else
        echo "  [错误] Python 版本过低，请安装 Python 3.9 或更高版本"
        exit 1
    fi
else
    echo "  [错误] 未检测到 Python3，请先安装 Python"
    exit 1
fi

# 2. 安装系统依赖
echo "[2/5] 安装系统依赖..."
if command -v apt-get &> /dev/null; then
    sudo apt-get update -qq
    sudo apt-get install -y -qq python3-pip python3-venv libgl1-mesa-glx libglib2.0-0 2>/dev/null || true
    echo "  系统依赖安装完成"
else
    echo "  [提示] 非 Debian/Ubuntu 系统，请手动安装 libgl1 和 libglib2.0"
fi

# 3. 创建虚拟环境
echo "[3/5] 创建 Python 虚拟环境..."
cd "$PROJECT_DIR"
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "  虚拟环境创建完成: $PROJECT_DIR/venv"
else
    echo "  虚拟环境已存在，跳过创建"
fi

# 4. 激活虚拟环境并安装依赖
echo "[4/5] 安装 Python 依赖包..."
source venv/bin/activate
pip install --upgrade pip -q
pip install -r requirements.txt -q
echo "  依赖安装完成"

# 5. 创建数据目录
echo "[5/5] 初始化数据目录..."
mkdir -p data/snapshots data/logs data/models
echo "  数据目录创建完成"

echo ""
echo "=============================================="
echo "  安装完成！"
echo "=============================================="
echo ""
echo "启动系统："
echo "  cd $PROJECT_DIR"
echo "  source venv/bin/activate"
echo "  python run.py"
echo ""
echo "演示模式（无摄像头时）："
echo "  python run.py --demo"
echo ""
echo "启动后在浏览器访问: http://localhost:8080"
echo ""
