#!/usr/bin/env python3
"""
分析agent0使用不同prompt的胜率
"""
import os
import json
from pathlib import Path
from typing import Dict, Any, List, Tuple


def analyze_agent0_prompts(data_dir: str) -> Dict[str, Tuple[float, int, float]]:
    """
    分析agent0使用不同prompt的胜率
    
    Args:
        data_dir: 修复后的游戏日志文件目录
        
    Returns:
        字典：{prompt: (wins, total_games, win_rate)}
    """
    prompt_stats = {}
    
    # 遍历所有游戏日志文件
    batch_runs_dir = Path(data_dir) / "batch_runs"
    if not batch_runs_dir.exists():
        print(f"错误：找不到目录 {batch_runs_dir}")
        return {}
    
    for batch_run in batch_runs_dir.iterdir():
        if not batch_run.is_dir():
            continue
            
        for timestamp_dir in batch_run.iterdir():
            if not timestamp_dir.is_dir():
                continue
                
            for file in timestamp_dir.iterdir():
                if not file.is_file() or not file.name.endswith("_three_player_ipd.json"):
                    continue
                
                try:
                    # 读取游戏日志文件
                    with open(file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    # 获取final_results
                    final_results = data.get("final_results", {})
                    rewards = final_results.get("rewards", {})
                    
                    if not rewards:
                        print(f"警告：文件 {file} 中没有找到rewards信息")
                        continue
                    
                    # 确定获胜者
                    max_reward = max(rewards.values())
                    winners = [player_id for player_id, reward in rewards.items() if reward == max_reward]
                    
                    # 获取player_agent_mapping
                    player_agent_mapping = data.get("player_agent_mapping", {})
                    
                    # 获取agents信息
                    agents = data.get("agents", {})
                    
                    # 找到agent0的player_id和prompt
                    agent0_player_id = None
                    agent0_prompt = None
                    
                    for player_id, agent_id in player_agent_mapping.items():
                        if agent_id == "agent_0":
                            agent0_player_id = player_id
                            agent0_prompt = agents.get(agent_id, {}).get("prompt", "Unknown")
                            break
                    
                    if agent0_player_id is None:
                        print(f"警告：文件 {file} 中没有找到agent_0")
                        continue
                    
                    # 初始化prompt统计（如果尚未初始化）
                    if agent0_prompt not in prompt_stats:
                        prompt_stats[agent0_prompt] = [0.0, 0]  # [wins, total_games]，wins改为浮点数
                    
                    # 更新统计信息
                    prompt_stats[agent0_prompt][1] += 1  # 增加总游戏次数
                    
                    # 检查agent0是否是获胜者之一
                    if agent0_player_id in winners:
                        # 根据平局人数计算胜场
                        num_winners = len(winners)
                        if num_winners == 1:
                            # 单人获胜，得1胜场
                            prompt_stats[agent0_prompt][0] += 1.0
                        elif num_winners == 2:
                            # 两人平局，各得0.5胜场
                            prompt_stats[agent0_prompt][0] += 0.5
                        elif num_winners == 3:
                            # 三人平局，各得0.33胜场
                            prompt_stats[agent0_prompt][0] += 0.33
                        
                except Exception as e:
                    print(f"处理文件 {file} 时出错: {e}")
                    continue
    
    # 计算胜率
    result = {}
    for prompt, (wins, total_games) in prompt_stats.items():
        win_rate = wins / total_games if total_games > 0 else 0.0
        result[prompt] = (wins, total_games, win_rate)
    
    return result


def main():
    """
    主函数
    """
    # 设置修复后的游戏日志文件目录
    data_dir = "/home/syh/mindgames/large_model_game_arena/data/datafix"
    
    print("开始分析agent0使用不同prompt的胜率...")
    
    # 分析agent0使用不同prompt的胜率
    prompt_win_rates = analyze_agent0_prompts(data_dir)
    
    # 打印统计结果
    print("\n=== Agent0不同Prompt的胜率统计结果 ===")
    for prompt, (wins, total_games, win_rate) in sorted(prompt_win_rates.items()):
        print(f"Prompt '{prompt}': {wins}/{total_games} ({win_rate:.2%})")
    
    # 计算总体胜率
    total_wins = sum(wins for wins, _, _ in prompt_win_rates.values())
    total_games = sum(total_games for _, total_games, _ in prompt_win_rates.values())
    overall_win_rate = total_wins / total_games if total_games > 0 else 0.0
    
    print(f"\n=== Agent0总体胜率 ===")
    print(f"总体: {total_wins}/{total_games} ({overall_win_rate:.2%})")


if __name__ == "__main__":
    main()