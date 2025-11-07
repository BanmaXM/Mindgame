#!/usr/bin/env python3
"""
混合游戏并行运行脚本
同时并行运行上校博弈和三人囚徒困境游戏，共享令牌池以避免令牌冲突
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
import threading

# 添加项目路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils.game_manager import GameManager
from agents.agent_0 import Agent0
from agents.agent_1 import Agent1
from agents.agent_2 import Agent2
from datetime import datetime
from pathlib import Path
import uuid

def save_game_data(data_dir, game_log, agent_info):
    """保存游戏数据为统一格式"""
    # 创建时间戳目录
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    run_dir = Path(data_dir) / timestamp
    run_dir.mkdir(parents=True, exist_ok=True)
    
    # 转换游戏日志为统一格式
    unified_data = {
        "game_name": "three_player_ipd",
        "timestamp": agent_info["timestamp"],
        "steps": []
    }
    
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
    
    # 保存统一格式的游戏数据
    data_file = run_dir / f"{timestamp}_three_player_ipd.json"
    with open(data_file, 'w', encoding='utf-8') as f:
        json.dump(unified_data, f, ensure_ascii=False, indent=2)
    
    # 同时保存agent信息（保持原格式）
    info_file = run_dir / "agent_info.json"
    with open(info_file, 'w', encoding='utf-8') as f:
        json.dump(agent_info, f, ensure_ascii=False, indent=2)
    
    return run_dir
from token_pool import initialize_token_pools, token_pool

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

def run_single_colonel_blotto(args, run_number, verbose=True):
    """运行单次上校博弈游戏"""
    if verbose:
        print(f"\n开始第 {run_number} 次上校博弈游戏...")
    
    # 加载配置
    config = load_config()
    game_config = config["games"]["colonel_blotto"]
    
    try:
        # 随机分配agent位置
        agent_positions = random.randint(0, 1)
        
        # 创建agents
        agent_0 = Agent0(
            game_type="colonel_blotto",
            model_name=args.model_0,
            prompt_name=args.prompt_0
        )
        
        agent_1 = Agent1(
            game_type="colonel_blotto", 
            model_name=args.model_1,
            prompt_name=args.prompt_1
        )
        
        # 如果禁用详细输出，设置agent为非verbose模式
        if args.disable_verbose:
            # 修改agent的verbose设置
            if hasattr(agent_0.agent_instance, 'verbose'):
                agent_0.agent_instance.verbose = False
            if hasattr(agent_1.agent_instance, 'verbose'):
                agent_1.agent_instance.verbose = False
        
        # 设置重试参数
        max_retries = getattr(args, 'max_retries', 3)
        retry_delay = getattr(args, 'retry_delay', 5)
        
        # 如果agent实例支持设置重试参数，则设置
        if hasattr(agent_0.agent_instance, '_retry_request'):
            pass
        if hasattr(agent_1.agent_instance, '_retry_request'):
            pass
        
        # 设置stream参数
        if hasattr(args, 'stream') and args.stream:
            if hasattr(agent_0.agent_instance, 'stream'):
                agent_0.agent_instance.stream = True
            if hasattr(agent_1.agent_instance, 'stream'):
                agent_1.agent_instance.stream = True
        
        # 设置连接池参数
        if hasattr(args, 'no_connection_pool') and args.no_connection_pool:
            if hasattr(agent_0.agent_instance, 'use_connection_pool'):
                agent_0.agent_instance.use_connection_pool = False
            if hasattr(agent_1.agent_instance, 'use_connection_pool'):
                agent_1.agent_instance.use_connection_pool = False
        
        # 设置令牌池参数
        if hasattr(args, 'no_token_pool') and args.no_token_pool:
            if hasattr(agent_0.agent_instance, 'use_token_pool'):
                agent_0.agent_instance.use_token_pool = False
            if hasattr(agent_1.agent_instance, 'use_token_pool'):
                agent_1.agent_instance.use_token_pool = False
        
        # 设置游戏管理器
        manager = GameManager()
        manager.setup_game("colonel_blotto")
        
        # 根据随机结果添加agents到不同位置
        if agent_positions == 0:
            # agent0是player0，agent1是player1
            manager.add_agent(agent_0)  # Player 0
            manager.add_agent(agent_1)  # Player 1
        else:
            # agent0是player1，agent1是player0
            manager.add_agent(agent_1)  # Player 0
            manager.add_agent(agent_0)  # Player 1
        
        # 收集游戏日志
        game_log = []
        
        # 设置回调函数 - 减少详细输出
        def observation_callback(player_id, obs):
            # 记录观察但不打印
            game_log.append({
                "timestamp": datetime.now().isoformat(),
                "type": "observation",
                "player_id": player_id,
                "player_name": "Agent0" if player_id == 0 else "Agent1",
                "content": obs
            })
            
        def action_callback(player_id, action):
            # 记录动作但不打印
            game_log.append({
                "timestamp": datetime.now().isoformat(),
                "type": "action",
                "player_id": player_id,
                "player_name": "Agent0" if player_id == 0 else "Agent1",
                "content": action
            })
            
        def step_complete_callback(done, info):
            # 记录回合结束但不打印
            game_log.append({
                "timestamp": datetime.now().isoformat(),
                "type": "step_complete",
                "done": done,
                "info": info
            })
        
        callbacks = {
            "on_observation": observation_callback,
            "on_action": action_callback,
            "on_step_complete": step_complete_callback
        }
        
        # 启动游戏
        manager.start_game()
        result = manager.play_game(callbacks=callbacks)
        
        # 确定胜者
        winner = None
        if "rewards" in result and result["rewards"]:
            max_reward = max(result["rewards"].values())
            winners = [pid for pid, r in result["rewards"].items() if r == max_reward]
            winner = winners[0] if len(winners) == 1 else None  # 如果平局，winner为None
        
        # 确定实际agent0的胜者状态
        agent0_is_winner = False
        if agent_positions == 0:  # agent0是player0
            agent0_is_winner = (winner == 0)
        else:  # agent0是player1
            agent0_is_winner = (winner == 1)
        
        # 显示简要结果
        if verbose:
            winner_text = f"Agent{winner}" if winner is not None else "平局"
            print(f"第 {run_number} 次上校博弈游戏完成 - 胜者: {winner_text}, 步数: {result['steps']}")
        
        return {
            "game_type": "colonel_blotto",
            "run_number": run_number,
            "result": result,
            "winner": winner,
            "agent0_is_winner": agent0_is_winner,
            "agent_positions": agent_positions,
            "steps": result.get('steps', 0)
        }
        
    except Exception as e:
        if verbose:
            print(f"第 {run_number} 次上校博弈游戏失败: {e}")
        return {
            "game_type": "colonel_blotto",
            "run_number": run_number,
            "error": str(e)
        }

def run_single_three_player_ipd(args, run_number, verbose=True):
    """运行单次三人囚徒困境游戏"""
    if verbose:
        print(f"\n开始第 {run_number} 次三人囚徒困境游戏...")
    
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
            prompt_name=args.prompt_0
        )
        
        agent_1 = Agent1(
            game_type="three_player_ipd", 
            model_name=args.model_1,
            prompt_name=args.prompt_1
        )
        
        agent_2 = Agent2(
            game_type="three_player_ipd", 
            model_name=args.model_2,
            prompt_name=args.prompt_2
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
            # 找到agent i 应该被添加到哪个player位置
            player_pos = player_positions.index(i)
            manager.add_agent(agents[player_pos])  # 添加到对应位置
        
        # 收集游戏日志
        game_log = []
        
        # 设置回调函数 - 减少详细输出
        def observation_callback(player_id, obs):
            # 记录观察但不打印
            game_log.append({
                "timestamp": datetime.now().isoformat(),
                "type": "observation",
                "player_id": player_id,
                "player_name": "Agent0" if player_id == 0 else "Agent1" if player_id == 1 else "Agent2",
                "content": obs
            })
            
        def action_callback(player_id, action):
            # 记录动作但不打印
            game_log.append({
                "timestamp": datetime.now().isoformat(),
                "type": "action",
                "player_id": player_id,
                "player_name": "Agent0" if player_id == 0 else "Agent1" if player_id == 1 else "Agent2",
                "content": action
            })
            
        def step_complete_callback(done, info):
            # 记录回合结束但不打印
            game_log.append({
                "timestamp": datetime.now().isoformat(),
                "type": "step_complete",
                "done": done,
                "info": info
            })
        
        callbacks = {
            "on_observation": observation_callback,
            "on_action": action_callback,
            "on_step_complete": step_complete_callback
        }
        
        # 启动游戏
        manager.start_game()
        result = manager.play_game(callbacks=callbacks)
        
        # 确定胜者
        winner = None
        if "rewards" in result and result["rewards"]:
            max_reward = max(result["rewards"].values())
            winners = [pid for pid, r in result["rewards"].items() if r == max_reward]
            winner = winners[0] if len(winners) == 1 else None  # 如果平局，winner为None

        # 确定实际agent0的胜者状态
        # 找到agent0被分配到哪个player位置
        agent0_player_pos = player_positions.index(0)
        # 如果agent0所在的player位置获胜，则agent0获胜
        agent0_is_winner = (winner == agent0_player_pos)

        # 记录游戏结果
        game_log.append({
            "timestamp": datetime.now().isoformat(),
            "type": "game_result",
            "result": result
        })
        
        # 准备agent信息
        agent_info = {
            "agent_0": agent_0.get_model_info(),
            "agent_1": agent_1.get_model_info(),
            "agent_2": agent_2.get_model_info(),
            "game": "three_player_ipd",
            "timestamp": datetime.now().isoformat(),
            "run_id": str(uuid.uuid4())
        }
        
        # 确保agent_info中的每个agent都包含system_prompt
        for agent_key in ["agent_0", "agent_1", "agent_2"]:
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
        
        # 保存游戏数据
        data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), game_config["data_dir"])
        run_dir = save_game_data(data_dir, game_log, agent_info)
        
        if verbose:
            print(f"第 {run_number} 次三人囚徒困境游戏数据已保存: {run_dir}")

        return {
            "game_type": "three_player_ipd",
            "run_number": run_number,
            "result": result,
            "winner": winner,
            "agent0_is_winner": agent0_is_winner,
            "player_positions": player_positions,
            "steps": result.get('steps', 0),
            "data_dir": str(run_dir)  # 添加数据目录路径
        }
        
    except Exception as e:
        if verbose:
            print(f"第 {run_number} 次三人囚徒困境游戏失败: {e}")
        return {
            "game_type": "three_player_ipd",
            "run_number": run_number,
            "error": str(e)
        }

def run_colonel_blotto_games(args, num_runs, num_processes, result_queue, verbose=True):
    """运行上校博弈游戏的进程函数"""
    print(f"开始运行 {num_runs} 局上校博弈游戏，使用 {num_processes} 个进程...")
    
    # 创建进程池
    pool = multiprocessing.Pool(processes=num_processes)
    
    # 准备任务参数
    tasks = [(args, run_number, verbose) for run_number in range(1, num_runs + 1)]
    
    # 如果设置了禁用详细输出，修改args中的verbose标志
    if args.disable_verbose:
        # 创建一个新的args对象，禁用verbose
        import copy
        tasks = [(copy.copy(args), run_number, False) for run_number in range(1, num_runs + 1)]
        # 确保禁用详细输出
        for task_args, _, _ in tasks:
            task_args.disable_verbose = True
            task_args.verbose = False
    
    # 并行运行游戏
    try:
        # 使用imap_unordered获取结果，不保证顺序但可以提高效率
        results_iter = pool.starmap(run_single_colonel_blotto, tasks)
        
        # 处理结果
        for result in results_iter:
            result_queue.put(("colonel_blotto", result))
        
    except Exception as e:
        print(f"❌ 上校博弈并行运行过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # 关闭进程池
        pool.close()
        pool.join()
    
    # 发送完成信号
    result_queue.put(("colonel_blotto_done", None))

def run_three_player_ipd_games(args, num_runs, num_processes, result_queue, verbose=True):
    """运行三人囚徒困境游戏的进程函数"""
    print(f"开始运行 {num_runs} 局三人囚徒困境游戏，使用 {num_processes} 个进程...")
    
    # 创建进程池
    pool = multiprocessing.Pool(processes=num_processes)
    
    # 准备任务参数
    tasks = [(args, run_number, verbose) for run_number in range(1, num_runs + 1)]
    
    # 如果设置了禁用详细输出，修改args中的verbose标志
    if args.disable_verbose:
        # 创建一个新的args对象，禁用verbose
        import copy
        tasks = [(copy.copy(args), run_number, False) for run_number in range(1, num_runs + 1)]
        # 确保禁用详细输出
        for task_args, _, _ in tasks:
            task_args.disable_verbose = True
            task_args.verbose = False
    
    # 并行运行游戏
    try:
        # 使用imap_unordered获取结果，不保证顺序但可以提高效率
        results_iter = pool.starmap(run_single_three_player_ipd, tasks)
        
        # 处理结果
        for result in results_iter:
            result_queue.put(("three_player_ipd", result))
        
    except Exception as e:
        print(f"❌ 三人囚徒困境并行运行过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # 关闭进程池
        pool.close()
        pool.join()
    
    # 发送完成信号
    result_queue.put(("three_player_ipd_done", None))

def run_mixed_games(args):
    """并行运行混合游戏"""
    print(f"开始混合游戏并行运行...")
    print(f"上校博弈: {args.num_blotto_runs} 局, {args.num_blotto_processes} 个进程")
    print(f"三人囚徒困境: {args.num_ipd_runs} 局, {args.num_ipd_processes} 个进程")
    
    # 初始化令牌池
    print("初始化令牌池...")
    initialize_token_pools()
    
    # 统计信息
    stats = {
        "start_time": datetime.now().isoformat(),
        "colonel_blotto": {
            "total_runs": 0,
            "agent0_wins": 0,
            "errors": 0,
            "results": []
        },
        "three_player_ipd": {
            "total_runs": 0,
            "agent0_wins": 0,
            "errors": 0,
            "results": []
        }
    }
    
    # 创建结果队列
    result_queue = multiprocessing.Queue()
    
    # 创建并启动上校博弈进程
    blotto_process = multiprocessing.Process(
        target=run_colonel_blotto_games,
        args=(args, args.num_blotto_runs, args.num_blotto_processes, result_queue, args.verbose)
    )
    
    # 创建并启动三人囚徒困境进程
    ipd_process = multiprocessing.Process(
        target=run_three_player_ipd_games,
        args=(args, args.num_ipd_runs, args.num_ipd_processes, result_queue, args.verbose)
    )
    
    # 启动进程
    blotto_process.start()
    ipd_process.start()
    
    # 等待所有结果
    blotto_done = False
    ipd_done = False
    total_games = args.num_blotto_runs + args.num_ipd_runs
    completed_games = 0
    
    while not (blotto_done and ipd_done):
        try:
            # 从队列获取结果，设置超时以避免无限等待
            game_type, result = result_queue.get(timeout=1)
            
            if game_type == "colonel_blotto_done":
                blotto_done = True
                print("上校博弈游戏全部完成")
            elif game_type == "three_player_ipd_done":
                ipd_done = True
                print("三人囚徒困境游戏全部完成")
            elif game_type == "colonel_blotto":
                # 处理上校博弈结果
                if "error" in result:
                    stats["colonel_blotto"]["errors"] += 1
                    print(f"❌ 上校博弈第 {result['run_number']} 次运行出错: {result['error']}")
                else:
                    stats["colonel_blotto"]["total_runs"] += 1
                    completed_games += 1
                    
                    if result["agent0_is_winner"]:
                        stats["colonel_blotto"]["agent0_wins"] += 1
                        winner_text = "Agent0获胜"
                    else:
                        winner_text = "Agent1获胜"
                    
                    # 保存结果
                    stats["colonel_blotto"]["results"].append({
                        "run_number": result["run_number"],
                        "agent0_is_winner": result["agent0_is_winner"],
                        "steps": result["steps"]
                    })
                    
                    # 显示结果
                    print(f"\n=== 上校博弈第 {result['run_number']} 局 ===")
                    print(f"结果: {winner_text}, 步数: {result['steps']}")
                    
                    # 显示当前进度
                    print(f"进度: {completed_games}/{total_games} | 上校博弈: {stats['colonel_blotto']['total_runs']}/{args.num_blotto_runs} | 三人IPD: {stats['three_player_ipd']['total_runs']}/{args.num_ipd_runs}")
            elif game_type == "three_player_ipd":
                # 处理三人囚徒困境结果
                if "error" in result:
                    stats["three_player_ipd"]["errors"] += 1
                    print(f"❌ 三人囚徒困境第 {result['run_number']} 次运行出错: {result['error']}")
                else:
                    stats["three_player_ipd"]["total_runs"] += 1
                    completed_games += 1
                    
                    if result["agent0_is_winner"]:
                        stats["three_player_ipd"]["agent0_wins"] += 1
                        winner_text = "Agent0获胜"
                    else:
                        winner_text = "Agent0未获胜"
                    
                    # 保存结果
                    stats["three_player_ipd"]["results"].append({
                        "run_number": result["run_number"],
                        "agent0_is_winner": result["agent0_is_winner"],
                        "steps": result["steps"],
                        "data_dir": result.get("data_dir", "")  # 添加数据目录路径
                    })
                    
                    # 显示结果
                    print(f"\n=== 三人囚徒困境第 {result['run_number']} 局 ===")
                    print(f"结果: {winner_text}, 步数: {result['steps']}")
                    if "data_dir" in result and result["data_dir"]:
                        print(f"数据保存位置: {result['data_dir']}")
                    
                    # 显示当前进度
                    print(f"进度: {completed_games}/{total_games} | 上校博弈: {stats['colonel_blotto']['total_runs']}/{args.num_blotto_runs} | 三人IPD: {stats['three_player_ipd']['total_runs']}/{args.num_ipd_runs}")
            
        except Exception as e:
            # 检查进程是否仍在运行
            if not blotto_process.is_alive():
                blotto_done = True
                print("上校博弈进程已结束")
            if not ipd_process.is_alive():
                ipd_done = True
                print("三人囚徒困境进程已结束")
    
    # 等待进程结束
    blotto_process.join()
    ipd_process.join()
    
    # 计算最终统计
    stats["end_time"] = datetime.now().isoformat()
    
    if stats["colonel_blotto"]["total_runs"] > 0:
        stats["colonel_blotto"]["agent0_win_rate"] = stats["colonel_blotto"]["agent0_wins"] / stats["colonel_blotto"]["total_runs"]
    else:
        stats["colonel_blotto"]["agent0_win_rate"] = 0
    
    if stats["three_player_ipd"]["total_runs"] > 0:
        stats["three_player_ipd"]["agent0_win_rate"] = stats["three_player_ipd"]["agent0_wins"] / stats["three_player_ipd"]["total_runs"]
    else:
        stats["three_player_ipd"]["agent0_win_rate"] = 0
    
    # 保存统计结果
    stats_file = Path("mixed_games_stats_final.json")
    with open(stats_file, 'w', encoding='utf-8') as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)
    
    # 显示最终统计
    print("\n" + "="*50)
    print("混合游戏并行运行完成")
    print("="*50)
    print(f"上校博弈:")
    print(f"  总计划局数: {args.num_blotto_runs}")
    print(f"  成功完成局数: {stats['colonel_blotto']['total_runs']}")
    print(f"  失败局数: {stats['colonel_blotto']['errors']}")
    print(f"  Agent0 胜率: {stats['colonel_blotto']['agent0_win_rate']:.2%}")
    print(f"三人囚徒困境:")
    print(f"  总计划局数: {args.num_ipd_runs}")
    print(f"  成功完成局数: {stats['three_player_ipd']['total_runs']}")
    print(f"  失败局数: {stats['three_player_ipd']['errors']}")
    print(f"  Agent0 胜率: {stats['three_player_ipd']['agent0_win_rate']:.2%}")
    print("="*50)
    
    # 保存结果到CSV文件
    blotto_csv = Path("mixed_games_blotto_results.csv")
    with blotto_csv.open("w", encoding="utf-8") as f:
        f.write("game_index,agent0_is_winner,steps\n")
        for rec in stats["colonel_blotto"]["results"]:
            f.write(f"{rec['run_number']},{rec['agent0_is_winner']},{rec['steps']}\n")
    
    ipd_csv = Path("mixed_games_ipd_results.csv")
    with ipd_csv.open("w", encoding="utf-8") as f:
        f.write("game_index,agent0_is_winner,steps,data_dir\n")
        for rec in stats["three_player_ipd"]["results"]:
            f.write(f"{rec['run_number']},{rec['agent0_is_winner']},{rec['steps']},{rec.get('data_dir', '')}\n")
    
    print(f"\n结果明细已保存:")
    print(f"  上校博弈: {blotto_csv}")
    print(f"  三人囚徒困境: {ipd_csv}")
    print(f"统计结果已保存到: {stats_file}")
    
    # 打印令牌使用统计
    token_pool.print_usage_stats()
    
    return stats

def main():
    parser = argparse.ArgumentParser(description="混合游戏并行运行")
    parser.add_argument("--num_blotto_runs", type=int, default=5, help="上校博弈运行次数 (默认: 5)")
    parser.add_argument("--num_blotto_processes", type=int, default=5, help="上校博弈并行进程数 (默认: 5)")
    parser.add_argument("--num_ipd_runs", type=int, default=3, help="三人囚徒困境运行次数 (默认: 3)")
    parser.add_argument("--num_ipd_processes", type=int, default=3, help="三人囚徒困境并行进程数 (默认: 3)")
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
        stats = run_mixed_games(args)
        if stats:
            print(f"\n混合游戏并行运行完成!")
        else:
            print(f"\n混合游戏并行运行失败")
    except KeyboardInterrupt:
        print(f"\n用户中断")
    except Exception as e:
        print(f"\n系统错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()