#!/usr/bin/env python3
"""
统计批量运行结果的脚本
"""

import os
import json
import glob
from pathlib import Path

def parse_game_result(game_file):
    """解析游戏结果文件，确定胜者"""
    try:
        with open(game_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 查找所有回合的胜利信息
        alpha_wins = 0
        beta_wins = 0
        
        # 遍历所有步骤，统计每个回合的胜者
        for step in data["steps"]:
            if "observation" in step and "Winner:" in step["observation"]:
                lines = step["observation"].split('\n')
                for line in lines:
                    if "Winner:" in line:
                        winner = line.split("Winner: ")[1].strip()
                        if winner == "Commander Alpha":
                            alpha_wins += 1
                        elif winner == "Commander Beta":
                            beta_wins += 1
        
        # 如果没有找到明确的胜者信息，尝试从回合统计中获取
        if alpha_wins == 0 and beta_wins == 0:
            for step in data["steps"]:
                if "observation" in step and "Rounds Won - Commander Alpha:" in step["observation"]:
                    lines = step["observation"].split('\n')
                    for line in lines:
                        if "Rounds Won - Commander Alpha:" in line:
                            # 提取双方胜利回合数
                            parts = line.split("Rounds Won - Commander Alpha: ")[1].split(", Commander Beta: ")
                            alpha_wins = int(parts[0])
                            beta_wins = int(parts[1])
                            break
        
        # 确定胜者
        if alpha_wins > beta_wins:
            return 0  # Agent0 (Commander Alpha) 胜利
        elif beta_wins > alpha_wins:
            return 1  # Agent1 (Commander Beta) 胜利
        else:
            return None  # 平局
    except Exception as e:
        print(f"解析游戏文件 {game_file} 时出错: {e}")
        return None

def main():
    # 批量运行目录
    batch_dir = Path("/home/syh/mindgames/large_model_game_arena/data/colonel_blotto/batch_runs")
    
    # 统计信息
    stats = {
        "total_runs": 0,
        "agent0_wins": 0,
        "agent1_wins": 0,
        "draws": 0,
        "errors": 0,
        "agent0_models": {},
        "agent1_models": {},
        "results": []
    }
    
    # 遍历所有批量运行目录
    for batch_run_dir in sorted(batch_dir.glob("batch_run_*")):
        if not batch_run_dir.is_dir():
            continue
            
        # 遍历该批次下的所有游戏目录
        for game_dir in batch_run_dir.glob("*"):
            if not game_dir.is_dir():
                continue
                
            # 查找游戏数据文件
            game_files = list(game_dir.glob("*_colonel_blotto.json"))
            if not game_files:
                continue
                
            game_file = game_files[0]
            agent_info_file = game_dir / "agent_info.json"
            
            # 解析游戏结果
            winner = parse_game_result(game_file)
            
            # 读取agent信息
            agent_info = {}
            if agent_info_file.exists():
                try:
                    with open(agent_info_file, 'r', encoding='utf-8') as f:
                        agent_info = json.load(f)
                except Exception as e:
                    print(f"读取agent信息文件 {agent_info_file} 时出错: {e}")
            
            # 更新统计信息
            stats["total_runs"] += 1
            
            if winner == 0:
                stats["agent0_wins"] += 1
            elif winner == 1:
                stats["agent1_wins"] += 1
            else:
                stats["draws"] += 1
            
            # 记录模型使用情况
            if "agent_0" in agent_info and "model_name" in agent_info["agent_0"]:
                agent0_model = agent_info["agent_0"]["model_name"]
                if agent0_model not in stats["agent0_models"]:
                    stats["agent0_models"][agent0_model] = 0
                stats["agent0_models"][agent0_model] += 1
            
            if "agent_1" in agent_info and "model_name" in agent_info["agent_1"]:
                agent1_model = agent_info["agent_1"]["model_name"]
                if agent1_model not in stats["agent1_models"]:
                    stats["agent1_models"][agent1_model] = 0
                stats["agent1_models"][agent1_model] += 1
            
            # 保存单次结果
            run_number = int(batch_run_dir.name.split("_")[-1])
            stats["results"].append({
                "run_number": run_number,
                "winner": winner,
                "agent0_model": agent_info.get("agent_0", {}).get("model_name", ""),
                "agent1_model": agent_info.get("agent_1", {}).get("model_name", ""),
                "agent0_prompt": agent_info.get("agent_0", {}).get("prompt_name", ""),
                "agent1_prompt": agent_info.get("agent_1", {}).get("prompt_name", ""),
                "game_dir": str(game_dir)
            })
    
    # 计算胜率
    if stats["total_runs"] > 0:
        stats["agent0_win_rate"] = stats["agent0_wins"] / stats["total_runs"] * 100
        stats["agent1_win_rate"] = stats["agent1_wins"] / stats["total_runs"] * 100
        stats["draw_rate"] = stats["draws"] / stats["total_runs"] * 100
    else:
        stats["agent0_win_rate"] = 0
        stats["agent1_win_rate"] = 0
        stats["draw_rate"] = 0
    
    # 输出统计结果
    print("=" * 50)
    print("上校博弈批量运行统计结果")
    print("=" * 50)
    print(f"总运行次数: {stats['total_runs']}")
    print(f"Agent0胜率: {stats['agent0_win_rate']:.1f}% ({stats['agent0_wins']}/{stats['total_runs']})")
    print(f"Agent1胜率: {stats['agent1_win_rate']:.1f}% ({stats['agent1_wins']}/{stats['total_runs']})")
    print(f"平局率: {stats['draw_rate']:.1f}% ({stats['draws']}/{stats['total_runs']})")
    
    print("\nAgent0使用的模型:")
    for model, count in stats["agent0_models"].items():
        print(f"  {model}: {count}次")
    
    print("\nAgent1使用的模型:")
    for model, count in stats["agent1_models"].items():
        print(f"  {model}: {count}次")
    
    # 保存统计结果
    stats_file = batch_dir / "batch_stats_final.json"
    with open(stats_file, 'w', encoding='utf-8') as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)
    
    print(f"\n统计结果已保存到: {stats_file}")

if __name__ == "__main__":
    main()