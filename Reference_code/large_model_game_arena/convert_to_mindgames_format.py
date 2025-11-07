#!/usr/bin/env python3
"""
Script to convert Colonel Blotto game data to SFT format similar to mindgames_gpt5_cases_0814.json
"""

import json
import os
import glob
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
                if os.path.exists(game_file):
                    with open(game_file, 'r') as f:
                        game_data = json.load(f)
                        all_games.append(game_data)
    
    return all_games

def extract_conversation_steps(game_data):
    """Extract conversation steps from game data"""
    steps = game_data.get("steps", [])
    conversations = []
    
    for step in steps:
        # Create user message from observation
        user_content = step.get("observation", "")
        
        # Extract system prompt from model_input
        system_prompt = ""
        model_input = step.get("model_input", {})
        if "system_prompt" in model_input:
            system_prompt = model_input["system_prompt"]
        
        # Prepend system prompt to user content
        if system_prompt:
            user_content = f"{system_prompt}\n\n{user_content}"
        
        # Create assistant message from action
        assistant_content = step.get("action", "")
        
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