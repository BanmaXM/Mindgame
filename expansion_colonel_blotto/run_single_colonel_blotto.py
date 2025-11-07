#!/usr/bin/env python3
"""
Run a single Colonel Blotto game locally using expansion agents and OpenRouter.

Requirements:
- Uses Agent0 and Agent1 from expansion_colonel_blotto/agents
- Each agent loads its own prompt file and YAML config
- GameManager from src manages the environment and game loop

Usage:
  python expansion_colonel_blotto/run_single_colonel_blotto.py
"""

import os
import sys
import json
import re
import argparse
from datetime import datetime
from pathlib import Path
from typing import Any, List

# Ensure project root on sys.path
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(ROOT_DIR)
# Prefer expansion_src over src when resolving top-level modules like 'agent'
EXP_SRC_DIR = os.path.join(ROOT_DIR, "expansion_src")
if EXP_SRC_DIR not in sys.path:
    sys.path.insert(0, EXP_SRC_DIR)
# Ensure src package modules with absolute imports (e.g., 'agent') are resolvable
SRC_DIR = os.path.join(ROOT_DIR, "src")
if SRC_DIR not in sys.path:
    sys.path.append(SRC_DIR)

# Import expansion agents
from expansion_colonel_blotto.agents.agent0 import Agent0
from expansion_colonel_blotto.agents.agent1 import Agent1

# Import GameManager (prefer expansion_src)
try:
    from expansion_src.game_manager import GameManager
except Exception:
    # fallback to src if expansion_src not available
    from src.game_manager import GameManager


def save_game_data(run_dir: Path, game_log: list, agent_info: dict, result: dict) -> Path:
    """Save logs into a per-run timestamp subfolder to avoid clutter.

    Folder layout:
      <run_dir>/<YYYY-MM-DD_HH-MM-SS>/
        - colonel_blotto.json
        - summary.csv
        - agent_info.json
    """
    run_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    run_subdir = run_dir / timestamp
    run_subdir.mkdir(parents=True, exist_ok=True)

    unified_data = {
        "game_name": "colonel_blotto",
        "timestamp": agent_info.get("timestamp", datetime.now().isoformat()),
        "steps": [],
    }

    current_observation = {}
    current_model_input = {}

    for entry in game_log:
        if entry["type"] == "observation":
            pid = entry["player_id"]
            current_observation[pid] = {
                "timestamp": entry["timestamp"],
                "observation": entry["content"],
            }
            agent_key = f"agent_{pid}"
            model_info = agent_info.get(agent_key, {})
            system_prompt = model_info.get("system_prompt", "")
            current_model_input[pid] = {
                "system_prompt": system_prompt,
                "user_message": entry["content"],
                "model": model_info.get("model_name", ""),
                "was_summarised": False,
            }
        elif entry["type"] == "action":
            pid = entry["player_id"]
            if pid in current_observation:
                unified_data["steps"].append({
                    "step_num": len(unified_data["steps"]),
                    "player_id": pid,
                    "timestamp": current_observation[pid]["timestamp"],
                    "observation": current_observation[pid]["observation"],
                    "action": entry["content"],
                    "model_input": current_model_input.get(pid, {}),
                    "model_output": {
                        "response": entry["content"],
                        "raw_content": entry.get("raw_content"),
                        "reasoning": entry.get("reasoning"),
                        "meta": entry.get("meta", {}),
                    },
                })

    unified_data["final_results"] = result

    # Detailed JSON
    data_file = run_subdir / "colonel_blotto.json"
    with data_file.open("w", encoding="utf-8") as f:
        json.dump(unified_data, f, ensure_ascii=False, indent=2, default=json_default)

    # Agent info JSON
    info_file = run_subdir / "agent_info.json"
    with info_file.open("w", encoding="utf-8") as f:
        json.dump(agent_info, f, ensure_ascii=False, indent=2, default=json_default)

    # Simple CSV summary
    simple_csv = run_subdir / "summary.csv"
    try:
        rewards = result.get("rewards", {})
        steps = result.get("steps", 0)
        winner = None
        if isinstance(rewards, dict) and rewards:
            max_r = max(rewards.values())
            winners = [pid for pid, r in rewards.items() if r == max_r]
            winner = winners[0] if len(winners) == 1 else None
        r0 = rewards.get("0", rewards.get(0, 0))
        r1 = rewards.get("1", rewards.get(1, 0))
        with simple_csv.open("w", encoding="utf-8") as f:
            f.write("steps,reward_player0,reward_player1,winner\n")
            f.write(f"{steps},{r0},{r1},{winner}\n")
    except Exception:
        pass

    return run_subdir


def main():
    print("🚀 启动单局 Colonel Blotto 对战")
    print("=" * 50)

    # CLI arguments for reasoning control and rounds
    parser = argparse.ArgumentParser(description="Run a single Colonel Blotto game with optional reasoning.")
    parser.add_argument("--reasoning", choices=["off", "on", "visible"], default="off",
                        help="是否启用 reasoning: off=关闭, on=启用隐藏推理, visible=输出可见推理(调试用)")
    parser.add_argument("--reasoning-effort", choices=["low", "medium", "high"], default=None,
                        help="推理强度提示，可选，取决于模型/路由支持")
    parser.add_argument("--rounds", type=int, default=3, help="对局回合数，默认 3 以便快速验证")
    args = parser.parse_args()

    # Initialize agents with default YAML and prompts inside expansion_colonel_blotto
    agent0 = Agent0(game_type="colonel_blotto", reasoning=args.reasoning, reasoning_effort=args.reasoning_effort)
    agent1 = Agent1(game_type="colonel_blotto", reasoning=args.reasoning, reasoning_effort=args.reasoning_effort)

    # Show model info
    print("🔧 Agent0 配置信息:")
    print(f"   模型: {agent0.get_model_info().get('model_name')}")
    print(f"   Prompt: {agent0.get_model_info().get('prompt_name')}")
    print("🔧 Agent1 配置信息:")
    print(f"   模型: {agent1.get_model_info().get('model_name')}")
    print(f"   Prompt: {agent1.get_model_info().get('prompt_name')}")

    # Set up game
    print("🎯 初始化上校博弈环境 (使用 expansion_src.GameManager 优先)...")
    manager = GameManager()
    # 可配置回合数（默认 3 回合以便快速验证）
    manager.setup_game("colonel_blotto", env_config={"num_rounds": int(args.rounds)})

    # Add agents as player0 and player1
    manager.add_agent(agent0)  # Player 0
    manager.add_agent(agent1)  # Player 1

    # Optional: callbacks to log observations and actions
    game_log = []

    def stringify_observation(obs: Any) -> str:
        """将 observation 清洗为可读文本，去除元组/类型标记。

        支持两类输入：
        1) 结构化列表/元组：例如 [(-1, "text", ObservationType.X), ...]
           -> 提取每个项的第2个字符串元素并按行拼接。
        2) 字符串化的repr：例如 "[(... \"text\" ...), (... \"more\" ...)]"
           -> 正则提取其中的被引号包裹的文本，按行拼接，并反转义换行与引号。
        """
        try:
            # 情况1：结构化列表/元组
            if isinstance(obs, (list, tuple)):
                parts: List[str] = []
                for item in obs:
                    if isinstance(item, (list, tuple)) and len(item) >= 2 and isinstance(item[1], str):
                        parts.append(item[1])
                    elif isinstance(item, str):
                        parts.append(item)
                    else:
                        continue
                if parts:
                    return "\n".join(parts)

            # 情况2：字符串repr，需要清洗（解析形如 (pid, "text", ObservationType.X) 的第二元素）
            if isinstance(obs, str):
                s = obs
                if ("ObservationType" in s) or (s.startswith("[") and ("(" in s)):
                    dq_pat = re.compile(r"\(\s*-?\d+\s*,\s*\"((?:\\.|[^\"\\])*)\"\s*,")
                    sq_pat = re.compile(r"\(\s*-?\d+\s*,\s*'((?:\\.|[^'\\])*)'\s*,")
                    texts = dq_pat.findall(s) + sq_pat.findall(s)
                    if texts:
                        def _unescape(t: str) -> str:
                            return (
                                t.replace("\\n", "\n")
                                 .replace("\\t", "\t")
                                 .replace("\\r", "\r")
                                 .replace("\\\"", '"')
                                 .replace("\\'", "'")
                            )
                        cleaned = [ _unescape(t) for t in texts if t.strip() ]
                        return "\n".join(cleaned)
                return s
        except Exception:
            return str(obs)
        return str(obs)

    def observation_cb(player_id, obs):
        # 直接使用传给代理的累计观察字符串，保证与模型输入一致
        obs_text = stringify_observation(obs)
        game_log.append({
            "timestamp": datetime.now().isoformat(),
            "type": "observation",
            "player_id": player_id,
            "content": obs_text,
        })

    def action_cb(player_id, action):
        # 尝试从对应代理抓取原始输出与reasoning
        raw_content = None
        reasoning = None
        meta = {}
        try:
            agent = agent0 if player_id == 0 else agent1
            inst = getattr(agent, "agent_instance", None)
            if inst and hasattr(inst, "get_last_output"):
                last = inst.get_last_output()
                raw_content = last.get("raw_content")
                reasoning = last.get("reasoning")
                meta = last.get("meta", {})
        except Exception:
            pass

        game_log.append({
            "timestamp": datetime.now().isoformat(),
            "type": "action",
            "player_id": player_id,
            "content": action,
            "raw_content": raw_content,
            "reasoning": reasoning,
            "meta": meta,
        })

    step_idx = {"n": 0}
    def step_complete_cb(done, info):
        # Print simple per-step info to terminal for visibility
        step_idx["n"] += 1
        try:
            print(f"📍 步骤 {step_idx['n']} 完成 | done={done}")
        except Exception:
            pass

    callbacks = {
        "on_observation": observation_cb,
        "on_action": action_cb,
        "on_step_complete": step_complete_cb,
    }

    # Start and play one full game
    print("🎮 开始游戏...")
    manager.start_game()
    result = manager.play_game(callbacks=callbacks)

    print("\n===== 游戏结果 =====")
    print(f"  状态: {result.get('status')}")
    print(f"  总步数: {result.get('steps')}")
    rewards = result.get('rewards')
    if rewards is not None:
        print(f"  奖励: {rewards}")
        try:
            # Determine winner from rewards (dict or list)
            if isinstance(rewards, dict):
                max_r = max(rewards.values())
                winners = [pid for pid, r in rewards.items() if r == max_r]
            else:
                max_r = max(rewards)
                winners = [i for i, r in enumerate(rewards) if r == max_r]
            print(f"  胜者: {winners}")
        except Exception:
            pass

    print("✅ 单局对战完成")
    print(f"   reasoning: {args.reasoning}, effort: {args.reasoning_effort}")

    # Save logs to expansion_colonel_blotto/data/single_runs/YYYY-MM-DD
    data_root = Path(os.path.dirname(os.path.abspath(__file__))) / "data" / "single_runs" / datetime.now().strftime("%Y-%m-%d")
    agent_info = {
        "agent_0": agent0.get_model_info(),
        "agent_1": agent1.get_model_info(),
        "game": "colonel_blotto",
        "timestamp": datetime.now().isoformat(),
    }
    run_dir = save_game_data(data_root, game_log, agent_info, result)
    print(f"🧾 日志已保存: {run_dir}")


# Robust JSON default to handle Enums, numpy types, sets, and unknowns
def json_default(obj):
    try:
        import numpy as np
    except Exception:
        np = None
    # Handle enums
    try:
        import enum
        if isinstance(obj, enum.Enum):
            return obj.name
    except Exception:
        pass
    # numpy scalars and arrays
    if np is not None:
        if isinstance(obj, (np.integer,)):
            return int(obj)
        if isinstance(obj, (np.floating,)):
            return float(obj)
        if isinstance(obj, (np.ndarray,)):
            return obj.tolist()
    # sets
    if isinstance(obj, (set, frozenset)):
        return list(obj)
    # Fallback to string
    return str(obj)


if __name__ == "__main__":
    main()

def _dedupe_lines(text: str) -> str:
    lines = text.splitlines()
    seen = set()
    result: List[str] = []
    prev_blank = False
    for ln in lines:
        key = ln.strip()
        is_blank = (key == "")
        if not is_blank:
            if key not in seen:
                seen.add(key)
                result.append(ln)
                prev_blank = False
            else:
                continue
        else:
            if not prev_blank:
                result.append("")
                prev_blank = True
    while result and result[0].strip() == "":
        result.pop(0)
    while result and result[-1].strip() == "":
        result.pop()
    return "\n".join(result)