#!/bin/bash
# 设置Mind Games Challenge环境的脚本

echo "===== 设置Mind Games Challenge环境 ====="
cd /home/aiscuser/mindgames-starter-kit/
# 检查conda是否已安装
if ! command -v conda &> /dev/null; then
    echo "错误: 未找到conda. 请先安装Miniconda或Anaconda."
    exit 1
fi

# 创建新的conda环境
echo "创建新的conda环境: mind (Python 3.10)"
conda create -n mind python=3.10 -y

# 激活环境
echo "激活环境..."
source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate mind

# 安装依赖
echo "安装依赖..."
cd "$(dirname "$(dirname "$0")")"  # 移动到项目根目录
pip install -r requirements.txt

echo ""
echo "===== 环境设置完成! ====="
echo "现在您可以使用以下命令运行游戏:"
echo "bash examples/run_game.sh cli     # 命令行界面"
echo "bash examples/run_game.sh web     # 网页界面"
echo ""
echo "或者手动运行:"
echo "conda activate mind"
echo "python examples/human_vs_llm_example.py --game three_player_ipd  # 命令行界面"
echo "python src/webui.py                                              # 网页界面"
