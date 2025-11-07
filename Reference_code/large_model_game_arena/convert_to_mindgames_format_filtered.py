#!/usr/bin/env python3
"""
Script to convert Colonel Blotto game data to SFT format similar to mindgames_gpt5_cases_0814.json
Only include data where:
1. The prompt used is 'advanced_strategy'
2. The player won or drew in that round
"""

import json
import os
import glob
import re
from pathlib import Path

def load_colonel_blotto_data(data_dir):
    """Load all Colonel Blotto game data from batch runs"""
    all_games = []
    
    batch_runs_dir = os.path.join(data_dir, "batch_runs")
    for batch_dir in sorted(glob.glob(os.path.join(batch_runs_dir, "batch_run_*"))):
        timestamp_dirs = glob.glob(os.path.join(batch_dir, "*"))
        for timestamp_dir in timestamp_dirs:
            if os.path.isdir(timestamp_dir):
                game_file = os.path.join(timestamp_dir, os.path.basename(timestamp_dir) + "_colonel_blotto.json")
                agent_info_file = os.path.join(timestamp_dir, "agent_info.json")
                
                if os.path.exists(game_file) and os.path.exists(agent_info_file):
                    with open(game_file, 'r') as f:
                        game_data = json.load(f)
                    with open(agent_info_file, 'r') as f:
                        agent_info = json.load(f)
                    
                    # Add agent info to game data for later filtering
                    game_data["agent_info"] = agent_info
                    all_games.append(game_data)
    
    return all_games

def parse_action(action_text):
    """Parse the action text to extract troop allocation"""
    # Look for pattern like [A9 B8 C3]
    match = re.search(r'\[A(\d+) B(\d+) C(\d+)\]', action_text)
    if match:
        return {
            'A': int(match.group(1)),
            'B': int(match.group(2)),
            'C': int(match.group(3))
        }
    return None

def determine_winner(observation_text, player_id):
    """Determine if the player won or drew based on the observation text"""
    # Look for pattern like "Winner: Commander Alpha" or "Winner: Commander Beta"
    match = re.search(r'Winner: Commander (\w+)', observation_text)
    if match:
        winner = match.group(1)
        if player_id == 0 and winner == "Alpha":
            return "win"
        elif player_id == 1 and winner == "Beta":
            return "win"
        else:
            return "lose"
    
    # If no explicit winner found, try to determine from troop allocations
    # Look for pattern like "Commander Alpha allocated: A: 9 , B: 8 , C: 3"
    alpha_match = re.search(r'Commander Alpha allocated: A: (\d+) , B: (\d+) , C: (\d+)', observation_text)
    beta_match = re.search(r'Commander Beta allocated: A: (\d+) , B: (\d+) , C: (\d+)', observation_text)
    
    if alpha_match and beta_match:
        alpha_troops = {
            'A': int(alpha_match.group(1)),
            'B': int(alpha_match.group(2)),
            'C': int(alpha_match.group(3))
        }
        beta_troops = {
            'A': int(beta_match.group(1)),
            'B': int(beta_match.group(2)),
            'C': int(beta_match.group(3))
        }
        
        # Count wins for each player
        alpha_wins = 0
        beta_wins = 0
        
        for field in ['A', 'B', 'C']:
            if alpha_troops[field] > beta_troops[field]:
                alpha_wins += 1
            elif beta_troops[field] > alpha_troops[field]:
                beta_wins += 1
            # If equal, it's a draw for that field
        
        if player_id == 0:
            return "win" if alpha_wins > beta_wins else ("lose" if alpha_wins < beta_wins else "draw")
        else:
            return "win" if beta_wins > alpha_wins else ("lose" if beta_wins < alpha_wins else "draw")
    
    return "unknown"

def extract_conversation_steps(game_data):
    """Extract conversation steps from game data, filtering by prompt and win/loss"""
    steps = game_data.get("steps", [])
    agent_info = game_data.get("agent_info", {})
    player_agent_mapping = game_data.get("player_agent_mapping", {})
    
    # Find which player_id corresponds to agent_0 (which uses advanced_strategy)
    target_player_id = None
    for player_id, agent_name in player_agent_mapping.items():
        if agent_name == "agent_0" and agent_info.get("agent_0", {}).get("prompt_name", "") == "advanced_strategy":
            target_player_id = int(player_id)
            break
    
    # If no player uses advanced_strategy, return empty list
    if target_player_id is None:
        return []
    
    conversations = []
    
    # Process steps in pairs (player 0 and player 1 for each round)
    for i in range(0, len(steps), 2):
        if i + 1 >= len(steps):
            break
            
        step_0 = steps[i]  # Player 0
        step_1 = steps[i+1]  # Player 1
        
        # Only process if this is the target player with advanced_strategy
        if step_0.get("player_id") != target_player_id and step_1.get("player_id") != target_player_id:
            continue
            
        # Get the step for the target player
        target_step = step_0 if step_0.get("player_id") == target_player_id else step_1
        
        # Check if target player won or drew in this round
        observation = target_step.get("observation", "")
        result = determine_winner(observation, target_player_id)
        
        # Include data if target player won or drew
        if result not in ["win", "draw"]:
            continue
            
        # Create user message from observation
        user_content = observation
        
        # Extract system prompt from model_input
        system_prompt = ""
        model_input = target_step.get("model_input", {})
        if "system_prompt" in model_input:
            system_prompt = model_input["system_prompt"]
        
        # Prepend system prompt to user content
        if system_prompt:
            user_content = f"{system_prompt}\n\n{user_content}"
        
        # Create assistant message from action
        assistant_content = target_step.get("action", "")
        
        # Create conversation entry
        conversation = {
            "messages": [
                {
                    "role": "user",
                    "content": user_content
                },
                {
                    "role": "assistant",
                    "content": assistant_content
                }
            ]
        }
        
        conversations.append(conversation)
    
    return conversations

def convert_to_sft_format(all_games):
    """Convert all games to SFT format"""
    sft_data = []
    
    for game_data in all_games:
        conversations = extract_conversation_steps(game_data)
        sft_data.extend(conversations)
    
    return sft_data

def main():
    # Set paths
    data_dir = "/home/syh/mindgames/large_model_game_arena/data/colonel_blotto"
    output_file = "/home/syh/mindgames/large_model_game_arena/databottle/mindgames_gpt5_cases_0814.json"
    
    # Load Colonel Blotto data
    print("Loading Colonel Blotto data...")
    all_games = load_colonel_blotto_data(data_dir)
    print(f"Loaded {len(all_games)} games")
    
    # Convert to SFT format
    print("Converting to SFT format...")
    sft_data = convert_to_sft_format(all_games)
    print(f"Generated {len(sft_data)} conversation samples")
    
    # Save to file
    print(f"Saving to {output_file}...")
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, 'w') as f:
        json.dump(sft_data, f, indent=2)
    
    print("Conversion complete!")

if __name__ == "__main__":
    main()