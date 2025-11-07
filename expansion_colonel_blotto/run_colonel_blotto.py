#!/usr/bin/env python3
"""
Run a single Colonel Blotto game with Agent0 (player 0) and Agent1 (player 1),
using expansion_src.GameManager for environment control and unified logging.
"""
import os
import sys
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List
from enum import Enum

try:
    import numpy as np  # Optional, used in json safety conversion
except Exception:
    np = None

# Ensure project root on sys.path
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

# Prefer expansion_src over src when resolving top-level modules like 'agent'
EXP_SRC_DIR = os.path.join(ROOT_DIR, "expansion_src")
if EXP_SRC_DIR not in sys.path:
    sys.path.insert(0, EXP_SRC_DIR)

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
    from src.game_manager import GameManager


def _stringify_observation(obs: Any) -> str:
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

    def json_default(obj):
        """Best-effort JSON serializer for Enums, numpy types, sets, and others."""
        try:
            if isinstance(obj, Enum):
                return getattr(obj, "name", None) or getattr(obj, "value", None) or str(obj)
        except Exception:
            pass
        if np is not None:
            try:
                if isinstance(obj, (np.integer,)):
                    return int(obj)
                if isinstance(obj, (np.floating,)):
                    return float(obj)
                if isinstance(obj, (np.bool_,)):
                    return bool(obj)
                if isinstance(obj, np.ndarray):
                    return obj.tolist()
            except Exception:
                pass
        if isinstance(obj, set):
            return list(obj)
        try:
            return str(obj)
        except Exception:
            return "<unserializable>"

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


def main() -> Dict[str, Any]:
    print("🚀 启动单局 Colonel Blotto 对战")
    print("=" * 50)

    # Initialize agents with default YAML and prompts inside expansion_colonel_blotto
    agent0 = Agent0(game_type="colonel_blotto")
    agent1 = Agent1(game_type="colonel_blotto")

    # Show model info
    print("🔧 Agent0 配置信息:")
    print(f"   模型: {agent0.get_model_info().get('model_name')}")
    print(f"   Prompt: {agent0.get_model_info().get('prompt_name')}")
    print("🔧 Agent1 配置信息:")
    print(f"   模型: {agent1.get_model_info().get('model_name')}")
    print(f"   Prompt: {agent1.get_model_info().get('prompt_name')}")

    # Set up game via GameManager
    print("🎯 初始化上校博弈环境 (使用 expansion_src.GameManager 优先)...")
    manager = GameManager()
    manager.setup_game("colonel_blotto")

    # Add agents as player0 and player1
    manager.add_agent(agent0)  # Player 0
    manager.add_agent(agent1)  # Player 1

    # Callbacks to capture observations/actions for unified logs
    game_log = []
    # 按玩家维护累计观察历史（字符串），确保每次日志包含开局信息与所有过往轮次
    obs_history: Dict[int, str] = {}

    def observation_cb(player_id, obs):
        # 直接使用传给代理的累计观察字符串，保证与模型输入一致
        combined = _stringify_observation(obs)
        obs_history[player_id] = combined

        game_log.append({
            "timestamp": datetime.now().isoformat(),
            "type": "observation",
            "player_id": player_id,
            "content": combined,
        })

    def action_cb(player_id, action):
        # 仅记录动作文本，保持与参考日志相同的结构
        game_log.append({
            "timestamp": datetime.now().isoformat(),
            "type": "action",
            "player_id": player_id,
            "content": action,
        })

    def step_complete_cb(done, info):
        # Minimal per-step hook; info already logged by GameManager
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

    return result


if __name__ == "__main__":
    main()