#!/usr/bin/env python3
"""
三人囚徒困境并行批量运行脚本
同时运行多个三人囚徒困境游戏，统计Agent0的胜率，并保存详细日志
"""

import os
import sys
import json
import uuid
import yaml
import argparse
import random
from datetime import datetime
from pathlib import Path
import time
import multiprocessing
from functools import partial

# 添加项目路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils.game_manager import GameManager
from agents.agent_0 import Agent0
from agents.agent_1 import Agent1
from agents.agent_2 import Agent2

def print_colored(text: str, color: str = "white"):
    """打印彩色文本"""
    colors = {
        "red": "\033[91m",
        "green": "\033[92m",
        "yellow": "\033[93m",
        "blue": "\033[94m",
        "purple": "\033[95m",
        "cyan": "\033[96m",
        "white": "\033[97m",
        "reset": "\033[0m"
    }
    print(f"{colors.get(color, colors['white'])}{text}{colors['reset']}")

def load_config():
    """加载配置文件"""
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.yaml")
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def save_game_data(data_dir, game_log, agent_info, run_number, result, player_positions):
    """保存游戏数据为统一格式"""
    # 创建时间戳目录
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    run_dir = Path(data_dir) / f"batch_run_{run_number:03d}" / timestamp
    run_dir.mkdir(parents=True, exist_ok=True)
    
    # 如果有GameManager的原始日志，复制到运行目录
    log_path = None
    for log_entry in game_log:
        if log_entry.get("type") == "game_result" and "log_path" in log_entry.get("result", {}):
            log_path = log_entry["result"]["log_path"]
            break
    
    if log_path and os.path.exists(log_path):
        try:
            import shutil
            shutil.copy(log_path, run_dir / "original_game_log.json")
            print(f"已复制原始日志到: {run_dir / 'original_game_log.json'}")
        except Exception as e:
            print(f"复制原始日志失败: {e}")
    
    # 转换游戏日志为统一格式
    unified_data = {
        "game_name": "three_player_ipd",
        "timestamp": agent_info["timestamp"],
        "run_number": run_number,
        "steps": []
    }
    
    # 添加player与agent的映射关系
    if player_positions is not None:
        # player_positions[i] = j 表示agent i 被分配到 player j 的位置
        # 创建映射：player_id -> agent_id
        player_agent_mapping = {}
        for agent_id, player_id in enumerate(player_positions):
            player_agent_mapping[str(player_id)] = f"agent_{agent_id}"
        
        unified_data["player_agent_mapping"] = player_agent_mapping
        # 修正player_positions的逻辑，使其与player_agent_mapping保持一致
        # player_positions应该表示每个player位置对应的agent索引
        corrected_player_positions = [None] * 3
        for agent_id, player_id in enumerate(player_positions):
            corrected_player_positions[player_id] = agent_id
        unified_data["player_positions"] = corrected_player_positions
        
        # 添加调试信息，验证映射关系
        print(f"调试信息: player_positions={player_positions}")
        print(f"调试信息: corrected_player_positions={corrected_player_positions}")
        print(f"调试信息: player_agent_mapping={player_agent_mapping}")
        
        # 验证映射关系是否正确
        for player_id in range(3):
            agent_id = corrected_player_positions[player_id]
            print(f"调试信息: Player {player_id} -> Agent {agent_id} ({agent_info[f'agent_{agent_id}']['model_name']})")
    
    # 处理游戏日志，将其转换为统一格式
    current_observation = {}
    current_model_input = {}
    
    for entry in game_log:
        if entry["type"] == "observation":
            # 保存观察信息
            player_id = entry["player_id"]
            current_observation[player_id] = {
                "timestamp": entry["timestamp"],
                "observation": entry["content"]
            }
            
            # 准备模型输入信息
            agent_key = f"agent_{player_id}"
            if agent_key in agent_info:
                model_info = agent_info[agent_key]
                # 三级获取system_prompt：
                # 1. 从model_info直接获取
                # 2. 从model_info的config中获取
                # 3. 从prompt文件中加载
                system_prompt = model_info.get("system_prompt", "")
                if not system_prompt and "config" in model_info:
                    system_prompt = model_info["config"].get("system_prompt", "")
                
                # 如果仍然没有system_prompt，则从prompt文件中加载
                if not system_prompt and "prompt_name" in model_info:
                    try:
                        # 获取当前文件的目录
                        current_dir = os.path.dirname(os.path.abspath(__file__))
                        # 构建prompt文件路径
                        prompt_path = os.path.join(
                            current_dir,  # 项目根目录
                            "prompt_pool", 
                            model_info.get("game_type", "three_player_ipd"), 
                            f"pool_{'A' if agent_key == 'agent_0' else 'B'}", 
                            f"{model_info['prompt_name']}.txt"
                        )
                        # 检查文件是否存在
                        if os.path.exists(prompt_path):
                            # 以UTF-8编码读取文件
                            with open(prompt_path, 'r', encoding='utf-8') as f:
                                system_prompt = f.read()
                        else:
                            print(f"警告: 找不到prompt文件 {prompt_path}")
                    except Exception as e:
                        print(f"加载prompt文件时出错: {e}")
                        pass  # 如果加载失败，保持为空字符串
                
                # 将system_prompt添加到model_info中
                model_info["system_prompt"] = system_prompt
                
                current_model_input[player_id] = {
                    "system_prompt": system_prompt,
                    "user_message": entry["content"],
                    "model": model_info.get("model_name", ""),
                    "was_summarised": False
                }
                
        elif entry["type"] == "action":
            # 保存动作信息
            player_id = entry["player_id"]
            if player_id in current_observation:
                step_data = {
                    "step_num": len(unified_data["steps"]),
                    "player_id": player_id,
                    "timestamp": current_observation[player_id]["timestamp"],
                    "observation": current_observation[player_id]["observation"],
                    "action": entry["content"],
                    "model_input": current_model_input.get(player_id, {}),
                    "model_output": {
                        "raw_response": entry["content"]
                    }
                }
                unified_data["steps"].append(step_data)
    
    # 添加agents信息
    unified_data["agents"] = {
        "agent_0": {
            "type": "Agent0",
            "model": agent_info.get("agent_0", {}).get("model_name", ""),
            "prompt": agent_info.get("agent_0", {}).get("prompt_name", "")
        },
        "agent_1": {
            "type": "Agent1",
            "model": agent_info.get("agent_1", {}).get("model_name", ""),
            "prompt": agent_info.get("agent_1", {}).get("prompt_name", "")
        },
        "agent_2": {
            "type": "Agent2",
            "model": agent_info.get("agent_2", {}).get("model_name", ""),
            "prompt": agent_info.get("agent_2", {}).get("prompt_name", "")
        }
    }
    
    # 添加final_results部分
    if result and "rewards" in result:
        # 确定胜者 - 基于当前分数
        rewards = result["rewards"]
        # 确保rewards使用整数键
        if isinstance(rewards, dict):
            # 检查键是否为字符串，如果是则转换为整数
            if all(isinstance(k, str) for k in rewards.keys()):
                rewards = {int(k): v for k, v in rewards.items()}
            
            # 如果是字典格式，直接比较分数
            max_reward = max(rewards.values())
            winners = [player for player, reward in rewards.items() if reward == max_reward]
        else:
            # 如果是列表格式，比较列表中的分数
            max_reward = max(rewards)
            winners = [i for i, reward in enumerate(rewards) if reward == max_reward]
        
        # 设置winner为第一个胜者（如果有的话）
        winner = winners[0] if winners else None
        
        # 生成游戏结果描述
        if len(winners) == 1:
            reason = f"Player {winner} wins with {max_reward} points!"
        else:
            # 平局情况，显示所有玩家分数
            if isinstance(rewards, dict):
                scores = [rewards[pid] for pid in sorted(rewards.keys())]
            else:
                scores = rewards
            reason = f"Game ends in a {scores[0]}-{scores[1]}-{scores[2]} tie after {result.get('steps', 0)} rounds!"
        
        # 尝试从游戏日志中提取实际累加分数
        actual_scores = {}
        try:
            # 查找包含"Current scores:"的observation
            for entry in game_log:
                if entry["type"] == "observation" and "Current scores:" in entry["content"]:
                    # 使用正则表达式提取分数
                    import re
                    score_pattern = r"Current scores: P0=(\d+), P1=(\d+), P2=(\d+)"
                    match = re.search(score_pattern, entry["content"])
                    if match:
                        actual_scores[0] = float(match.group(1))
                        actual_scores[1] = float(match.group(2))
                        actual_scores[2] = float(match.group(3))
                        print(f"提取到实际累加分数: {actual_scores}")
                        break
        except Exception as e:
            print(f"提取实际累加分数时出错: {e}")
            actual_scores = {}
        
        # 添加final_results，与上校博弈格式保持一致
        # 创建agent_rewards，将player_id的rewards映射到agent_id
        agent_rewards = {}
        normalized_agent_rewards = {}  # 保存归一化分数用于对比
        
        # 确定使用实际分数还是归一化分数
        use_actual_scores = len(actual_scores) == 3
        
        if player_positions is not None:
            for player_id, reward in rewards.items():
                # 找到这个player位置对应的agent
                agent_id = None
                for i, pos in enumerate(player_positions):
                    if pos == player_id:
                        agent_id = i
                        break
                if agent_id is not None:
                    # 如果有实际分数，使用实际分数，否则使用归一化分数
                    if use_actual_scores and player_id in actual_scores:
                        agent_rewards[agent_id] = actual_scores[player_id]
                        normalized_agent_rewards[agent_id] = reward
                    else:
                        agent_rewards[agent_id] = reward
            
            # 添加调试信息
            print(f"调试信息: 原始rewards (player_id -> reward): {rewards}")
            if use_actual_scores:
                print(f"调试信息: 实际累加分数 (player_id -> actual_score): {actual_scores}")
            print(f"调试信息: 映射后rewards (agent_id -> reward): {agent_rewards}")
            
            # 验证映射关系
            for agent_id, reward in agent_rewards.items():
                player_pos = player_positions[agent_id]
                model_name = agent_info[f"agent_{agent_id}"]["model_name"]
                score_type = "实际累加分数" if use_actual_scores else "归一化分数"
                print(f"调试信息: Agent {agent_id} ({model_name}) 在Player {player_pos}位置，{score_type}: {reward}")
        
        # 如果无法映射，则使用原始的player_id作为键
        if not agent_rewards:
            if use_actual_scores:
                agent_rewards = actual_scores
            else:
                agent_rewards = rewards
            print(f"调试信息: 无法映射，使用原始rewards: {agent_rewards}")
    
        # 构建final_results
        final_results_data = {
            "rewards": agent_rewards,  # 使用实际累加分数（如果有）或归一化分数
            "game_info": {
                "0": {
                    "role": "Player 0",
                    "invalid_move": False,
                    "turn_count": result.get('steps', 0),
                    "reason": reason
                },
                "1": {
                    "role": "Player 1",
                    "invalid_move": False,
                    "turn_count": result.get('steps', 0),
                    "reason": reason
                },
                "2": {
                    "role": "Player 2",
                    "invalid_move": False,
                    "turn_count": result.get('steps', 0),
                    "reason": reason
                }
            },
            "timestamp": datetime.now().isoformat(),
            "status": "completed",
            "total_steps": result.get("steps", 0)
        }
        
        # 如果有实际分数，添加归一化分数用于对比
        if use_actual_scores and normalized_agent_rewards:
            final_results_data["normalized_rewards"] = normalized_agent_rewards
        
        unified_data["final_results"] = final_results_data
    
    # 保存统一格式的游戏数据
    data_file = run_dir / f"{timestamp}_three_player_ipd.json"
    with open(data_file, 'w', encoding='utf-8') as f:
        json.dump(unified_data, f, ensure_ascii=False, indent=2)
    
    # 同时保存agent信息（保持原格式）
    info_file = run_dir / "agent_info.json"
    with open(info_file, 'w', encoding='utf-8') as f:
        json.dump(agent_info, f, ensure_ascii=False, indent=2)
    
    return run_dir

def run_single_three_player_ipd(args, run_number, verbose=True):
    """运行单次三人囚徒困境游戏"""
    if verbose:
        print(f"\n开始第 {run_number} 次游戏...")
    
    # 加载配置
    config = load_config()
    game_config = config["games"]["three_player_ipd"]
    
    try:
        # 随机分配agent位置，player_positions[i] = j 表示agent i 被分配到 player j 的位置
        player_positions = random.sample([0, 1, 2], 3)
        
        # 创建agents
        agent_0 = Agent0(
            game_type="three_player_ipd",
            model_name=args.model_0,
            prompt_name=args.prompt_0,
            token_pool_type="three_player_ipd"  # 使用3PIPD令牌池
        )
        
        agent_1 = Agent1(
            game_type="three_player_ipd", 
            model_name=args.model_1,
            prompt_name=args.prompt_1,
            token_pool_type="three_player_ipd"  # 使用3PIPD令牌池
        )
        
        agent_2 = Agent2(
            game_type="three_player_ipd", 
            model_name=args.model_2,
            prompt_name=args.prompt_2,
            token_pool_type="three_player_ipd"  # 使用3PIPD令牌池
        )
        
        # 如果禁用详细输出，设置agent为非verbose模式
        if args.disable_verbose:
            # 修改agent的verbose设置
            if hasattr(agent_0.agent_instance, 'verbose'):
                agent_0.agent_instance.verbose = False
            if hasattr(agent_1.agent_instance, 'verbose'):
                agent_1.agent_instance.verbose = False
            if hasattr(agent_2.agent_instance, 'verbose'):
                agent_2.agent_instance.verbose = False
        
        # 设置重试参数
        max_retries = getattr(args, 'max_retries', 3)
        retry_delay = getattr(args, 'retry_delay', 5)
        
        # 如果agent实例支持设置重试参数，则设置
        if hasattr(agent_0.agent_instance, '_retry_request'):
            pass
        if hasattr(agent_1.agent_instance, '_retry_request'):
            pass
        if hasattr(agent_2.agent_instance, '_retry_request'):
            pass
        
        # 设置stream参数
        if hasattr(args, 'stream') and args.stream:
            if hasattr(agent_0.agent_instance, 'stream'):
                agent_0.agent_instance.stream = True
            if hasattr(agent_1.agent_instance, 'stream'):
                agent_1.agent_instance.stream = True
            if hasattr(agent_2.agent_instance, 'stream'):
                agent_2.agent_instance.stream = True
        
        # 设置连接池参数
        if hasattr(args, 'no_connection_pool') and args.no_connection_pool:
            if hasattr(agent_0.agent_instance, 'use_connection_pool'):
                agent_0.agent_instance.use_connection_pool = False
            if hasattr(agent_1.agent_instance, 'use_connection_pool'):
                agent_1.agent_instance.use_connection_pool = False
            if hasattr(agent_2.agent_instance, 'use_connection_pool'):
                agent_2.agent_instance.use_connection_pool = False
        
        # 设置令牌池参数
        if hasattr(args, 'no_token_pool') and args.no_token_pool:
            if hasattr(agent_0.agent_instance, 'use_token_pool'):
                agent_0.agent_instance.use_token_pool = False
            if hasattr(agent_1.agent_instance, 'use_token_pool'):
                agent_1.agent_instance.use_token_pool = False
            if hasattr(agent_2.agent_instance, 'use_token_pool'):
                agent_2.agent_instance.use_token_pool = False
        
        # 设置游戏管理器
        manager = GameManager()
        manager.setup_game("three_player_ipd")
        
        # 根据随机结果添加agents到不同位置
        agents = [agent_0, agent_1, agent_2]
        for i in range(3):
            # player_positions[i] 表示agent i 被分配到哪个player位置
            player_pos = player_positions[i]
            manager.add_agent(agents[i], player_pos)  # 将agent i添加到player_pos位置
        
        # 调试信息：打印agent到player的映射关系
        if verbose:
            print(f"调试信息: Agent到Player的映射关系:")
            for i in range(3):
                print(f"  Agent {i} -> Player {player_positions[i]}")
        
        # 收集游戏日志
        game_log = []
        current_scores = {0: 0.0, 1: 0.0, 2: 0.0}
        
        # 设置回调函数 - 增加详细输出和分数跟踪
        player_names = ["Player_0", "Player_1", "Player_2"]
        def observation_callback(player_id, obs):
            # 记录观察
            game_log.append({
                "timestamp": datetime.now().isoformat(),
                "type": "observation",
                "player_id": player_id,
                "player_name": player_names[player_id],
                "content": obs
            })
            if verbose and not args.disable_verbose:
                print_colored(f"\n===== 观察 ({player_names[player_id]}) =====", "blue")
                print(obs)
            
        def action_callback(player_id, action):
            # 记录动作
            game_log.append({
                "timestamp": datetime.now().isoformat(),
                "type": "action",
                "player_id": player_id,
                "player_name": player_names[player_id],
                "content": action
            })
            if verbose and not args.disable_verbose:
                action_preview = action.replace('\n', ' ').strip()
                print_colored(f"执行动作 ({player_names[player_id]}): {action_preview}", "green")
            
        def step_complete_callback(done, info):
            nonlocal current_scores
            # 记录回合结束
            game_log.append({
                "timestamp": datetime.now().isoformat(),
                "type": "step_complete",
                "done": done,
                "info": info
            })
            
            # 如果有分数更新，更新当前分数
            if "current_scores" in info:
                current_scores = info["current_scores"].copy()
                if verbose and not args.disable_verbose:
                    print_colored(f"\n===== 步骤完成 =====", "yellow")
                    print(f"游戏结束: {done}")
                    print(f"当前分数: {current_scores}")
        
        callbacks = {
            "on_observation": observation_callback,
            "on_action": action_callback,
            "on_step_complete": step_complete_callback
        }
        
        # 启动游戏
        manager.start_game()
        result = manager.play_game(callbacks=callbacks)
        
        # 获取GameManager的日志路径
        log_path = manager.logger.json_path if manager.logger else None
        
        # 确定胜者 - 基于当前分数
        rewards = current_scores
        if isinstance(rewards, dict):
            # 如果是字典格式，直接比较分数
            max_reward = max(rewards.values())
            winners = [player for player, reward in rewards.items() if reward == max_reward]
        else:
            # 如果是列表格式，比较列表中的分数
            max_reward = max(rewards)
            winners = [i for i, reward in enumerate(rewards) if reward == max_reward]
        
        # 判断agent0是否是胜者
        agent0_is_winner = False
        if player_positions:
            # 找到agent0对应的player位置
            agent0_player_pos = player_positions.index(0)
            agent0_is_winner = (agent0_player_pos in winners)
        else:
            # 如果没有player_positions映射，假设agent0对应player0
            agent0_is_winner = (0 in winners)
        
        # 设置winner为第一个胜者（如果有的话）
        winner = winners[0] if winners else None
        
        # 调试信息：打印agent0的胜者状态
        if verbose:
            print(f"调试信息: Agent0被分配到Player {agent0_player_pos}位置")
            print(f"调试信息: 游戏胜者是Player {winner}")
            print(f"调试信息: Agent0是否获胜: {agent0_is_winner}")
            print_colored("\n===== 游戏结果 =====", "magenta")
            print(f"总步数: {result['steps']}")
            print(f"当前分数: {current_scores}")
            print(f"胜者: {winner}")
            print(f"Agent0获胜: {agent0_is_winner}")
            if log_path:
                print(f"日志路径: {log_path}")

        # 记录游戏结果 - 使用当前分数作为最终分数
        final_result = result.copy()
        final_result["rewards"] = current_scores
        
        game_log.append({
            "timestamp": datetime.now().isoformat(),
            "type": "game_result",
            "result": final_result,
            "log_path": log_path
        })

        # 准备agent信息
        agent_info = {
            "agent_0": agent_0.get_model_info(),
            "agent_1": agent_1.get_model_info(),
            "agent_2": agent_2.get_model_info(),
            "game": "three_player_ipd",
            "timestamp": datetime.now().isoformat(),
            "run_id": str(uuid.uuid4()),
            "run_number": run_number
        }

        # 保存游戏数据
        data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), game_config["data_dir"], "batch_runs")
        run_dir = save_game_data(data_dir, game_log, agent_info, run_number, final_result, player_positions)

        # 显示简要结果
        if verbose:
            winner_text = f"Agent{winner}" if winner is not None else "平局"
            # 获取三个玩家的得分
            r0 = current_scores.get(0, 0.0)
            r1 = current_scores.get(1, 0.0)
            r2 = current_scores.get(2, 0.0)
            total_score = r0 + r1 + r2
            print(f"第 {run_number} 次游戏完成 - 胜者: {winner_text}, 步数: {result['steps']}")
            print(f"  玩家得分: 玩家0={r0}, 玩家1={r1}, 玩家2={r2}, 总分={total_score}")
            
            # 调试信息：打印每个玩家对应的Agent
            print(f"调试信息: 玩家到Agent的映射关系:")
            for player_id in range(3):
                agent_id = None
                for i, pos in enumerate(player_positions):
                    if pos == player_id:
                        agent_id = i
                        break
                agent_name = f"Agent{agent_id}" if agent_id is not None else "Unknown"
                model_name = agent_info[f"agent_{agent_id}"]["model_name"] if agent_id is not None else "Unknown"
                print(f"  Player {player_id} -> {agent_name} ({model_name})")

        return {
            "result": final_result,
            "winner": winner,
            "agent0_is_winner": agent0_is_winner,
            "player_positions": player_positions,  # 记录agent位置分配
            "agent_info": agent_info,
            "run_dir": run_dir,
            "log_path": log_path,
            "current_scores": current_scores
        }
        
    except Exception as e:
        if verbose:
            print(f"第 {run_number} 次游戏失败: {e}")
            import traceback
            traceback.print_exc()
        return None

def run_single_game_wrapper(args, run_number, verbose=True):
    """包装单次游戏运行，用于多进程"""
    result = run_single_three_player_ipd(args, run_number, verbose=verbose)
    return (run_number, result)

def run_parallel_three_player_ipd(args):
    """并行运行三人囚徒困境游戏"""
    print(f"开始批量运行 {args.num_runs} 局三人囚徒困境对战...")
    print(f"并行进程数: {args.num_processes}")
    
    # 统计信息
    stats = {
        "total_runs": 0,
        "agent0_wins": 0,
        "errors": 0,
        "start_time": datetime.now().isoformat(),
        "results": []
    }
    
    # 创建批量运行目录
    config = load_config()
    game_config = config["games"]["three_player_ipd"]
    batch_dir = Path(os.path.join(os.path.dirname(os.path.abspath(__file__)), game_config["data_dir"], "batch_runs"))
    batch_dir.mkdir(parents=True, exist_ok=True)
    
    # 创建进程池
    pool = multiprocessing.Pool(processes=args.num_processes)
    
    # 准备任务参数
    tasks = [(args, run_number, args.verbose) for run_number in range(1, args.num_runs + 1)]
    
    # 如果设置了禁用详细输出，修改args中的verbose标志
    if args.disable_verbose:
        # 创建一个新的args对象，禁用verbose
        import copy
        tasks = [(copy.copy(args), run_number, False) for run_number in range(1, args.num_runs + 1)]
        # 确保禁用详细输出
        for task_args, _, _ in tasks:
            task_args.disable_verbose = True
            task_args.verbose = False
    
    # 并行运行游戏
    start_time = time.time()
    
    try:
        # 使用imap_unordered获取结果，不保证顺序但可以提高效率
        results_iter = pool.starmap(run_single_game_wrapper, tasks)
        
        # 处理结果
        for run_number, game_result in results_iter:
            print(f"\n=== 第 {run_number} 局 ===")
            
            if game_result:
                stats["total_runs"] += 1
                
                # 记录agent0是否获胜
                if game_result["agent0_is_winner"]:
                    stats["agent0_wins"] += 1
                    winner_text = "Agent0获胜"
                else:
                    winner_text = "Agent0未获胜"
                
                # 获取奖励
                rewards = game_result["result"]["rewards"]
                r0 = rewards.get(0, 0.0)
                r1 = rewards.get(1, 0.0)
                r2 = rewards.get(2, 0.0)
                
                # 保存单次结果
                # 确保rewards使用整数键
                fixed_rewards = {}
                for k, v in rewards.items():
                    fixed_rewards[int(k)] = v
                
                stats["results"].append({
                    "run_number": run_number,
                    "agent0_is_winner": game_result["agent0_is_winner"],
                    "rewards": fixed_rewards,
                    "steps": game_result["result"]["steps"],
                    "run_dir": str(game_result["run_dir"])
                })
                
                # 显示结果
                print(f"解析结果 -> 玩家0: {r0}, 玩家1: {r1}, 玩家2: {r2}, 结果: {winner_text}")
                print(f"   └── 原始日志: {game_result['run_dir']}")
                
                # 显示当前统计 - 只在关键节点显示
                if stats["total_runs"] % 5 == 0 or stats["total_runs"] == args.num_runs:
                    if stats["total_runs"] > 0:
                        agent0_win_rate = stats["agent0_wins"] / stats["total_runs"]
                        print(f"  进度: {stats['total_runs']}/{args.num_runs} | Agent0胜率: {agent0_win_rate:.2%} | 错误: {stats['errors']}")
            else:
                stats["errors"] += 1
                print(f"❌ 第 {run_number} 次运行出错")
            
            # 保存中间统计结果
            if stats["total_runs"] % 10 == 0 or stats["total_runs"] == args.num_runs:
                stats["end_time"] = datetime.now().isoformat()
                stats_file = batch_dir / "batch_stats.json"
                with open(stats_file, 'w', encoding='utf-8') as f:
                    json.dump(stats, f, ensure_ascii=False, indent=2)
        
    except Exception as e:
        print(f"❌ 并行运行过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # 关闭进程池
        pool.close()
        pool.join()
    
    elapsed_time = time.time() - start_time
    
    # 计算最终统计
    stats["end_time"] = datetime.now().isoformat()
    if stats["total_runs"] > 0:
        stats["agent0_win_rate"] = stats["agent0_wins"] / stats["total_runs"]
        
        # 计算所有玩家的平均得分和总分统计
        total_r0 = 0
        total_r1 = 0
        total_r2 = 0
        total_all = 0
        
        for result in stats["results"]:
            rewards = result["rewards"]
            total_r0 += rewards.get(0, 0.0)
            total_r1 += rewards.get(1, 0.0)
            total_r2 += rewards.get(2, 0.0)
            total_all += rewards.get(0, 0.0) + rewards.get(1, 0.0) + rewards.get(2, 0.0)
        
        stats["avg_score_player0"] = total_r0 / stats["total_runs"]
        stats["avg_score_player1"] = total_r1 / stats["total_runs"]
        stats["avg_score_player2"] = total_r2 / stats["total_runs"]
        stats["avg_total_score"] = total_all / stats["total_runs"]
        stats["total_score_player0"] = total_r0
        stats["total_score_player1"] = total_r1
        stats["total_score_player2"] = total_r2
        stats["grand_total_score"] = total_all
    else:
        stats["agent0_win_rate"] = 0
        stats["avg_score_player0"] = 0
        stats["avg_score_player1"] = 0
        stats["avg_score_player2"] = 0
        stats["avg_total_score"] = 0
        stats["total_score_player0"] = 0
        stats["total_score_player1"] = 0
        stats["total_score_player2"] = 0
        stats["grand_total_score"] = 0
    
    # 保存最终统计结果
    stats_file = batch_dir / "batch_stats_final.json"
    with open(stats_file, 'w', encoding='utf-8') as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)
    
    # 显示最终统计
    print("\n" + "="*50)
    print("批量运行完成")
    print("="*50)
    print(f"总计划局数: {args.num_runs}")
    print(f"成功完成局数: {stats['total_runs']}")
    print(f"失败局数: {stats['errors']}")
    print(f"Agent0 胜率: {stats['agent0_win_rate']:.2%}")
    print("-"*50)
    print("得分统计:")
    print(f"玩家0 - 平均得分: {stats['avg_score_player0']:.2f}, 总得分: {stats['total_score_player0']}")
    print(f"玩家1 - 平均得分: {stats['avg_score_player1']:.2f}, 总得分: {stats['total_score_player1']}")
    print(f"玩家2 - 平均得分: {stats['avg_score_player2']:.2f}, 总得分: {stats['total_score_player2']}")
    print(f"每局平均总分: {stats['avg_total_score']:.2f}")
    print(f"所有局数总分: {stats['grand_total_score']}")
    print("="*50)
    
    # 保存结果到CSV文件
    out_csv = Path("player0_batch_results_3pipd_parallel.csv")
    with out_csv.open("w", encoding="utf-8") as f:
        f.write("game_index,reward_player0,reward_player1,reward_player2,agent0_is_winner\n")
        for rec in stats["results"]:
            rewards = rec["rewards"]
            f.write(f"{rec['run_number']},{rewards.get(0, 0.0)},{rewards.get(1, 0.0)},{rewards.get(2, 0.0)},{rec['agent0_is_winner']}\n")
    print(f"\n结果明细已保存: {out_csv}")
    print(f"统计结果已保存到: {stats_file}")
    
    return stats

def main():
    parser = argparse.ArgumentParser(description="三人囚徒困境并行批量运行")
    parser.add_argument("--num_runs", type=int, default=10, help="运行次数 (默认: 10)")
    parser.add_argument("--num_processes", type=int, default=3, help="并行进程数 (默认: 3)")
    parser.add_argument("--model_0", type=str, help="Agent0使用的模型名称")
    parser.add_argument("--prompt_0", type=str, help="Agent0使用的提示名称")
    parser.add_argument("--model_1", type=str, help="Agent1使用的模型名称")
    parser.add_argument("--prompt_1", type=str, help="Agent1使用的提示名称")
    parser.add_argument("--model_2", type=str, help="Agent2使用的模型名称")
    parser.add_argument("--prompt_2", type=str, help="Agent2使用的提示名称")
    parser.add_argument("--verbose", action="store_true", help="显示运行信息")
    parser.add_argument("--disable_verbose", action="store_true", help="禁用agent详细输出以提高性能")
    parser.add_argument("--max_retries", type=int, default=3, help="API调用最大重试次数 (默认: 3)")
    parser.add_argument("--retry_delay", type=int, default=5, help="API调用重试延迟秒数 (默认: 5)")
    parser.add_argument("--stream", action="store_true", help="启用流式输出模式，可能提高响应速度")
    parser.add_argument("--no_connection_pool", action="store_true", help="禁用连接池，每个agent使用独立的连接")
    parser.add_argument("--no_token_pool", action="store_true", help="禁用令牌池，使用原始配置的令牌")
    
    args = parser.parse_args()
    
    try:
        stats = run_parallel_three_player_ipd(args)
        if stats:
            print(f"\n并行批量运行完成!")
        else:
            print(f"\n并行批量运行失败")
    except KeyboardInterrupt:
        print(f"\n用户中断")
    except Exception as e:
        print(f"\n系统错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()