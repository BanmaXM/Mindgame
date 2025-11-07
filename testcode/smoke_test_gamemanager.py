import random
import sys
from pathlib import Path

# Make repo root importable when running as a script
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from expansion_src.game_manager import GameManager


class EchoAgent:
    def __init__(self, name="echo"):
        self.name = name
    def __call__(self, observation: str) -> str:
        # always pass or echo a plausible token depending on game
        # keep it simple: just return "[pass]"
        return "[pass]"


def run_secret_mafia():
    gm = GameManager()
    gm.setup_game("secret_mafia", env_config={"mafia_ratio": 0.25, "discussion_rounds": 1})
    # 6 players minimum
    for _ in range(6):
        gm.add_agent(EchoAgent())
    gm.start_game(seed=42)
    res = gm.play_game(max_steps=50)
    return res


def run_three_player_ipd():
    gm = GameManager()
    gm.setup_game("three_player_ipd", env_config={"num_rounds": 1, "communication_turns": 1})
    for _ in range(3):
        gm.add_agent(EchoAgent())
    gm.start_game(seed=123)
    res = gm.play_game(max_steps=50)
    return res


def run_colonel_blotto():
    gm = GameManager()
    gm.setup_game("colonel_blotto", env_config={"num_rounds": 1})
    for _ in range(2):
        gm.add_agent(EchoAgent())
    gm.start_game(seed=7)
    res = gm.play_game(max_steps=50)
    return res


def run_codenames():
    gm = GameManager()
    gm.setup_game("codenames", env_config={})
    for _ in range(4):
        gm.add_agent(EchoAgent())
    gm.start_game(seed=9)
    res = gm.play_game(max_steps=50)
    return res


if __name__ == "__main__":
    # Run minimal flows; they may end early by invalid move rules
    results = {}
    try:
        results["secret_mafia"] = run_secret_mafia()
    except Exception as e:
        results["secret_mafia"] = f"ERROR: {e}"
    try:
        results["three_player_ipd"] = run_three_player_ipd()
    except Exception as e:
        results["three_player_ipd"] = f"ERROR: {e}"
    try:
        results["colonel_blotto"] = run_colonel_blotto()
    except Exception as e:
        results["colonel_blotto"] = f"ERROR: {e}"
    try:
        results["codenames"] = run_codenames()
    except Exception as e:
        results["codenames"] = f"ERROR: {e}"

    for k, v in results.items():
        print(f"{k}: {type(v)} -> {v if isinstance(v, str) else v.get('status')}")