#!/usr/bin/env python3
"""
一次性可配置运行多局 Colonel Blotto 的便捷脚本。

使用方式：直接编辑本文件顶部的 CONFIG 字典（无需命令行参数），然后执行：
  python expansion_colonel_blotto/run_multi_config.py

可配置项说明（在 CONFIG 中编辑）：
- num_games: int
  运行的局数（例如 1、3、10）。

- rounds: int
  每局的回合数（传入本地扩展环境的 num_rounds）。
  注意：此项依赖 expansion_src.GameManager + 本地 expansion_envs 的实现。

- reasoning: str
  推理开关模式：
    - "off": 关闭推理，响应最快。
    - "on": 开启隐藏推理（router 侧启用 reasoning，响应中不回传思维）。
    - "visible": 开启可见推理（仅调试用，响应中会包含 <think>）。

- reasoning_effort: Optional[str]
  若模型/路由支持，可选 "low" | "medium" | "high" | None。

- request_timeout: Optional[float]
  每次聊天请求的超时时间（秒）。默认 40.0。

- agent0 / agent1: dict
  - model_yaml_path: Optional[str]
    指定该代理的 YAML 模型配置文件路径；留空则使用默认：
      agent0 -> expansion_colonel_blotto/model_pool0/api/openai_gpt5mini.yaml
      agent1 -> expansion_colonel_blotto/model_pool1/api/openai_gpt5mini.yaml
  - prompt_path: Optional[str]
    指定该代理使用的 prompt 文件路径；留空则使用默认：
      agent0 -> expansion_colonel_blotto/prompts/prompt_agent0.txt
      agent1 -> expansion_colonel_blotto/prompts/prompt_agent1.txt
  - model_name_override: Optional[str]
    直接覆盖 YAML 中的模型名（例如 "openai/gpt-5-mini" 或其他在路由可用的模型名）。
    如果不填，按 YAML 配置。

- seed: Optional[int]
  传入 GameManager.start_game 的种子；可复现实验（可留空）。

注意：
- max_tokens 会在 Agent 内部强制不小于 4096（满足你的约束）。
- 本脚本沿用 run_single_colonel_blotto.py 的日志保存格式（详细 JSON + 简要 CSV），
  多局运行会在相同日期目录下生成多份时间戳文件。agent_info.json 会在同一目录下被覆盖为最新一次。
"""

import os
import sys
from datetime import datetime
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

# 确保项目根路径与模块搜索路径
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

EXP_SRC_DIR = os.path.join(ROOT_DIR, "expansion_src")
if EXP_SRC_DIR not in sys.path:
    sys.path.insert(0, EXP_SRC_DIR)

SRC_DIR = os.path.join(ROOT_DIR, "src")
if SRC_DIR not in sys.path:
    sys.path.append(SRC_DIR)

# 复用单局脚本的保存与 JSON 序列化工具
from expansion_colonel_blotto.run_single_colonel_blotto import save_game_data, json_default

# 引入代理
from expansion_colonel_blotto.agents.agent0 import Agent0
from expansion_colonel_blotto.agents.agent1 import Agent1

# 优先使用本地扩展管理器（支持 env_config）
try:
    from expansion_src.game_manager import GameManager
except Exception:
    from src.game_manager import GameManager


# =============== 顶部配置 ===============
CONFIG: Dict[str, Any] = {
    # 要运行的总局数（修改这里即可）
    "num_games": 1,

    # 每局 Colonel Blotto 的回合数（传给 env 的 num_rounds）
    "rounds": 5,

    # reasoning 模式："off" | "on" | "visible"
    "reasoning": "visible",

    # reasoning 强度（可选）：None | "low" | "medium" | "high"
    "reasoning_effort": "medium",

    # 超时（秒）。为 None 则使用 Agent 内默认
    "request_timeout": None,

    # Agent0 的配置（玩家 0）
    "agent0": {
        # 可选：替换成你自己的 YAML 路径；留空使用默认
        "model_yaml_path": None,
        # 可选：替换成你自己的 prompt 文件路径；留空使用默认
        "prompt_path": None,
        # 可选：直接覆盖 YAML 中的模型名（例如 "openai/gpt-5-mini"）
        "model_name_override": None,
    },

    # Agent1 的配置（玩家 1）
    "agent1": {
        "model_yaml_path": None,
        "prompt_path": None,
        "model_name_override": None,
    },

    # 可选：固定随机种子（传入 start_game），便于复现实验
    "seed": None,
}


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
                    # 非预期项，跳过不必要的repr
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
            # 普通字符串直接返回
            return s
    except Exception:
        # 任何解析异常，退回安全的字符串化
        return str(obs)
    # 兜底
    return str(obs)


def _dedupe_lines(text: str) -> str:
    """按行去重并压缩空行，保持顺序稳定。"""
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
                # 重复行跳过
                continue
        else:
            # 压缩连续空行为一个
            if not prev_blank:
                result.append("")
                prev_blank = True
    # 去掉首尾空行
    while result and result[0].strip() == "":
        result.pop(0)
    while result and result[-1].strip() == "":
        result.pop()
    return "\n".join(result)


def _build_agents(cfg: Dict[str, Any]) -> tuple[Agent0, Agent1]:
    """按配置构造两位代理，并应用可选的模型名覆盖。"""
    a0_conf = cfg.get("agent0", {}) or {}
    a1_conf = cfg.get("agent1", {}) or {}

    agent0 = Agent0(
        game_type="colonel_blotto",
        model_yaml_path=a0_conf.get("model_yaml_path"),
        prompt_path=a0_conf.get("prompt_path"),
        reasoning=cfg.get("reasoning", "off"),
        reasoning_effort=cfg.get("reasoning_effort"),
        request_timeout=cfg.get("request_timeout"),
    )
    agent1 = Agent1(
        game_type="colonel_blotto",
        model_yaml_path=a1_conf.get("model_yaml_path"),
        prompt_path=a1_conf.get("prompt_path"),
        reasoning=cfg.get("reasoning", "off"),
        reasoning_effort=cfg.get("reasoning_effort"),
        request_timeout=cfg.get("request_timeout"),
    )

    # 可选：直接覆盖模型名（无需改 YAML 文件）
    m0 = a0_conf.get("model_name_override")
    if m0:
        try:
            agent0.agent_instance.model_name = m0
        except Exception:
            pass
    m1 = a1_conf.get("model_name_override")
    if m1:
        try:
            agent1.agent_instance.model_name = m1
        except Exception:
            pass

    return agent0, agent1


def run_one_game(cfg: Dict[str, Any]) -> Dict[str, Any]:
    """运行一局，返回 GameManager.play_game 的结果。"""
    rounds = int(cfg.get("rounds", 3))
    seed = cfg.get("seed")

    agent0, agent1 = _build_agents(cfg)

    # 显示配置信息
    print("🔧 Agent0 配置信息:")
    try:
        a0_model_print = getattr(agent0.agent_instance, "model_name", None) or agent0.get_model_info().get("model_name")
    except Exception:
        a0_model_print = agent0.get_model_info().get("model_name")
    print(f"   模型: {a0_model_print}")
    print(f"   Prompt: {agent0.get_model_info().get('prompt_name')}")
    print("🔧 Agent1 配置信息:")
    try:
        a1_model_print = getattr(agent1.agent_instance, "model_name", None) or agent1.get_model_info().get("model_name")
    except Exception:
        a1_model_print = agent1.get_model_info().get("model_name")
    print(f"   模型: {a1_model_print}")
    print(f"   Prompt: {agent1.get_model_info().get('prompt_name')}")

    # 初始化与配置环境
    print("🎯 初始化上校博弈环境 (使用 expansion_src.GameManager 优先)...")
    manager = GameManager()
    manager.setup_game("colonel_blotto", env_config={"num_rounds": rounds})

    manager.add_agent(agent0)
    manager.add_agent(agent1)

    # 回调日志
    game_log: List[Dict[str, Any]] = []
    # 按玩家维护累计观察历史（字符串），确保每次日志包含开局信息与所有过往轮次
    obs_history: Dict[int, str] = {}

    def observation_cb(player_id, obs):
        # 使用原始聚合后的观察字符串，确保与模型输入完全一致
        s = _stringify_observation(obs)
        combined = s
        obs_history[player_id] = combined

        game_log.append({
            "timestamp": datetime.now().isoformat(),
            "type": "observation",
            "player_id": player_id,
            "content": combined,
        })

    def action_cb(player_id, action):
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

    # 运行
    print("🎮 开始游戏...")
    manager.start_game(seed=seed)
    result = manager.play_game(callbacks=callbacks)

    print("\n===== 游戏结果 =====")
    print(f"  状态: {result.get('status')}")
    print(f"  总步数: {result.get('steps')}")
    rewards = result.get('rewards')
    if rewards is not None:
        print(f"  奖励: {rewards}")
        try:
            if isinstance(rewards, dict):
                max_r = max(rewards.values())
                winners = [pid for pid, r in rewards.items() if r == max_r]
            else:
                max_r = max(rewards)
                winners = [i for i, r in enumerate(rewards) if r == max_r]
            print(f"  胜者: {winners}")
        except Exception:
            pass

    # 保存日志到单局目录
    data_root = Path(os.path.dirname(os.path.abspath(__file__))) / "data" / "single_runs" / datetime.now().strftime("%Y-%m-%d")
    # 生成 agent_info，并在需要时用实际的 agent_instance.model_name 覆盖
    agent0_info = agent0.get_model_info()
    agent1_info = agent1.get_model_info()
    try:
        real_m0 = getattr(agent0.agent_instance, "model_name", None)
        if real_m0:
            agent0_info["model_name"] = real_m0
    except Exception:
        pass
    try:
        real_m1 = getattr(agent1.agent_instance, "model_name", None)
        if real_m1:
            agent1_info["model_name"] = real_m1
    except Exception:
        pass

    agent_info = {
        "agent_0": agent0_info,
        "agent_1": agent1_info,
        "game": "colonel_blotto",
        "timestamp": datetime.now().isoformat(),
    }
    run_dir = save_game_data(data_root, game_log, agent_info, result)
    print(f"🧾 日志已保存: {run_dir}")

    return result


def main():
    print("🚀 多局 Colonel Blotto 对战 - 可配置脚本")
    print("=" * 56)

    num_games = int(CONFIG.get("num_games", 1))
    print(f"计划运行局数: {num_games}")
    print(f"reasoning: {CONFIG.get('reasoning')} | effort: {CONFIG.get('reasoning_effort')} | rounds: {CONFIG.get('rounds')}")

    all_results: List[Dict[str, Any]] = []
    for i in range(1, num_games + 1):
        print("\n" + "-" * 12 + f" 第 {i}/{num_games} 局 " + "-" * 12)
        try:
            res = run_one_game(CONFIG)
            all_results.append(res)
        except Exception as e:
            print(f"❌ 第 {i} 局运行失败: {e}")

    # 简单汇总
    if all_results:
        total_steps = sum(int(r.get("steps", 0)) for r in all_results)
        avg_steps = total_steps / len(all_results)
        print("\n===== 汇总统计 =====")
        print(f"  总局数: {len(all_results)}")
        print(f"  平均步数: {avg_steps:.2f}")
        # 胜者统计（如果 reward 可判胜者）
        wins: Dict[int, int] = {0: 0, 1: 0, -1: 0}  # -1 代表平局或无法判定
        for r in all_results:
            rewards = r.get("rewards")
            winner = None
            try:
                if isinstance(rewards, dict) and rewards:
                    max_r = max(rewards.values())
                    winners = [pid for pid, rv in rewards.items() if rv == max_r]
                    winner = winners[0] if len(winners) == 1 else -1
                elif isinstance(rewards, (list, tuple)) and rewards:
                    max_r = max(rewards)
                    winners = [idx for idx, rv in enumerate(rewards) if rv == max_r]
                    winner = winners[0] if len(winners) == 1 else -1
            except Exception:
                winner = -1
            wins[winner if winner in (0, 1) else -1] += 1
        print(f"  胜者统计: P0={wins.get(0,0)} | P1={wins.get(1,0)} | 平局/未判定={wins.get(-1,0)}")


if __name__ == "__main__":
    main()