#!/usr/bin/env python3
"""
Parse Colonel Blotto run JSONs into per-round CSVs.

- Round boundary: from one player0 action to the next player0 action.
- For each round, take the last actions of player0 and player1 observed in that interval.
- Decide the round winner by battlefield majority: compare A/B/C; higher value wins a field; majority wins the round; ties yield a draw.

Outputs:
- For each run directory containing `colonel_blotto.json`, create `rounds.csv` with columns:
  round_index, p0_action, p1_action, winner, p0_cum_wins, p1_cum_wins.

Usage:
    python3 blotto_rounds_to_csv.py \
        --root /home/syhh/Mindgame/expansion_colonel_blotto/data/single_runs

If --root is omitted, defaults to the above path.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple


ACTION_RE = re.compile(r"([ABCabc])\s*:?\s*(\d+)")


def parse_action(action_str: str) -> Optional[Tuple[int, int, int]]:
    """Parse action like "[A2 B10 C8]" to (A, B, C).
    Returns None if cannot parse three fields.
    """
    if not isinstance(action_str, str):
        return None
    pairs = ACTION_RE.findall(action_str)
    if not pairs:
        return None
    values: Dict[str, int] = {}
    for k, v in pairs:
        values[k.upper()] = int(v)
    if all(x in values for x in ("A", "B", "C")):
        return values["A"], values["B"], values["C"]
    return None


def decide_winner(p0: Tuple[int, int, int], p1: Tuple[int, int, int]) -> int:
    """Return 0 if player0 wins, 1 if player1 wins, -1 if draw."""
    a0, b0, c0 = p0
    a1, b1, c1 = p1
    wins0 = (1 if a0 > a1 else 0) + (1 if b0 > b1 else 0) + (1 if c0 > c1 else 0)
    wins1 = (1 if a1 > a0 else 0) + (1 if b1 > b0 else 0) + (1 if c1 > c0 else 0)
    if wins0 > wins1:
        return 0
    if wins1 > wins0:
        return 1
    return -1


@dataclass
class RoundRecord:
    round_index: int
    p0_action_str: str
    p1_action_str: str
    p0_vals: Tuple[int, int, int]
    p1_vals: Tuple[int, int, int]
    winner: int  # 0, 1, or -1
    p0_cum_wins: int
    p1_cum_wins: int
    start_step: int
    end_step: int
    start_ts: str
    end_ts: str


def process_run(json_path: Path) -> List[RoundRecord]:
    data = json.loads(json_path.read_text())
    steps = data.get("steps", [])
    rounds: List[RoundRecord] = []

    p0_cum = 0
    p1_cum = 0

    # Pending info for current boundary (from a P0 until next P0)
    pending_p0_action_str: Optional[str] = None
    pending_p1_action_str: Optional[str] = None
    pending_p0_vals: Optional[Tuple[int, int, int]] = None
    pending_p1_vals: Optional[Tuple[int, int, int]] = None
    pending_start_step: Optional[int] = None
    pending_start_ts: Optional[str] = None
    has_p1_between: bool = False

    for s in steps:
        player_id = s.get("player_id")
        action_str = s.get("action")
        step_num = s.get("step_num")
        ts = s.get("timestamp")

        if player_id == 0:
            if pending_p0_action_str is None:
                # First P0: start boundary
                pending_p0_action_str = action_str or ""
                pending_p0_vals = parse_action(pending_p0_action_str) or (0, 0, 0)
                pending_p1_action_str = None
                pending_p1_vals = None
                has_p1_between = False
                pending_start_step = step_num if isinstance(step_num, int) else None
                pending_start_ts = ts or None
            else:
                # Next P0 encountered: boundary crossed
                if has_p1_between and (pending_p1_action_str is not None):
                    # finalize previous round using last P0 & last P1 within boundary
                    winner = decide_winner(pending_p0_vals, pending_p1_vals)  # type: ignore[arg-type]
                    if winner == 0:
                        p0_cum += 1
                    elif winner == 1:
                        p1_cum += 1
                    rounds.append(
                        RoundRecord(
                            round_index=len(rounds) + 1,
                            p0_action_str=pending_p0_action_str or "",
                            p1_action_str=pending_p1_action_str or "",
                            p0_vals=pending_p0_vals or (0, 0, 0),
                            p1_vals=pending_p1_vals or (0, 0, 0),
                            winner=winner,
                            p0_cum_wins=p0_cum,
                            p1_cum_wins=p1_cum,
                            start_step=pending_start_step or -1,
                            end_step=step_num if isinstance(step_num, int) else -1,
                            start_ts=pending_start_ts or "",
                            end_ts=ts or "",
                        )
                    )
                # Start new boundary with this P0; if no P1 in previous boundary, we simply overwrite P0
                pending_p0_action_str = action_str or ""
                pending_p0_vals = parse_action(pending_p0_action_str) or (0, 0, 0)
                pending_p1_action_str = None
                pending_p1_vals = None
                has_p1_between = False
                pending_start_step = step_num if isinstance(step_num, int) else None
                pending_start_ts = ts or None

        elif player_id == 1:
            # Update last player1 action within current boundary
            if pending_p0_action_str is None:
                # Player1 action before any player0 — ignore safely
                continue
            pending_p1_action_str = action_str or ""
            pending_p1_vals = parse_action(pending_p1_action_str) or (0, 0, 0)
            has_p1_between = True

        else:
            # Unknown player id; ignore
            continue

    # Finalize last round if complete and had P1
    if (pending_p0_action_str is not None) and has_p1_between and (pending_p1_action_str is not None):
        winner = decide_winner(pending_p0_vals, pending_p1_vals)  # type: ignore[arg-type]
        if winner == 0:
            p0_cum += 1
        elif winner == 1:
            p1_cum += 1
        # end_step/ts unknown at file end; reuse last known ts/step if available
        end_step = steps[-1].get("step_num") if steps else -1
        end_ts = steps[-1].get("timestamp") if steps else ""
        rounds.append(
            RoundRecord(
                round_index=len(rounds) + 1,
                p0_action_str=pending_p0_action_str or "",
                p1_action_str=pending_p1_action_str or "",
                p0_vals=pending_p0_vals or (0, 0, 0),
                p1_vals=pending_p1_vals or (0, 0, 0),
                winner=winner,
                p0_cum_wins=p0_cum,
                p1_cum_wins=p1_cum,
                start_step=pending_start_step or -1,
                end_step=end_step if isinstance(end_step, int) else -1,
                start_ts=pending_start_ts or "",
                end_ts=end_ts or "",
            )
        )

    return rounds


def write_rounds_csv(run_dir: Path, rounds: List[RoundRecord]) -> Path:
    out_path = run_dir / "rounds.csv"
    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "round_index",
            "p0_action",
            "p1_action",
            "winner",
            "p0_cum_wins",
            "p1_cum_wins",
        ])
        for r in rounds:
            writer.writerow([
                r.round_index,
                r.p0_action_str,
                r.p1_action_str,
                r.winner,
                r.p0_cum_wins,
                r.p1_cum_wins,
            ])
    return out_path


def find_runs(root: Path) -> List[Path]:
    runs: List[Path] = []
    for p in root.rglob("colonel_blotto.json"):
        runs.append(p.parent)
    return sorted(runs)


def main():
    parser = argparse.ArgumentParser(description="Convert Colonel Blotto JSON runs to per-round CSVs.")
    parser.add_argument(
        "--root",
        type=Path,
        default=Path("/home/syhh/Mindgame/expansion_colonel_blotto/data/single_runs"),
        help="Root directory containing run subfolders with colonel_blotto.json",
    )
    args = parser.parse_args()

    root = args.root
    if not root.exists():
        raise SystemExit(f"Root path not found: {root}")

    run_dirs = find_runs(root)
    if not run_dirs:
        raise SystemExit(f"No runs found under: {root}")

    print(f"[INFO] Found {len(run_dirs)} runs under {root}")
    for run_dir in run_dirs:
        json_path = run_dir / "colonel_blotto.json"
        try:
            rounds = process_run(json_path)
            out_csv = write_rounds_csv(run_dir, rounds)
            print(f"[OK] {run_dir.name}: wrote {len(rounds)} rounds -> {out_csv}")
        except Exception as e:
            print(f"[ERROR] {run_dir}: {e}")


if __name__ == "__main__":
    main()