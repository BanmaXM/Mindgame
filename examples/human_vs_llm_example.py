#!/usr/bin/env python
"""
示例脚本：演示如何使用 GameManager 进行人类与 LLM 的对战
支持本地Hugging Face模型和OpenAI API
"""

import sys
import os
import argparse
import time
from typing import Dict, Any

# 添加项目根目录到 Python 路径
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from src.game_manager import GameManager
from src.agent import LLMAgent, OpenAIAgent

def print_colored(text: str, color: str = "white") -> None:
    """打印彩色文本"""
    colors = {
        "red": "\033[91m",
        "green": "\033[92m",
        "yellow": "\033[93m",
        "blue": "\033[94m",
        "magenta": "\033[95m",
        "cyan": "\033[96m",
        "white": "\033[97m",
        "reset": "\033[0m"
    }
    print(f"{colors.get(color, colors['white'])}{text}{colors['reset']}")

def observation_callback(player_id: int, observation: str) -> None:
    """处理观察事件"""
    print_colored(f"\n===== 玩家 {player_id} 的观察 =====", "blue")
    print(observation)
    print_colored("=" * 40, "blue")

def action_callback(player_id: int, action: str) -> None:
    """处理动作事件"""
    print_colored(f"玩家 {player_id} 的动作: {action}", "green")

def step_complete_callback(done: bool, info: Dict[str, Any]) -> None:
    """处理步骤完成事件"""
    if done:
        print_colored("\n游戏结束！", "yellow")
    time.sleep(0.5)  # 添加短暂延迟，让UI更流畅

def setup_game(args) -> GameManager:
    """设置游戏环境和玩家"""
    manager = GameManager()
    
    # 设置游戏环境
    game_name = manager.setup_game(args.game)
    print_colored(f"设置游戏: {game_name}", "cyan")
    
    required_players = manager.get_required_players()
    print_colored(f"该游戏需要 {required_players} 名玩家", "cyan")
    
    # 确定人类和LLM玩家数量
    human_count = min(args.human_players, required_players)
    llm_count = required_players - human_count
    
    # 添加人类玩家
    for i in range(human_count):
        manager.add_human_player()
    
    # 添加LLM玩家
    for i in range(llm_count):
        if args.agent_type == "local":
            # 使用本地Hugging Face模型
            manager.add_llm_player(args.model_name)
            agent_type_str = f"本地LLM ({args.model_name})"
        else:
            # 使用OpenAI API
            agent = OpenAIAgent(model_name=args.openai_model, api_key=args.openai_api_key, base_url=args.openai_base_url)
            manager.add_agent(agent)
            agent_type_str = f"OpenAI API ({args.openai_model})"
    
    print_colored(f"添加了 {human_count} 名人类玩家和 {llm_count} 名{agent_type_str}玩家", "cyan")
    
    return manager

def main():
    parser = argparse.ArgumentParser(description="人类 vs LLM 游戏示例")
    parser.add_argument("--game", type=str, choices=["secret_mafia", "three_player_ipd", "colonel_blotto", "codenames"],
                       default="three_player_ipd", help="要玩的游戏")
    
    # 代理类型选择
    parser.add_argument("--agent-type", type=str, choices=["local", "openai"], default="local",
                      help="LLM代理类型: local (本地Hugging Face模型) 或 openai (OpenAI API)")
    
    # 本地模型参数
    parser.add_argument("--model_name", type=str, default="deepseek-ai/DeepSeek-R1-0528-Qwen3-8B",
                       help="本地Hugging Face LLM模型名称 (当agent-type=local时使用)")
    
    # OpenAI API参数
    parser.add_argument("--openai-model", type=str, default="gpt-3.5-turbo", 
                      help="OpenAI模型名称 (当agent-type=openai时使用)")
    parser.add_argument("--openai-api-key", type=str, default="", 
                      help="OpenAI API密钥 (当agent-type=openai时使用)")
    parser.add_argument("--openai-base-url", type=str, default="https://api.openai.com/v1", 
                      help="OpenAI API基础URL (当agent-type=openai时使用)")
    
    # 通用参数
    parser.add_argument("--human_players", type=int, default=1,
                       help="人类玩家数量，其余将由LLM填充")
    parser.add_argument("--seed", type=int, default=None,
                       help="随机种子")
    
    args = parser.parse_args()
    
    # 设置游戏
    manager = setup_game(args)
    
    # 设置回调
    callbacks = {
        "on_observation": observation_callback,
        "on_action": action_callback,
        "on_step_complete": step_complete_callback
    }
    
    # 启动游戏
    print_colored("\n正在启动游戏...", "yellow")
    manager.start_game(seed=args.seed)
    
    # 运行游戏
    result = manager.play_game(callbacks=callbacks)
    
    # 显示结果
    print_colored("\n===== 游戏结果 =====", "magenta")
    print(f"总步数: {result['steps']}")
    print(f"奖励: {result['rewards']}")
    
    # 确定胜者
    if "rewards" in result and result["rewards"]:
        max_reward = max(result["rewards"].values())
        winners = [player_id for player_id, reward in result["rewards"].items() if reward == max_reward]
        
        winner_types = []
        for winner in winners:
            if winner in result["human_players"]:
                winner_types.append("人类")
            else:
                winner_types.append("LLM")
        
        print_colored(f"胜者: 玩家 {winners} ({', '.join(winner_types)})", "yellow")

if __name__ == "__main__":
    main()
