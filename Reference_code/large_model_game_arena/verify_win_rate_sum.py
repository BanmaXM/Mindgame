#!/usr/bin/env python3
"""
验证胜率总和是否为100%的脚本
"""
import os
import json
from pathlib import Path
from typing import Dict, Any, List, Tuple


def verify_win_rate_sum(data_dir: str) -> float:
    """
    验证所有agent的胜率总和是否为100%
    
    Args:
        data_dir: 修复后的游戏日志文件目录
        
    Returns:
        胜率总和
    """
    agent_stats = {}
    
    # 遍历所有游戏日志文件
    batch_runs_dir = Path(data_dir) / "batch_runs"
    if not batch_runs_dir.exists():
        print(f"错误：找不到目录 {batch_runs_dir}")
        return 0.0
    
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
                    
                    # 初始化agent统计（如果尚未初始化）
                    for agent_id in player_agent_mapping.values():
                        if agent_id not in agent_stats:
                            agent_stats[agent_id] = [0.0, 0]  # [wins, total_games]，wins改为浮点数
                    
                    # 更新每个agent的统计信息
                    for player_id, agent_id in player_agent_mapping.items():
                        agent_stats[agent_id][1] += 1  # 增加总游戏次数
                        
                        # 检查该agent是否是获胜者之一
                        if player_id in winners:
                            # 根据平局人数计算胜场
                            num_winners = len(winners)
                            if num_winners == 1:
                                # 单人获胜，得1胜场
                                agent_stats[agent_id][0] += 1.0
                            elif num_winners == 2:
                                # 两人平局，各得0.5胜场
                                agent_stats[agent_id][0] += 0.5
                            elif num_winners == 3:
                                # 三人平局，各得0.33胜场
                                agent_stats[agent_id][0] += 0.33
                        
                except Exception as e:
                    print(f"处理文件 {file} 时出错: {e}")
                    continue
    
    # 计算胜率总和
    total_win_rate = 0.0
    print("\n=== 各agent胜率详情 ===")
    for agent_id, (wins, total_games) in agent_stats.items():
        win_rate = wins / total_games if total_games > 0 else 0.0
        total_win_rate += win_rate
        print(f"{agent_id}: {wins}/{total_games} ({win_rate:.2%})")
    
    return total_win_rate


def main():
    """
    主函数
    """
    # 设置修复后的游戏日志文件目录
    data_dir = "/home/syh/mindgames/large_model_game_arena/data/datafix"
    
    print("开始验证胜率总和...")
    
    # 验证胜率总和
    total_win_rate = verify_win_rate_sum(data_dir)
    
    # 打印结果
    print(f"\n=== 胜率总和 ===")
    print(f"总胜率: {total_win_rate:.2%}")
    
    if abs(total_win_rate - 1.0) < 0.01:  # 允许1%的误差
        print("✓ 胜率总和约为100%，验证通过！")
    else:
        print("✗ 胜率总和不为100%，验证失败！")


if __name__ == "__main__":
    main()