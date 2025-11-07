#!/usr/bin/env python3
"""
上校博弈批量运行脚本
连续运行100次上校博弈游戏，统计Agent0的胜率，并保存详细日志
"""

import os
import sys
import json
import uuid
import yaml
import argparse
from datetime import datetime
from pathlib import Path
import time

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

def save_game_data(data_dir, game_log, agent_info, run_number):
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
        print_colored(f"\n🚀 第 {run_number} 次上校博弈", "cyan")
        print_colored("=" * 50, "cyan")
    
    # 加载配置
    config = load_config()
    game_config = config["games"]["colonel_blotto"]
    
    try:
        # 初始化agents
        if verbose:
            print_colored("🔄 初始化我们的Agent (Agent0)...", "yellow")
        agent_0 = Agent0(game_type="colonel_blotto", 
                         model_name=args.model_0, 
                         prompt_name=args.prompt_0)
        if verbose:
            print_colored("✅ 我们的Agent初始化成功!", "green")
            print_colored(f"   模型: {agent_0.get_model_info()['model_name']}", "blue")
            print_colored(f"   提示: {agent_0.get_model_info()['prompt_name']}", "blue")
        
        if verbose:
            print_colored("🔄 初始化对手Agent (Agent1)...", "yellow")
        agent_1 = Agent1(game_type="colonel_blotto", 
                         model_name=args.model_1, 
                         prompt_name=args.prompt_1)
        if verbose:
            print_colored("✅ 对手Agent初始化成功!", "green")
            print_colored(f"   模型: {agent_1.get_model_info()['model_name']}", "blue")
            print_colored(f"   提示: {agent_1.get_model_info()['prompt_name']}", "blue")
        
        # 设置游戏管理器
        if verbose:
            print_colored("🎯 初始化上校博弈环境...", "yellow")
        manager = GameManager()
        manager.setup_game("colonel_blotto")
        
        # 添加agents
        manager.add_agent(agent_0)  # Player 0
        manager.add_agent(agent_1)  # Player 1
        
        # 收集游戏日志
        game_log = []
        
        # 设置回调函数
        def observation_callback(player_id, obs):
            player_name = "Agent0" if player_id == 0 else "Agent1"
            if verbose:
                print_colored(f"\n===== 观察 ({player_name}) =====", "blue")
                print(obs[:500] + "..." if len(obs) > 500 else obs)
            
            # 记录观察
            game_log.append({
                "timestamp": datetime.now().isoformat(),
                "type": "observation",
                "player_id": player_id,
                "player_name": player_name,
                "content": obs
            })
            
        def action_callback(player_id, action):
            player_name = "Agent0" if player_id == 0 else "Agent1"
            action_preview = action.replace('\n', ' ').strip()
            if not action_preview:
                action_preview = "[EMPTY ACTION]"
            if verbose:
                print_colored(f"执行动作 ({player_name}): {action_preview}", "green")
            
            # 记录动作
            game_log.append({
                "timestamp": datetime.now().isoformat(),
                "type": "action",
                "player_id": player_id,
                "player_name": player_name,
                "content": action
            })
            
        def step_complete_callback(done, info):
            if done and verbose:
                print_colored("\n游戏回合结束！", "yellow")
            
            # 记录回合结束
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
        
        if verbose:
            print_colored("\n...正在启动游戏...", "yellow")
        manager.start_game()
        result = manager.play_game(callbacks=callbacks)
        
        # 显示游戏结果
        if verbose:
            print_colored("\n===== 游戏结果 =====", "magenta")
            print(f"  总步数: {result['steps']}")
        
        winner = None
        if "rewards" in result and result["rewards"]:
            if verbose:
                reward_details = [f"玩家{pid} ({'Agent0' if pid == 0 else 'Agent1'}): {reward}" for pid, reward in result["rewards"].items()]
                print(f"  奖励: {', '.join(reward_details)}")
            
            max_reward = max(result["rewards"].values())
            winners = [pid for pid, r in result["rewards"].items() if r == max_reward]
            winner = winners[0] if len(winners) == 1 else None  # 如果平局，winner为None
            
            if verbose:
                winner_names = [f"玩家{pid} ({'Agent0' if pid == 0 else 'Agent1'})" for pid in winners]
                print_colored(f"  胜者: {', '.join(winner_names)}", "yellow")
        
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
        run_dir = save_game_data(data_dir, game_log, agent_info, run_number)
        
        if verbose:
            print_colored(f"\n📁 游戏数据已保存: {run_dir}", "blue")
        
        return {
            "result": result,
            "winner": winner,
            "agent_info": agent_info,
            "run_dir": run_dir
        }
        
    except Exception as e:
        if verbose:
            print_colored(f"❌ 对战过程中出现错误: {e}", "red")
            import traceback
            traceback.print_exc()
        return None

def run_batch_colonel_blotto(args):
    """批量运行上校博弈游戏"""
    print_colored("🚀 上校博弈批量运行系统", "cyan")
    print_colored("=" * 50, "cyan")
    print_colored(f"总运行次数: {args.num_runs}", "blue")
    
    # 统计信息
    stats = {
        "total_runs": 0,
        "agent0_wins": 0,
        "agent1_wins": 0,
        "draws": 0,
        "errors": 0,
        "start_time": datetime.now().isoformat(),
        "agent0_models": {},
        "agent1_models": {},
        "results": []
    }
    
    # 创建批量运行目录
    config = load_config()
    game_config = config["games"]["colonel_blotto"]
    batch_dir = Path(os.path.join(os.path.dirname(os.path.abspath(__file__)), game_config["data_dir"], "batch_runs"))
    batch_dir.mkdir(parents=True, exist_ok=True)
    
    # 运行游戏
    for run_number in range(1, args.num_runs + 1):
        print_colored(f"\n🔄 开始第 {run_number}/{args.num_runs} 次运行...", "yellow")
        
        start_time = time.time()
        game_result = run_single_colonel_blotto(args, run_number, verbose=args.verbose)
        elapsed_time = time.time() - start_time
        
        if game_result:
            stats["total_runs"] += 1
            
            # 记录胜者
            winner = game_result["winner"]
            if winner == 0:
                stats["agent0_wins"] += 1
            elif winner == 1:
                stats["agent1_wins"] += 1
            else:
                stats["draws"] += 1
            
            # 记录模型使用情况
            agent0_model = game_result["agent_info"]["agent_0"]["model_name"]
            agent1_model = game_result["agent_info"]["agent_1"]["model_name"]
            
            if agent0_model not in stats["agent0_models"]:
                stats["agent0_models"][agent0_model] = 0
            stats["agent0_models"][agent0_model] += 1
            
            if agent1_model not in stats["agent1_models"]:
                stats["agent1_models"][agent1_model] = 0
            stats["agent1_models"][agent1_model] += 1
            
            # 保存单次结果
            stats["results"].append({
                "run_number": run_number,
                "winner": winner,
                "agent0_model": agent0_model,
                "agent1_model": agent1_model,
                "agent0_prompt": game_result["agent_info"]["agent_0"]["prompt_name"],
                "agent1_prompt": game_result["agent_info"]["agent_1"]["prompt_name"],
                "rewards": game_result["result"]["rewards"],
                "steps": game_result["result"]["steps"],
                "elapsed_time": elapsed_time,
                "run_dir": str(game_result["run_dir"])
            })
            
            # 显示当前统计
            agent0_win_rate = stats["agent0_wins"] / stats["total_runs"] * 100
            print_colored(f"  当前Agent0胜率: {agent0_win_rate:.1f}% ({stats['agent0_wins']}/{stats['total_runs']})", "blue")
        else:
            stats["errors"] += 1
            print_colored(f"  第 {run_number} 次运行出错", "red")
        
        # 保存中间统计结果
        if run_number % 10 == 0 or run_number == args.num_runs:
            stats["end_time"] = datetime.now().isoformat()
            stats_file = batch_dir / "batch_stats.json"
            with open(stats_file, 'w', encoding='utf-8') as f:
                json.dump(stats, f, ensure_ascii=False, indent=2)
            print_colored(f"  已保存中间统计结果到: {stats_file}", "green")
        
        # 如果不是最后一次运行，添加延迟
        if run_number < args.num_runs:
            delay = args.delay if args.delay > 0 else 1
            print_colored(f"  等待 {delay} 秒后继续...", "yellow")
            time.sleep(delay)
    
    # 计算最终统计
    stats["end_time"] = datetime.now().isoformat()
    if stats["total_runs"] > 0:
        stats["agent0_win_rate"] = stats["agent0_wins"] / stats["total_runs"] * 100
        stats["agent1_win_rate"] = stats["agent1_wins"] / stats["total_runs"] * 100
        stats["draw_rate"] = stats["draws"] / stats["total_runs"] * 100
    else:
        stats["agent0_win_rate"] = 0
        stats["agent1_win_rate"] = 0
        stats["draw_rate"] = 0
    
    # 保存最终统计结果
    stats_file = batch_dir / "batch_stats_final.json"
    with open(stats_file, 'w', encoding='utf-8') as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)
    
    # 显示最终统计
    print_colored("\n" + "=" * 50, "cyan")
    print_colored("🎯 批量运行完成!", "cyan")
    print_colored(f"总运行次数: {stats['total_runs']}", "blue")
    print_colored(f"Agent0胜率: {stats['agent0_win_rate']:.1f}% ({stats['agent0_wins']}/{stats['total_runs']})", "green")
    print_colored(f"Agent1胜率: {stats['agent1_win_rate']:.1f}% ({stats['agent1_wins']}/{stats['total_runs']})", "yellow")
    print_colored(f"平局率: {stats['draw_rate']:.1f}% ({stats['draws']}/{stats['total_runs']})", "purple")
    print_colored(f"错误次数: {stats['errors']}", "red")
    print_colored(f"统计结果已保存到: {stats_file}", "blue")
    
    return stats

def main():
    parser = argparse.ArgumentParser(description="上校博弈批量运行")
    parser.add_argument("--num_runs", type=int, default=10, help="运行次数 (默认: 10)")
    parser.add_argument("--model_0", type=str, help="Agent0使用的模型名称")
    parser.add_argument("--prompt_0", type=str, help="Agent0使用的提示名称")
    parser.add_argument("--model_1", type=str, help="Agent1使用的模型名称")
    parser.add_argument("--prompt_1", type=str, help="Agent1使用的提示名称")
    parser.add_argument("--delay", type=float, default=1.0, help="每次运行之间的延迟秒数 (默认: 1.0)")
    parser.add_argument("--verbose", action="store_true", help="显示详细运行信息")
    
    args = parser.parse_args()
    
    try:
        stats = run_batch_colonel_blotto(args)
        if stats:
            print_colored(f"\n✅ 批量运行完成!", "green")
        else:
            print_colored(f"\n❌ 批量运行失败", "red")
    except KeyboardInterrupt:
        print_colored(f"\n⚠️ 用户中断", "yellow")
    except Exception as e:
        print_colored(f"\n❌ 系统错误: {e}", "red")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()