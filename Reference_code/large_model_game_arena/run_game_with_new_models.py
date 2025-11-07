#!/usr/bin/env python3
"""
使用新配置的模型进行游戏的示例脚本
"""

import os
import sys
import argparse
from pathlib import Path

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agents.agent_0 import Agent0
from agents.agent_1 import Agent1
from src.utils.game_manager import GameManager

def run_game_with_models(args):
    """使用指定模型运行游戏"""
    print(f"🚀 使用模型进行游戏: {args.game}")
    print("=" * 50)
    
    # 初始化agents
    print(f"🔄 初始化我们的Agent (使用 {args.model_0})...")
    agent_0 = Agent0(game_type=args.game, 
                     model_name=args.model_0, 
                     prompt_name=args.prompt_0)
    print("✅ 我们的Agent初始化成功!")
    print(f"   模型: {agent_0.get_model_info()['model_name']}")
    print(f"   提示: {agent_0.get_model_info()['prompt_name']}")
    
    print(f"🔄 初始化对手Agent (使用 {args.model_1})...")
    agent_1 = Agent1(game_type=args.game, 
                     model_name=args.model_1, 
                     prompt_name=args.prompt_1)
    print("✅ 对手Agent初始化成功!")
    print(f"   模型: {agent_1.get_model_info()['model_name']}")
    print(f"   提示: {agent_1.get_model_info()['prompt_name']}")
    
    # 设置游戏管理器
    print(f"🎯 初始化{args.game}游戏环境...")
    manager = GameManager()
    manager.setup_game(args.game)
    
    # 添加agents
    manager.add_agent(agent_0)  # Player 0
    manager.add_agent(agent_1)  # Player 1
    
    # 运行游戏
    print("🎮 开始游戏...")
    manager.run_game(rounds=args.rounds)
    
    print("✅ 游戏完成!")

def main():
    parser = argparse.ArgumentParser(description="使用新配置的模型进行游戏")
    parser.add_argument("--game", type=str, default="colonel_blotto", 
                       choices=["colonel_blotto", "three_player_ipd"],
                       help="游戏类型")
    parser.add_argument("--model_0", type=str, default="api/openai-gpt-5",
                       help="我们的Agent使用的模型")
    parser.add_argument("--model_1", type=str, default="api/x-ai-grok-4-fast-free",
                       help="对手Agent使用的模型")
    parser.add_argument("--prompt_0", type=str, default="advanced_strategy",
                       help="我们的Agent使用的提示")
    parser.add_argument("--prompt_1", type=str, default="simple_role_play",
                       help="对手Agent使用的提示")
    parser.add_argument("--rounds", type=int, default=3,
                       help="游戏轮数")
    
    args = parser.parse_args()
    
    run_game_with_models(args)

if __name__ == "__main__":
    main()