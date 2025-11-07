#!/bin/bash
# Mind Games Challenge游戏启动脚本

# 确保在正确的目录
cd "$(dirname "$(dirname "$0")")"  # 移动到项目根目录

# 激活conda环境
source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate mind

# 检查是否有参数
if [ $# -eq 0 ]; then
    echo "错误: 请指定要运行的界面类型 (cli 或 web)"
    echo "用法: bash examples/run_game.sh [cli|web] [额外参数]"
    exit 1
fi

# 根据参数选择启动方式
case "$1" in
    cli)
        shift  # 移除第一个参数(cli)
        echo "===== 启动命令行界面 ====="
        python examples/human_vs_llm_example.py "$@"
        ;;
    web)
        shift  # 移除第一个参数(web)
        echo "===== 启动网页界面 ====="
        python src/webui.py "$@"
        ;;
    *)
        echo "错误: 未知的界面类型: $1"
        echo "用法: bash examples/run_game.sh [cli|web] [额外参数]"
        exit 1
        ;;
esac
