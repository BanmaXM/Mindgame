#!/usr/bin/env python3
"""
上校博弈并行批量运行脚本
同时运行多个上校博弈游戏，统计Agent0的胜率，并保存详细日志
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

def save_game_data(data_dir, game_log, agent_info, run_number, result=None, agent_positions=None):
    """保存游戏数据为统一格式"""
    # 创建时间戳目录
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    run_dir = Path(data_dir) / f"batch_run_{run_number:03d}" / timestamp
    run_dir.mkdir(parents=True, exist_ok=True)
    
    # 转换游戏日志为统一格式
    unified_data = {
        "game_name": "colonel_blotto",
        "timestamp": agent_info["timestamp"],
        "run_number": run_number,
        "steps": []
    }
    
    # 添加player与agent的映射关系
    if agent_positions is not None:
        # agent_positions: 0表示agent0是player0，agent1是player1
        #                 1表示agent0是player1，agent1是player0
        if agent_positions == 0:
            player_agent_mapping = {
                "0": "agent_0",  # player 0 对应 agent_0
                "1": "agent_1"   # player 1 对应 agent_1
            }
        else:
            player_agent_mapping = {
                "0": "agent_1",  # player 0 对应 agent_1
                "1": "agent_0"   # player 1 对应 agent_0
            }
        
        unified_data["player_agent_mapping"] = player_agent_mapping
        unified_data["agent_positions"] = agent_positions
    
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
                # 从agent_info中获取system_prompt，如果不存在则从config中获取
                system_prompt = model_info.get("system_prompt", "")
                if not system_prompt and "config" in model_info:
                    system_prompt = model_info["config"].get("system_prompt", "")
                
                # 如果仍然没有system_prompt，则从prompt文件中加载
                if not system_prompt and "prompt_name" in model_info:
                    try:
                        prompt_path = os.path.join(
                            os.path.dirname(os.path.abspath(__file__)), 
                            "prompt_pool", 
                            model_info.get("game_type", "colonel_blotto"), 
                            f"pool_{'A' if agent_key == 'agent_0' else 'B'}", 
                            f"{model_info['prompt_name']}.txt"
                        )
                        if os.path.exists(prompt_path):
                            with open(prompt_path, 'r', encoding='utf-8') as f:
                                system_prompt = f.read()
                    except Exception:
                        pass  # 如果加载失败，保持为空字符串
                
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
                        "response": entry["content"]
                    }
                }
                unified_data["steps"].append(step_data)
    
    # 添加agents信息
    unified_data["agents"] = {
        "0": {
            "agent_type": agent_info.get("agent_0", {}).get("agent_type", "Unknown"),
            "model_name": agent_info.get("agent_0", {}).get("model_name", None)
        },
        "1": {
            "agent_type": agent_info.get("agent_1", {}).get("agent_type", "Unknown"),
            "model_name": agent_info.get("agent_1", {}).get("model_name", None)
        }
    }
    
    # 添加最终结果
    if result and "rewards" in result:
        rewards = result["rewards"]
        steps = result.get("steps", 0)
        
        # 确定胜者
        winner = None
        if rewards:
            max_reward = max(rewards.values())
            winners = [pid for pid, r in rewards.items() if r == max_reward]
            winner = winners[0] if len(winners) == 1 else None  # 如果平局，winner为None
        
        # 生成游戏结果描述
        if winner is not None:
            reason = f"Player {winner} wins with {rewards[winner]} points!"
        else:
            reason = f"Game ends in a tie with {rewards['0']}-{rewards['1']} points!"
        
        # 添加final_results部分
        unified_data["final_results"] = {
            "rewards": rewards,
            "game_info": {
                "0": {
                    "role": "Player 0",
                    "invalid_move": False,
                    "turn_count": steps // 2,  # 每个玩家的回合数
                    "reason": reason
                },
                "1": {
                    "role": "Player 1",
                    "invalid_move": False,
                    "turn_count": steps // 2,  # 每个玩家的回合数
                    "reason": reason
                }
            },
            "timestamp": datetime.now().isoformat(),
            "status": "completed",
            "total_steps": steps
        }
    
    # 保存统一格式的游戏数据
    data_file = run_dir / f"{timestamp}_colonel_blotto.json"
    with open(data_file, 'w', encoding='utf-8') as f:
        json.dump(unified_data, f, ensure_ascii=False, indent=2)
    
    # 同时保存agent信息（保持原格式）
    info_file = run_dir / "agent_info.json"
    with open(info_file, 'w', encoding='utf-8') as f:
        json.dump(agent_info, f, ensure_ascii=False, indent=2)
    
    return run_dir

def run_single_colonel_blotto(args, run_number, verbose=True):
    """运行单次上校博弈游戏"""
    if verbose:
        print(f"\n开始第 {run_number} 次游戏...")
    
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
            prompt_name=args.prompt_0,
            token_pool_type="colonel_blotto"  # 使用上校博弈令牌池
        )
        
        agent_1 = Agent1(
            game_type="colonel_blotto", 
            model_name=args.model_1,
            prompt_name=args.prompt_1,
            token_pool_type="colonel_blotto"  # 使用上校博弈令牌池
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
            "game": "colonel_blotto",
            "timestamp": datetime.now().isoformat(),
            "run_id": str(uuid.uuid4()),
            "run_number": run_number
        }
        
        # 保存游戏数据
        data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), game_config["data_dir"], "batch_runs")
        run_dir = save_game_data(data_dir, game_log, agent_info, run_number, result, agent_positions)
        
        # 显示简要结果
        if verbose:
            winner_text = f"Agent{winner}" if winner is not None else "平局"
            print(f"第 {run_number} 次游戏完成 - 胜者: {winner_text}, 步数: {result['steps']}")
        
        # 确定实际agent0的胜者状态
        # 如果agent0是player0且player0获胜，或者agent0是player1且player1获胜，则agent0获胜
        agent0_is_winner = False
        if agent_positions == 0:  # agent0是player0
            agent0_is_winner = (winner == 0)
        else:  # agent0是player1
            agent0_is_winner = (winner == 1)
        
        return {
            "result": result,
            "winner": winner,
            "agent0_is_winner": agent0_is_winner,
            "agent_positions": agent_positions,  # 记录agent位置分配
            "agent_info": agent_info,
            "run_dir": run_dir
        }
        
    except Exception as e:
        if verbose:
            print(f"第 {run_number} 次游戏失败: {e}")
        return None

def run_single_game_wrapper(args, run_number, verbose=True):
    """包装单次游戏运行，用于多进程"""
    result = run_single_colonel_blotto(args, run_number, verbose=verbose)
    return (run_number, result)

def run_parallel_colonel_blotto(args):
    """并行运行上校博弈游戏"""
    print(f"开始批量运行 {args.num_runs} 局上校博弈对战...")
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
    game_config = config["games"]["colonel_blotto"]
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
                    winner_text = "Agent1获胜"
                
                # 获取奖励
                rewards = game_result["result"]["rewards"]
                r0 = rewards.get("0", 0)
                r1 = rewards.get("1", 0)
                
                # 保存单次结果
                stats["results"].append({
                    "run_number": run_number,
                    "agent0_is_winner": game_result["agent0_is_winner"],
                    "rewards": rewards,
                    "steps": game_result["result"]["steps"],
                    "run_dir": str(game_result["run_dir"])
                })
                
                # 显示结果
                print(f"解析结果 -> 玩家0: {r0}, 玩家1: {r1}, 结果: {winner_text}")
                print(f"   └── 原始日志: {game_result['run_dir']}")
                
                # 显示当前统计 - 只在关键节点显示
                if stats["total_runs"] % 5 == 0 or stats["total_runs"] == args.num_runs:
                    if stats["total_runs"] > 0:
                        agent0_win_rate = stats["agent0_wins"] / stats["total_runs"] * 100
                        print(f"  进度: {stats['total_runs']}/{args.num_runs} | Agent0胜率: {agent0_win_rate:.1f}% | 错误: {stats['errors']}")
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
    else:
        stats["agent0_win_rate"] = 0
    
    # 保存最终统计结果
    stats_file = batch_dir / "batch_stats_final.json"
    with open(stats_file, 'w', encoding='utf-8') as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)
    
    # 显示最终统计
    print("\n===== 最终统计 =====")
    print(f"总计划局数: {args.num_runs}")
    print(f"成功完成局数: {stats['total_runs']} (失败 {stats['errors']})")
    print(f"Agent0 胜: {stats['agent0_wins']}")
    print(f"Agent0 胜率: {stats['agent0_win_rate']:.2%}")
    print(f"平均每次运行时间: {elapsed_time/stats['total_runs']:.2f} 秒" if stats['total_runs'] > 0 else "平均每次运行时间: 0.00 秒")
    
    # 保存结果到CSV文件
    out_csv = Path("player0_batch_results_blotto_parallel.csv")
    with out_csv.open("w", encoding="utf-8") as f:
        f.write("game_index,reward_player0,reward_player1,agent0_is_winner\n")
        for rec in stats["results"]:
            rewards = rec["rewards"]
            f.write(f"{rec['run_number']},{rewards.get('0', 0)},{rewards.get('1', 0)},{rec['agent0_is_winner']}\n")
    print(f"\n结果明细已保存: {out_csv}")
    print(f"统计结果已保存到: {stats_file}")
    
    return stats

def main():
    parser = argparse.ArgumentParser(description="上校博弈并行批量运行")
    parser.add_argument("--num_runs", type=int, default=10, help="运行次数 (默认: 10)")
    parser.add_argument("--num_processes", type=int, default=3, help="并行进程数 (默认: 3)")
    parser.add_argument("--model_0", type=str, help="Agent0使用的模型名称")
    parser.add_argument("--prompt_0", type=str, help="Agent0使用的提示名称")
    parser.add_argument("--model_1", type=str, help="Agent1使用的模型名称")
    parser.add_argument("--prompt_1", type=str, help="Agent1使用的提示名称")
    parser.add_argument("--verbose", action="store_true", help="显示运行信息")
    parser.add_argument("--disable_verbose", action="store_true", help="禁用agent详细输出以提高性能")
    parser.add_argument("--max_retries", type=int, default=3, help="API调用最大重试次数 (默认: 3)")
    parser.add_argument("--retry_delay", type=int, default=5, help="API调用重试延迟秒数 (默认: 5)")
    parser.add_argument("--stream", action="store_true", help="启用流式输出模式，可能提高响应速度")
    parser.add_argument("--no_connection_pool", action="store_true", help="禁用连接池，每个agent使用独立的连接")
    parser.add_argument("--no_token_pool", action="store_true", help="禁用令牌池，使用原始配置的令牌")
    
    args = parser.parse_args()
    
    try:
        stats = run_parallel_colonel_blotto(args)
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