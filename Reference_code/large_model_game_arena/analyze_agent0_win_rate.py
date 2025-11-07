#!/usr/bin/env python3
"""
统计agent0胜率的脚本
"""
import os
import json
from pathlib import Path
from typing import Dict, Any, List, Tuple


def analyze_agent0_win_rate(data_dir: str) -> Tuple[int, int, float]:
    """
    分析agent0的胜率
    
    Args:
        data_dir: 修复后的游戏日志文件目录
        
    Returns:
        (agent0_wins, total_games, win_rate): agent0获胜次数、总游戏次数、胜率
    """
    agent0_wins = 0
    total_games = 0
    
    # 遍历所有游戏日志文件
    batch_runs_dir = Path(data_dir) / "batch_runs"
    if not batch_runs_dir.exists():
        print(f"错误：找不到目录 {batch_runs_dir}")
        return 0, 0, 0.0
    
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
                    
                    # 检查agent0是否是获胜者之一
                    agent0_is_winner = False
                    for player_id in winners:
                        agent_id = player_agent_mapping.get(player_id)
                        if agent_id == "agent_0":
                            agent0_is_winner = True
                            break
                    
                    total_games += 1
                    if agent0_is_winner:
                        agent0_wins += 1
                        
                except Exception as e:
                    print(f"处理文件 {file} 时出错: {e}")
                    continue
    
    # 计算胜率
    win_rate = agent0_wins / total_games if total_games > 0 else 0.0
    
    return agent0_wins, total_games, win_rate


def print_detailed_stats(data_dir: str):
    """
    打印详细的统计信息
    
    Args:
        data_dir: 修复后的游戏日志文件目录
    """
    batch_stats = {}
    
    # 遍历所有游戏日志文件
    batch_runs_dir = Path(data_dir) / "batch_runs"
    if not batch_runs_dir.exists():
        print(f"错误：找不到目录 {batch_runs_dir}")
        return
    
    for batch_run in batch_runs_dir.iterdir():
        if not batch_run.is_dir():
            continue
            
        batch_agent0_wins = 0
        batch_total_games = 0
        
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
                        continue
                    
                    # 确定获胜者
                    max_reward = max(rewards.values())
                    winners = [player_id for player_id, reward in rewards.items() if reward == max_reward]
                    
                    # 获取player_agent_mapping
                    player_agent_mapping = data.get("player_agent_mapping", {})
                    
                    # 检查agent0是否是获胜者之一
                    agent0_is_winner = False
                    for player_id in winners:
                        agent_id = player_agent_mapping.get(player_id)
                        if agent_id == "agent_0":
                            agent0_is_winner = True
                            break
                    
                    batch_total_games += 1
                    if agent0_is_winner:
                        batch_agent0_wins += 1
                        
                except Exception as e:
                    continue
        
        if batch_total_games > 0:
            batch_win_rate = batch_agent0_wins / batch_total_games
            batch_stats[batch_run.name] = {
                "wins": batch_agent0_wins,
                "total": batch_total_games,
                "win_rate": batch_win_rate
            }
    
    # 打印批次统计信息
    print("\n=== 各批次统计信息 ===")
    for batch_name, stats in sorted(batch_stats.items()):
        print(f"{batch_name}: {stats['wins']}/{stats['total']} ({stats['win_rate']:.2%})")


def main():
    """
    主函数
    """
    # 设置修复后的游戏日志文件目录
    data_dir = "/home/syh/mindgames/large_model_game_arena/data/datafix"
    
    print("开始统计agent0的胜率...")
    
    # 分析agent0的胜率
    agent0_wins, total_games, win_rate = analyze_agent0_win_rate(data_dir)
    
    # 打印总体统计结果
    print("\n=== 总体统计结果 ===")
    print(f"Agent0获胜次数: {agent0_wins}")
    print(f"总游戏次数: {total_games}")
    print(f"Agent0胜率: {win_rate:.2%}")
    
    # 注释掉详细统计信息以使输出更简洁
    # print_detailed_stats(data_dir)


if __name__ == "__main__":
    main()