#!/usr/bin/env python3
"""
修复3PIPD游戏日志中player_agent_mapping和player_positions的脚本

该脚本会读取原始游戏日志文件，修复其中的player_agent_mapping和player_positions，
确保它们逻辑正确，并将修复后的文件保存到指定目录。
"""

import os
import json
import shutil
from pathlib import Path
from typing import Dict, List, Any

def fix_player_agent_mapping(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    修复游戏日志中的player_agent_mapping和player_positions
    
    Args:
        data: 原始游戏日志数据
        
    Returns:
        修复后的游戏日志数据
    """
    # 获取原始的player_positions和agents信息
    player_positions = data.get("player_positions", [])
    agents = data.get("agents", {})
    
    # 如果没有player_positions或agents，直接返回原始数据
    if not player_positions or not agents:
        return data
    
    # 根据player_positions创建正确的player_agent_mapping
    # player_positions[i] = j 表示agent i 被分配到 player j 的位置
    # 所以我们需要创建一个映射：player_id -> agent_id
    player_agent_mapping = {}
    for agent_id, player_id in enumerate(player_positions):
        player_agent_mapping[str(player_id)] = f"agent_{agent_id}"
    
    # 打印调试信息
    print(f"player_positions: {player_positions}")
    print(f"agents: {agents}")
    print(f"computed player_agent_mapping: {player_agent_mapping}")
    
    # 更新数据
    data["player_agent_mapping"] = player_agent_mapping
    
    return data

def process_game_log_file(input_path: Path, output_path: Path) -> None:
    """
    处理单个游戏日志文件
    
    Args:
        input_path: 输入文件路径
        output_path: 输出文件路径
    """
    try:
        # 读取原始文件
        with open(input_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 修复数据
        fixed_data = fix_player_agent_mapping(data)
        
        # 打印调试信息
        print(f"处理文件: {input_path}")
        print(f"原始 player_agent_mapping: {data.get('player_agent_mapping', {})}")
        print(f"修复后 player_agent_mapping: {fixed_data.get('player_agent_mapping', {})}")
        
        # 确保输出目录存在
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 写入修复后的文件
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(fixed_data, f, indent=2, ensure_ascii=False)
        
        print(f"已修复: {input_path} -> {output_path}")
        print("-" * 50)
        
    except Exception as e:
        print(f"处理文件 {input_path} 时出错: {e}")

def process_batch_run_directory(input_dir: Path, output_dir: Path) -> None:
    """
    处理一个batch_run目录
    
    Args:
        input_dir: 输入目录
        output_dir: 输出目录
    """
    # 遍历目录中的所有子目录
    for item in input_dir.iterdir():
        if item.is_dir():
            # 处理子目录中的游戏日志文件
            process_single_run_directory(item, output_dir / item.name)

def process_single_run_directory(input_dir: Path, output_dir: Path) -> None:
    """
    处理单个运行目录
    
    Args:
        input_dir: 输入目录
        output_dir: 输出目录
    """
    # 确保输出目录存在
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 查找游戏日志文件
    for file in input_dir.iterdir():
        if file.is_file() and file.name.endswith('_three_player_ipd.json'):
            # 处理游戏日志文件
            output_file = output_dir / file.name
            process_game_log_file(file, output_file)
        
        # 复制agent_info.json文件（如果存在）
        elif file.is_file() and file.name == 'agent_info.json':
            output_file = output_dir / file.name
            shutil.copy2(file, output_file)

def main():
    """
    主函数，处理所有3PIPD游戏日志文件
    """
    # 设置输入和输出目录
    input_base_dir = Path("/home/syh/mindgames/large_model_game_arena/data/three_player_ipd")
    output_base_dir = Path("/home/syh/mindgames/large_model_game_arena/data/datafix")
    
    # 确保输出目录存在
    output_base_dir.mkdir(parents=True, exist_ok=True)
    
    # 处理所有游戏日志文件
    batch_runs_dir = input_base_dir / "batch_runs"
    if batch_runs_dir.exists():
        for batch_run in batch_runs_dir.iterdir():
            if batch_run.is_dir():
                for timestamp_dir in batch_run.iterdir():
                    if timestamp_dir.is_dir():
                        for file in timestamp_dir.iterdir():
                            if file.is_file() and file.name.endswith("_three_player_ipd.json"):
                                input_file = file
                                output_file = output_base_dir / "batch_runs" / batch_run.name / timestamp_dir.name / file.name
                                process_game_log_file(input_file, output_file)
    
    # 复制统计文件
    stats_file = input_base_dir / "stats.json"
    if stats_file.exists():
        shutil.copy2(stats_file, output_base_dir / "stats.json")
    
    print(f"所有文件已处理完成，修复后的文件保存在: {output_base_dir}")

if __name__ == "__main__":
    main()