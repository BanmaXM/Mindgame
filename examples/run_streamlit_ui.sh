#!/bin/bash

# 运行Streamlit Mind Games WebUI
# 用法: bash run_streamlit_ui.sh

# 切换到项目根目录
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

# 确保已激活conda环境
source ~/miniconda3/etc/profile.d/conda.sh
conda activate mind

# 检查是否已安装streamlit和openai
if ! python -c "import streamlit" &> /dev/null; then
    echo "安装streamlit..."
    pip install streamlit
fi

if ! python -c "import openai" &> /dev/null; then
    echo "安装openai..."
    pip install openai
fi

# 运行Streamlit应用
echo "===== 启动 Streamlit Mind Games WebUI ====="
streamlit run src/streamlit_ui.py
