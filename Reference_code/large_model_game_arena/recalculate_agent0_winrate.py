#!/usr/bin/env python3
"""
重新计算Agent0胜率的脚本
读取/home/syh/mindgames/large_model_game_arena/data/three_player_ipd目录下的所有游戏数据
并正确计算Agent0的胜率
"""

import json
import os
import re
import shutil
from pathlib import Path
from typing import Dict, List, Tuple, Any

def extract_final_scores_from_log(log_content: str) -> Dict[str, int]:
    """
    从游戏日志中提取最终分数
    """
    # 查找所有轮的分数记录
    score_pattern = r"-> Current scores: Player 0 \((\d+)\); Player 1 \((\d+)\); Player 2 \((\d+)\)"
    matches = re.findall(score_pattern, log_content)
    
    if not matches:
        return None
    
    # 获取最后一轮的分数（应该是第四轮）
    last_scores = matches[-1]
    base_scores = {
        "0": int(last_scores[0]),
        "1": int(last_scores[1]),
        "2": int(last_scores[2])
    }
    
    # 提取第五轮的决策
    round5_decisions = extract_round5_decisions(log_content)
    if round5_decisions:
        # 计算第五轮的结果
        round5_results = calculate_round_results(round5_decisions)
        
        # 将第四轮分数与第五轮结果相加
        final_scores = {
            "0": base_scores["0"] + round5_results.get("0", 0),
            "1": base_scores["1"] + round5_results.get("1", 0),
            "2": base_scores["2"] + round5_results.get("2", 0)
        }
        return final_scores
    
    # 如果没有第五轮决策，返回第四轮分数
    return base_scores

def extract_round5_decisions(log_content: str) -> Dict[str, str]:
    """
    从游戏日志中提取第五轮的决策
    """
    # 查找第五轮的决策模式
    decisions = {}
    
    # 查找Player 0的决策
    p0_pattern = r"Player 0.*?\[([12]) (cooperate|defect)\].*?\[([12]) (cooperate|defect)\]"
    p0_match = re.search(p0_pattern, log_content)
    if p0_match:
        decisions["0"] = {
            p0_match.group(1): p0_match.group(2),
            p0_match.group(3): p0_match.group(4)
        }
    
    # 查找Player 1的决策
    p1_pattern = r"Player 1.*?\[([02]) (cooperate|defect)\].*?\[([02]) (cooperate|defect)\]"
    p1_match = re.search(p1_pattern, log_content)
    if p1_match:
        decisions["1"] = {
            p1_match.group(1): p1_match.group(2),
            p1_match.group(3): p1_match.group(4)
        }
    
    # 查找Player 2的决策
    p2_pattern = r"Player 2.*?\[([01]) (cooperate|defect)\].*?\[([01]) (cooperate|defect)\]"
    p2_match = re.search(p2_pattern, log_content)
    if p2_match:
        decisions["2"] = {
            p2_match.group(1): p2_match.group(2),
            p2_match.group(3): p2_match.group(4)
        }
    
    return decisions

def calculate_round_results(decisions: Dict[str, Dict[str, str]]) -> Dict[str, int]:
    """
    根据决策计算一轮的结果
    """
    results = {"0": 0, "1": 0, "2": 0}
    
    # 计算每对玩家的结果
    pairs = [("0", "1"), ("0", "2"), ("1", "2")]
    
    for p1, p2 in pairs:
        # 获取玩家1对玩家2的决策
        p1_decision = decisions.get(p1, {}).get(p2, "cooperate")
        # 获取玩家2对玩家1的决策
        p2_decision = decisions.get(p2, {}).get(p1, "cooperate")
        
        # 计算得分
        if p1_decision == "cooperate" and p2_decision == "cooperate":
            # 双方合作，各得3分
            results[p1] += 3
            results[p2] += 3
        elif p1_decision == "cooperate" and p2_decision == "defect":
            # p1合作，p2背叛，p1得0分，p2得5分
            results[p1] += 0
            results[p2] += 5
        elif p1_decision == "defect" and p2_decision == "cooperate":
            # p1背叛，p2合作，p1得5分，p2得0分
            results[p1] += 5
            results[p2] += 0
        elif p1_decision == "defect" and p2_decision == "defect":
            # 双方背叛，各得1分
            results[p1] += 1
            results[p2] += 1
    
    return results

def determine_winners(scores: Dict[str, int]) -> List[str]:
    """
    根据分数确定胜者
    """
    if not scores:
        return []
    
    max_score = max(scores.values())
    winners = [player_id for player_id, score in scores.items() if score == max_score]
    return winners

def process_game_file(file_path: Path) -> Dict[str, Any]:
    """
    处理单个游戏文件，提取游戏结果
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            game_data = json.load(f)
        
        # 获取player_agent_mapping和player_positions
        player_agent_mapping = game_data.get("player_agent_mapping", {})
        player_positions = game_data.get("player_positions", [])
        
        # 从游戏日志中提取分数
        log_content = json.dumps(game_data)  # 将整个JSON转为字符串以便搜索
        scores = extract_final_scores_from_log(log_content)
        
        if scores is None:
            print(f"Warning: Could not extract scores from {file_path}")
            return None
        
        # 确定胜者
        winners = determine_winners(scores)
        
        # 找出agent0对应的player_id
        agent0_player_id = None
        for player_id, agent_id in player_agent_mapping.items():
            if agent_id == "agent_0":
                agent0_player_id = player_id
                break
        
        if agent0_player_id is None:
            print(f"Warning: Could not find agent0 in player_agent_mapping for {file_path}")
            return None
        
        # 判断agent0是否获胜
        agent0_is_winner = str(agent0_player_id) in winners
        
        return {
            "file_path": str(file_path),
            "scores": scores,
            "winners": winners,
            "agent0_player_id": agent0_player_id,
            "agent0_is_winner": agent0_is_winner,
            "agent0_score": scores.get(str(agent0_player_id), 0)
        }
    
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return None

def main():
    """
    主函数：处理所有游戏数据并计算Agent0的胜率
    """
    # 设置数据目录路径
    data_dir = Path("/home/syh/mindgames/large_model_game_arena/data/three_player_ipd/batch_runs")
    
    # 设置Agent0获胜游戏的输出目录
    output_dir = Path("/home/syh/mindgames/large_model_game_arena/datacollect_3pipd")
    
    if not data_dir.exists():
        print(f"Error: Data directory {data_dir} does not exist")
        return
    
    # 创建输出目录（如果不存在）
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"Agent0获胜游戏将保存到: {output_dir}")
    
    # 收集所有游戏文件
    game_files = []
    for batch_dir in data_dir.glob("batch_run_*"):
        if batch_dir.is_dir():
            for timestamp_dir in batch_dir.glob("*"):
                if timestamp_dir.is_dir():
                    game_file = timestamp_dir / f"{timestamp_dir.name}_three_player_ipd.json"
                    if game_file.exists():
                        game_files.append(game_file)
    
    print(f"Found {len(game_files)} game files")
    
    # 处理所有游戏文件
    game_results = []
    agent0_win_files = []  # 存储Agent0获胜的文件路径
    
    for game_file in game_files:
        result = process_game_file(game_file)
        if result:
            game_results.append(result)
            
            # 如果Agent0获胜，复制文件到输出目录
            if result["agent0_is_winner"]:
                agent0_win_files.append(game_file)
                
                # 创建对应的输出子目录结构
                relative_path = game_file.relative_to(data_dir)
                output_file_path = output_dir / relative_path
                
                # 确保输出目录存在
                output_file_path.parent.mkdir(parents=True, exist_ok=True)
                
                # 复制文件
                shutil.copy2(game_file, output_file_path)
    
    if not game_results:
        print("No valid game results found")
        return
    
    # 计算统计信息
    total_games = len(game_results)
    agent0_wins = len(agent0_win_files)
    agent0_win_rate = (agent0_wins / total_games) * 100 if total_games > 0 else 0
    
    # 计算平均分数
    agent0_scores = [result["agent0_score"] for result in game_results]
    agent0_avg_score = sum(agent0_scores) / len(agent0_scores) if agent0_scores else 0
    
    # 输出结果
    print("\n=== 重新计算的结果 ===")
    print(f"总游戏数: {total_games}")
    print(f"Agent0获胜次数: {agent0_wins}")
    print(f"Agent0胜率: {agent0_win_rate:.2f}%")
    print(f"Agent0平均得分: {agent0_avg_score:.2f}")
    print(f"已复制 {agent0_wins} 个Agent0获胜的游戏文件到: {output_dir}")
    
    # 输出详细统计
    print("\n=== 详细统计 ===")
    score_distribution = {}
    for result in game_results:
        score = result["agent0_score"]
        score_distribution[score] = score_distribution.get(score, 0) + 1
    
    print("Agent0得分分布:")
    for score in sorted(score_distribution.keys()):
        count = score_distribution[score]
        percentage = (count / total_games) * 100
        print(f"  {score}分: {count}次 ({percentage:.1f}%)")
    
    # 保存结果到文件
    output_file = data_dir / "recalculated_stats.json"
    output_data = {
        "total_games": total_games,
        "agent0_wins": agent0_wins,
        "agent0_win_rate": agent0_win_rate,
        "agent0_avg_score": agent0_avg_score,
        "score_distribution": score_distribution,
        "game_results": game_results,
        "agent0_win_files": [str(f) for f in agent0_win_files]
    }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    
    print(f"\n详细结果已保存到: {output_file}")

if __name__ == "__main__":
    main()