#!/usr/bin/env python3
"""
分析微调数据中的奖励分布，并筛选出赢的数据用于微调
"""

import json
import pandas as pd
import numpy as np
from collections import Counter
import os

def analyze_rewards(data_file):
    """分析奖励分布"""
    with open(data_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    rewards = [item['reward'] for item in data]
    
    print(f"总样本数: {len(data)}")
    print(f"奖励统计:")
    print(f"  最小值: {min(rewards)}")
    print(f"  最大值: {max(rewards)}")
    print(f"  平均值: {np.mean(rewards):.4f}")
    print(f"  中位数: {np.median(rewards):.4f}")
    
    # 奖励分布
    reward_counts = Counter(rewards)
    print(f"\n奖励分布:")
    for reward, count in sorted(reward_counts.items()):
        print(f"  奖励 {reward}: {count} 样本 ({count/len(data)*100:.2f}%)")
    
    return data, rewards

def filter_winning_data(data, threshold=0.0):
    """筛选出赢的数据（奖励值大于等于阈值的数据）"""
    winning_data = [item for item in data if item['reward'] >= threshold]
    print(f"\n筛选奖励 >= {threshold} 的数据:")
    print(f"  赢的样本数: {len(winning_data)}")
    print(f"  占比: {len(winning_data)/len(data)*100:.2f}%")
    
    return winning_data

def save_filtered_data(winning_data, output_file):
    """保存筛选后的数据"""
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(winning_data, f, ensure_ascii=False, indent=2)
    print(f"筛选后的数据已保存到: {output_file}")
    
    # 同时保存为CSV格式
    df = pd.DataFrame(winning_data)
    csv_file = output_file.replace('.json', '.csv')
    df.to_csv(csv_file, index=False, encoding='utf-8')
    print(f"CSV格式数据已保存到: {csv_file}")

def create_train_val_split(data, train_ratio=0.8, random_seed=42):
    """创建训练集和验证集分割"""
    np.random.seed(random_seed)
    np.random.shuffle(data)
    
    split_idx = int(len(data) * train_ratio)
    train_data = data[:split_idx]
    val_data = data[split_idx:]
    
    print(f"\n训练集/验证集分割 (比例 {train_ratio}:{1-train_ratio}):")
    print(f"  训练集: {len(train_data)} 样本")
    print(f"  验证集: {len(val_data)} 样本")
    
    return train_data, val_data

def analyze_winning_strategies(winning_data):
    """分析赢的策略特点"""
    agent_prompts = [item['agent_prompt'] for item in winning_data]
    agent_types = [item['agent_type'] for item in winning_data]
    models = [item['model'] for item in winning_data]
    
    print("\n赢的数据中的策略分析:")
    
    # Agent prompt分布
    prompt_counts = Counter(agent_prompts)
    print("  Agent Prompt分布:")
    for prompt, count in prompt_counts.most_common():
        print(f"    {prompt}: {count} 样本 ({count/len(winning_data)*100:.2f}%)")
    
    # Agent type分布
    type_counts = Counter(agent_types)
    print("  Agent Type分布:")
    for agent_type, count in type_counts.most_common():
        print(f"    {agent_type}: {count} 样本 ({count/len(winning_data)*100:.2f}%)")
    
    # Model分布
    model_counts = Counter(models)
    print("  Model分布:")
    for model, count in model_counts.most_common():
        print(f"    {model}: {count} 样本 ({count/len(winning_data)*100:.2f}%)")

def main():
    # 输入文件
    data_file = "fine_tuning_data.json"
    
    # 分析奖励分布
    data, rewards = analyze_rewards(data_file)
    
    # 筛选赢的数据（奖励 >= 0.0）
    winning_data = filter_winning_data(data, threshold=0.0)
    
    # 分析赢的策略特点
    analyze_winning_strategies(winning_data)
    
    # 保存筛选后的数据
    output_file = "fine_tuning_data_winning.json"
    save_filtered_data(winning_data, output_file)
    
    # 创建训练集和验证集分割
    train_data, val_data = create_train_val_split(winning_data)
    
    # 保存训练集和验证集
    train_file = "fine_tuning_data_winning_train.json"
    val_file = "fine_tuning_data_winning_val.json"
    
    with open(train_file, 'w', encoding='utf-8') as f:
        json.dump(train_data, f, ensure_ascii=False, indent=2)
    print(f"训练集已保存到: {train_file}")
    
    with open(val_file, 'w', encoding='utf-8') as f:
        json.dump(val_data, f, ensure_ascii=False, indent=2)
    print(f"验证集已保存到: {val_file}")
    
    # 保存CSV格式
    train_df = pd.DataFrame(train_data)
    train_df.to_csv("fine_tuning_data_winning_train.csv", index=False, encoding='utf-8')
    print(f"训练集CSV已保存到: fine_tuning_data_winning_train.csv")
    
    val_df = pd.DataFrame(val_data)
    val_df.to_csv("fine_tuning_data_winning_val.csv", index=False, encoding='utf-8')
    print(f"验证集CSV已保存到: fine_tuning_data_winning_val.csv")

if __name__ == "__main__":
    main()