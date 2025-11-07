#!/usr/bin/env python3
"""
上校博弈游戏数据转换为SFT格式的脚本
将colonel_blotto游戏数据转换为适合监督微调的格式
"""

import json
import os
import csv
import glob
from pathlib import Path
from typing import Dict, List, Any, Tuple
import random

def load_game_data(file_path: str) -> Dict[str, Any]:
    """加载游戏数据文件"""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def load_agent_info(file_path: str) -> Dict[str, Any]:
    """加载代理信息文件"""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def extract_round_data(steps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """从游戏步骤中提取回合数据"""
    rounds = []
    current_round = {}
    round_num = 1
    
    for i in range(0, len(steps), 2):
        if i + 1 >= len(steps):
            break
            
        player1_step = steps[i]
        player2_step = steps[i + 1]
        
        # 提取玩家1的行动和思考过程
        player1_action = player1_step.get("action", "").strip()
        player1_thinking = player1_step.get("model_output", {}).get("response", "")
        
        # 提取玩家2的行动和思考过程
        player2_action = player2_step.get("action", "").strip()
        player2_thinking = player2_step.get("model_output", {}).get("response", "")
        
        # 提取游戏状态和结果
        observation = player1_step.get("observation", "")
        
        # 查找回合结果
        round_result = ""
        if "Winner:" in observation:
            round_result = observation.split("Winner:")[1].split("\n")[0].strip()
        
        round_data = {
            "round_number": round_num,
            "player1": {
                "id": player1_step.get("player_id", 0),
                "action": player1_action,
                "thinking": player1_thinking,
                "observation": observation
            },
            "player2": {
                "id": player2_step.get("player_id", 1),
                "action": player2_action,
                "thinking": player2_thinking,
                "observation": player2_step.get("observation", "")
            },
            "result": round_result
        }
        
        rounds.append(round_data)
        round_num += 1
    
    return rounds

def create_sft_sample(round_data: Dict[str, Any], agent_info: Dict[str, Any], 
                     player_id: int) -> Dict[str, Any]:
    """为单个玩家创建SFT样本"""
    if player_id == 0:
        player_data = round_data["player1"]
        opponent_data = round_data["player2"]
        agent_key = "agent_0"
    else:
        player_data = round_data["player2"]
        opponent_data = round_data["player1"]
        agent_key = "agent_1"
    
    # 获取代理信息
    agent = agent_info.get(agent_key, {})
    model_name = agent.get("model_name", "unknown")
    prompt_name = agent.get("prompt_name", "unknown")
    
    # 创建指令
    instruction = f"作为上校博弈游戏中的玩家，根据当前游戏状态和对手的行动，制定你的策略并决定如何分配20个单位到A、B、C三个战场。"
    
    # 创建输入
    game_state = player_data.get("observation", "")
    opponent_action = opponent_data.get("action", "")
    
    input_text = f"""
游戏状态: {game_state}

对手上一回合的行动: {opponent_action}

你是玩家{player_id}，使用{model_name}模型和{prompt_name}策略。
请分析当前局势，制定你的策略，并决定如何分配20个单位到A、B、C三个战场。
你的回答应该只包含分配方案，格式为[Ax By Cz]，其中x+y+z=20。
"""
    
    # 创建输出
    output_text = player_data.get("thinking", "") + "\n" + player_data.get("action", "")
    
    # 确定是否获胜
    result = round_data.get("result", "")
    is_winner = 1 if (f"Player {player_id}" in result or 
                     (player_id == 0 and "Commander Alpha" in result) or
                     (player_id == 1 and "Commander Beta" in result)) else 0
    
    return {
        "instruction": instruction,
        "input": input_text.strip(),
        "output": output_text.strip(),
        "player_id": player_id,
        "model_name": model_name,
        "prompt_name": prompt_name,
        "round_number": round_data.get("round_number", 1),
        "is_winner": is_winner,
        "game_type": "colonel_blotto",
        "action": player_data.get("action", ""),
        "opponent_action": opponent_action
    }

def process_game_file(game_file_path: str, agent_info_file_path: str) -> List[Dict[str, Any]]:
    """处理单个游戏文件，返回SFT样本列表"""
    # 加载游戏数据和代理信息
    game_data = load_game_data(game_file_path)
    agent_info = load_agent_info(agent_info_file_path)
    
    # 提取回合数据
    steps = game_data.get("steps", [])
    rounds = extract_round_data(steps)
    
    # 为每个玩家的每个回合创建SFT样本
    sft_samples = []
    for round_data in rounds:
        for player_id in [0, 1]:
            sft_sample = create_sft_sample(round_data, agent_info, player_id)
            sft_samples.append(sft_sample)
    
    return sft_samples

def save_sft_data(sft_samples: List[Dict[str, Any]], output_dir: str, 
                 filename_prefix: str = "colonel_blotto_sft"):
    """保存SFT数据为JSON和CSV格式"""
    # 确保输出目录存在
    os.makedirs(output_dir, exist_ok=True)
    
    # 保存为JSON
    json_path = os.path.join(output_dir, f"{filename_prefix}.json")
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(sft_samples, f, ensure_ascii=False, indent=2)
    
    # 保存为CSV
    csv_path = os.path.join(output_dir, f"{filename_prefix}.csv")
    if sft_samples:
        fieldnames = sft_samples[0].keys()
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(sft_samples)
    
    return json_path, csv_path

def create_train_val_split(sft_samples: List[Dict[str, Any]], output_dir: str, 
                          val_ratio: float = 0.2, random_seed: int = 42) -> Tuple[str, str, str, str]:
    """创建训练集和验证集分割"""
    random.seed(random_seed)
    random.shuffle(sft_samples)
    
    # 计算分割点
    val_size = int(len(sft_samples) * val_ratio)
    train_samples = sft_samples[val_size:]
    val_samples = sft_samples[:val_size]
    
    # 保存训练集
    train_json, train_csv = save_sft_data(
        train_samples, output_dir, "colonel_blotto_sft_train"
    )
    
    # 保存验证集
    val_json, val_csv = save_sft_data(
        val_samples, output_dir, "colonel_blotto_sft_val"
    )
    
    return train_json, train_csv, val_json, val_csv

def analyze_sft_data(sft_samples: List[Dict[str, Any]]) -> Dict[str, Any]:
    """分析SFT数据并返回统计信息"""
    stats = {
        "total_samples": len(sft_samples),
        "players": {},
        "models": {},
        "prompts": {},
        "winners": 0,
        "losers": 0
    }
    
    for sample in sft_samples:
        player_id = sample.get("player_id", 0)
        model_name = sample.get("model_name", "unknown")
        prompt_name = sample.get("prompt_name", "unknown")
        is_winner = sample.get("is_winner", 0)
        
        # 统计玩家
        stats["players"][player_id] = stats["players"].get(player_id, 0) + 1
        
        # 统计模型
        stats["models"][model_name] = stats["models"].get(model_name, 0) + 1
        
        # 统计提示
        stats["prompts"][prompt_name] = stats["prompts"].get(prompt_name, 0) + 1
        
        # 统计胜负
        if is_winner:
            stats["winners"] += 1
        else:
            stats["losers"] += 1
    
    return stats

def main():
    # 设置路径
    data_dir = "/home/syh/mindgames/large_model_game_arena/data/colonel_blotto"
    output_dir = "/home/syh/mindgames/large_model_game_arena/databottle"
    
    # 确保输出目录存在
    os.makedirs(output_dir, exist_ok=True)
    
    # 收集所有游戏文件
    batch_runs_dir = os.path.join(data_dir, "batch_runs")
    game_files = []
    
    for batch_run_dir in glob.glob(os.path.join(batch_runs_dir, "batch_run_*")):
        for timestamp_dir in glob.glob(os.path.join(batch_run_dir, "*")):
            if os.path.isdir(timestamp_dir):
                game_file = glob.glob(os.path.join(timestamp_dir, "*_colonel_blotto.json"))
                if game_file:
                    agent_info_file = os.path.join(timestamp_dir, "agent_info.json")
                    if os.path.exists(agent_info_file):
                        game_files.append((game_file[0], agent_info_file))
    
    print(f"找到 {len(game_files)} 个游戏文件")
    
    # 处理所有游戏文件
    all_sft_samples = []
    for game_file, agent_info_file in game_files:
        try:
            sft_samples = process_game_file(game_file, agent_info_file)
            all_sft_samples.extend(sft_samples)
            print(f"处理 {game_file}，生成 {len(sft_samples)} 个样本")
        except Exception as e:
            print(f"处理 {game_file} 时出错: {e}")
    
    print(f"总共生成 {len(all_sft_samples)} 个SFT样本")
    
    # 分析数据
    stats = analyze_sft_data(all_sft_samples)
    print("\n数据统计:")
    print(f"总样本数: {stats['total_samples']}")
    print(f"获胜样本: {stats['winners']} ({stats['winners']/stats['total_samples']*100:.2f}%)")
    print(f"失败样本: {stats['losers']} ({stats['losers']/stats['total_samples']*100:.2f}%)")
    print("\n玩家分布:")
    for player_id, count in stats["players"].items():
        print(f"玩家 {player_id}: {count} 样本")
    print("\n模型分布:")
    for model, count in stats["models"].items():
        print(f"{model}: {count} 样本")
    print("\n提示分布:")
    for prompt, count in stats["prompts"].items():
        print(f"{prompt}: {count} 样本")
    
    # 保存完整数据集
    json_path, csv_path = save_sft_data(all_sft_samples, output_dir)
    print(f"\n完整数据集已保存到:")
    print(f"JSON: {json_path}")
    print(f"CSV: {csv_path}")
    
    # 创建训练集和验证集分割
    train_json, train_csv, val_json, val_csv = create_train_val_split(all_sft_samples, output_dir)
    print(f"\n训练集和验证集已保存到:")
    print(f"训练集 JSON: {train_json}")
    print(f"训练集 CSV: {train_csv}")
    print(f"验证集 JSON: {val_json}")
    print(f"验证集 CSV: {val_csv}")
    
    # 保存统计信息
    stats_path = os.path.join(output_dir, "colonel_blotto_sft_stats.json")
    with open(stats_path, 'w', encoding='utf-8') as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)
    print(f"\n统计信息已保存到: {stats_path}")

if __name__ == "__main__":
    main()