#!/usr/bin/env python3
"""
将游戏数据转换为适合模型微调的格式
"""

import json
import os
import glob
from pathlib import Path
from typing import List, Dict, Any, Optional
import argparse

def extract_conversation_turns(game_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    从游戏数据中提取对话轮次
    """
    turns = []
    steps = game_data.get("steps", [])
    
    # 按回合分组
    rounds = {}
    for step in steps:
        round_num = None
        # 从observation中提取回合信息
        obs = step.get("observation", "")
        if "Starting Round" in obs:
            # 提取回合号
            import re
            match = re.search(r"Starting Round (\d+)", obs)
            if match:
                round_num = int(match.group(1))
        
        if round_num is not None:
            if round_num not in rounds:
                rounds[round_num] = []
            rounds[round_num].append(step)
    
    # 处理每个回合
    for round_num, round_steps in rounds.items():
        # 分离聊天和决策阶段
        chat_steps = []
        decision_steps = []
        
        for step in round_steps:
            action = step.get("action", "")
            if "chat" in action:
                chat_steps.append(step)
            elif "cooperate" in action or "defect" in action:
                decision_steps.append(step)
        
        # 添加聊天轮次
        for step in chat_steps:
            player_id = step.get("player_id")
            observation = step.get("observation", "")
            action = step.get("action", "")
            model_input = step.get("model_input", {})
            system_prompt = model_input.get("system_prompt", "")
            user_message = model_input.get("user_message", "")
            model_output = step.get("model_output", {})
            raw_response = model_output.get("raw_response", "")
            
            turns.append({
                "round": round_num,
                "phase": "chat",
                "player_id": player_id,
                "observation": observation,
                "action": action,
                "system_prompt": system_prompt,
                "user_message": user_message,
                "model_response": raw_response,
                "model": model_input.get("model", "")
            })
        
        # 添加决策轮次
        for step in decision_steps:
            player_id = step.get("player_id")
            observation = step.get("observation", "")
            action = step.get("action", "")
            model_input = step.get("model_input", {})
            system_prompt = model_input.get("system_prompt", "")
            user_message = model_input.get("user_message", "")
            model_output = step.get("model_output", {})
            raw_response = model_output.get("raw_response", "")
            
            turns.append({
                "round": round_num,
                "phase": "decision",
                "player_id": player_id,
                "observation": observation,
                "action": action,
                "system_prompt": system_prompt,
                "user_message": user_message,
                "model_response": raw_response,
                "model": model_input.get("model", "")
            })
    
    return turns

def create_fine_tuning_examples(turns: List[Dict[str, Any]], game_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    创建微调样本
    """
    examples = []
    
    # 获取游戏结果
    final_results = game_data.get("final_results", {})
    rewards = final_results.get("rewards", {})
    agents = game_data.get("agents", {})
    
    # 按回合和阶段组织数据
    round_data = {}
    for turn in turns:
        round_num = turn["round"]
        phase = turn["phase"]
        
        if round_num not in round_data:
            round_data[round_num] = {}
        if phase not in round_data[round_num]:
            round_data[round_num][phase] = []
        
        round_data[round_num][phase].append(turn)
    
    # 为每个回合创建样本
    for round_num in sorted(round_data.keys()):
        round_turns = round_data[round_num]
        
        # 聊天阶段的样本
        if "chat" in round_turns:
            for turn in round_turns["chat"]:
                player_id = turn["player_id"]
                agent_id = f"agent_{player_id}"
                agent_info = agents.get(agent_id, {})
                model = turn["model"]
                
                # 创建指令-响应对
                instruction = f"You are Player {player_id} in a 3-player Iterated Prisoner's Dilemma game. Round {round_num} chat phase. What would you say to other players?"
                
                # 构建输入上下文
                context = turn["observation"]
                
                # 模型的响应
                response = turn["model_response"]
                
                # 获取该玩家的最终奖励作为标签
                reward = rewards.get(str(player_id), 0)
                
                examples.append({
                    "instruction": instruction,
                    "input": context,
                    "output": response,
                    "player_id": player_id,
                    "round": round_num,
                    "phase": "chat",
                    "model": model,
                    "reward": reward,
                    "agent_type": agent_info.get("type", ""),
                    "agent_prompt": agent_info.get("prompt", "")
                })
        
        # 决策阶段的样本
        if "decision" in round_turns:
            for turn in round_turns["decision"]:
                player_id = turn["player_id"]
                agent_id = f"agent_{player_id}"
                agent_info = agents.get(agent_id, {})
                model = turn["model"]
                
                # 创建指令-响应对
                instruction = f"You are Player {player_id} in a 3-player Iterated Prisoner's Dilemma game. Round {round_num} decision phase. What are your moves against other players?"
                
                # 构建输入上下文
                context = turn["observation"]
                
                # 模型的响应
                response = turn["model_response"]
                
                # 获取该玩家的最终奖励作为标签
                reward = rewards.get(str(player_id), 0)
                
                examples.append({
                    "instruction": instruction,
                    "input": context,
                    "output": response,
                    "player_id": player_id,
                    "round": round_num,
                    "phase": "decision",
                    "model": model,
                    "reward": reward,
                    "agent_type": agent_info.get("type", ""),
                    "agent_prompt": agent_info.get("prompt", "")
                })
    
    return examples

def process_game_file(file_path: str) -> List[Dict[str, Any]]:
    """
    处理单个游戏文件
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            game_data = json.load(f)
        
        # 提取对话轮次
        turns = extract_conversation_turns(game_data)
        
        # 创建微调样本
        examples = create_fine_tuning_examples(turns, game_data)
        
        return examples
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return []

def process_all_games(data_dir: str, output_file: str) -> None:
    """
    处理所有游戏数据并保存为微调格式
    """
    all_examples = []
    
    # 查找所有游戏文件
    game_files = []
    for root, dirs, files in os.walk(data_dir):
        for file in files:
            if file.endswith("_three_player_ipd.json"):
                game_files.append(os.path.join(root, file))
    
    print(f"Found {len(game_files)} game files")
    
    # 处理每个游戏文件
    for i, game_file in enumerate(game_files):
        print(f"Processing file {i+1}/{len(game_files)}: {game_file}")
        examples = process_game_file(game_file)
        all_examples.extend(examples)
    
    print(f"Total examples: {len(all_examples)}")
    
    # 保存为JSON格式
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_examples, f, ensure_ascii=False, indent=2)
    
    # 保存为CSV格式（便于某些微调框架使用）
    import csv
    csv_file = output_file.replace('.json', '.csv')
    with open(csv_file, 'w', newline='', encoding='utf-8') as f:
        if all_examples:
            fieldnames = all_examples[0].keys()
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(all_examples)
    
    print(f"Saved fine-tuning data to {output_file} and {csv_file}")

def create_training_validation_split(data_file: str, train_ratio: float = 0.8) -> None:
    """
    创建训练集和验证集分割
    """
    with open(data_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # 随机打乱数据
    import random
    random.shuffle(data)
    
    # 分割数据
    split_idx = int(len(data) * train_ratio)
    train_data = data[:split_idx]
    val_data = data[split_idx:]
    
    # 保存训练集
    train_file = data_file.replace('.json', '_train.json')
    with open(train_file, 'w', encoding='utf-8') as f:
        json.dump(train_data, f, ensure_ascii=False, indent=2)
    
    # 保存验证集
    val_file = data_file.replace('.json', '_val.json')
    with open(val_file, 'w', encoding='utf-8') as f:
        json.dump(val_data, f, ensure_ascii=False, indent=2)
    
    print(f"Training set: {len(train_data)} examples -> {train_file}")
    print(f"Validation set: {len(val_data)} examples -> {val_file}")

def main():
    parser = argparse.ArgumentParser(description="Convert game data to fine-tuning format")
    parser.add_argument("--data_dir", type=str, default="/home/syh/mindgames/large_model_game_arena/data/datafix", 
                       help="Directory containing game data")
    parser.add_argument("--output_file", type=str, default="fine_tuning_data.json", 
                       help="Output file for fine-tuning data")
    parser.add_argument("--train_ratio", type=float, default=0.8, 
                       help="Ratio of training data (default: 0.8)")
    parser.add_argument("--no_split", action="store_true", 
                       help="Do not create train/validation split")
    
    args = parser.parse_args()
    
    # 处理所有游戏数据
    process_all_games(args.data_dir, args.output_file)
    
    # 创建训练集和验证集分割
    if not args.no_split:
        create_training_validation_split(args.output_file, args.train_ratio)

if __name__ == "__main__":
    main()