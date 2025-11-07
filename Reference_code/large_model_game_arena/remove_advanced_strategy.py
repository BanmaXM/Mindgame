#!/usr/bin/env python3
"""
Script to remove advanced_strategy.txt content from mindgames_gpt5_cases_0814.json
"""

import json
import os
import re

def remove_advanced_strategy_content(input_file, output_file):
    """
    Remove advanced_strategy.txt content from the JSON file
    """
    # Load the JSON data
    print(f"Loading data from {input_file}...")
    with open(input_file, 'r') as f:
        data = json.load(f)
    
    print(f"Loaded {len(data)} conversation samples")
    
    # Load the advanced_strategy.txt content for reference
    advanced_strategy_file = "/home/syh/mindgames/large_model_game_arena/prompt_pool/colonel_blotto/pool_A/advanced_strategy.txt"
    with open(advanced_strategy_file, 'r') as f:
        advanced_strategy_content = f.read()
    
    # Process each conversation sample
    processed_data = []
    removed_count = 0
    
    for conversation in data:
        messages = conversation.get("messages", [])
        if len(messages) >= 2:
            user_message = messages[0].get("content", "")
            assistant_message = messages[1].get("content", "")
            
            # Check if the user message contains the advanced_strategy content
            if advanced_strategy_content in user_message:
                # Remove the advanced_strategy content from the user message
                new_user_message = user_message.replace(advanced_strategy_content, "").strip()
                
                # Remove any leading/trailing newlines that might be left
                new_user_message = re.sub(r'^\n+', '', new_user_message)
                new_user_message = re.sub(r'\n+$', '', new_user_message)
                
                # Also remove the strategy section that might be present in some samples
                # This is the part that starts with "## Strategy" and ends before "[GAME]"
                strategy_pattern = r'## Strategy.*?(?=\[GAME\])'
                new_user_message = re.sub(strategy_pattern, '', new_user_message, flags=re.DOTALL)
                
                # Clean up any extra newlines that might result from removing the strategy section
                new_user_message = re.sub(r'\n{3,}', '\n\n', new_user_message)
                
                # Remove specific strategy sections that might be present
                # Remove "Core Philosophy" section
                core_philosophy_pattern = r'### Core Philosophy.*?(?=\n###|\n##|\[GAME\]|$)'
                new_user_message = re.sub(core_philosophy_pattern, '', new_user_message, flags=re.DOTALL)
                
                # Remove "Execution Rules" section
                execution_rules_pattern = r'### Execution Rules.*?(?=\n###|\n##|\[GAME\]|$)'
                new_user_message = re.sub(execution_rules_pattern, '', new_user_message, flags=re.DOTALL)
                
                # Remove "Tactical Prototypes and Counters" section
                tactical_pattern = r'### Tactical Prototypes and Counters.*?(?=\n###|\n##|\[GAME\]|$)'
                new_user_message = re.sub(tactical_pattern, '', new_user_message, flags=re.DOTALL)
                
                # Remove "Counter-Strategy Matrix" section
                counter_pattern = r'### Counter-Strategy Matrix.*?(?=\n###|\n##|\[GAME\]|$)'
                new_user_message = re.sub(counter_pattern, '', new_user_message, flags=re.DOTALL)
                
                # Remove "Special Execution Rules" section
                special_pattern = r'### Special Execution Rules.*?(?=\n###|\n##|\[GAME\]|$)'
                new_user_message = re.sub(special_pattern, '', new_user_message, flags=re.DOTALL)
                
                # Remove any standalone "## Strategy" heading that might be left
                standalone_strategy_pattern = r'## Strategy\s*\n'
                new_user_message = re.sub(standalone_strategy_pattern, '', new_user_message)
                
                # Remove specific advanced strategy content that might be present
                # Remove "Always execute a **Two-Front Push**" content
                two_front_pattern = r'Always execute a \*\*Two-Front Push\*\*.*?(?=\n###|\n##|\[GAME\]|$)'
                new_user_message = re.sub(two_front_pattern, '', new_user_message, flags=re.DOTALL)
                
                # Remove "Main Fronts" content
                main_fronts_pattern = r'\*\*Main Fronts:\*\*.*?(?=\n###|\n##|\[GAME\]|$)'
                new_user_message = re.sub(main_fronts_pattern, '', new_user_message, flags=re.DOTALL)
                
                # Remove "Sacrificial Front" content
                sacrificial_pattern = r'\*\*Sacrificial Front:\*\*.*?(?=\n###|\n##|\[GAME\]|$)'
                new_user_message = re.sub(sacrificial_pattern, '', new_user_message, flags=re.DOTALL)
                
                # Remove "Randomization" content
                randomization_pattern = r'\*\*Randomization:\*\*.*?(?=\n###|\n##|\[GAME\]|$)'
                new_user_message = re.sub(randomization_pattern, '', new_user_message, flags=re.DOTALL)
                
                # Clean up extra newlines again
                new_user_message = re.sub(r'\n{3,}', '\n\n', new_user_message)
                new_user_message = re.sub(r'\n{3,}', '\n\n', new_user_message)
                
                new_user_message = new_user_message.strip()
                
                # Create a new conversation with the modified user message
                new_conversation = {
                    "messages": [
                        {
                            "role": "user",
                            "content": new_user_message
                        },
                        {
                            "role": "assistant",
                            "content": assistant_message
                        }
                    ]
                }
                
                processed_data.append(new_conversation)
                removed_count += 1
            else:
                # If no advanced_strategy content, keep the original conversation
                processed_data.append(conversation)
    
    print(f"Processed {len(processed_data)} conversation samples")
    print(f"Removed advanced_strategy content from {removed_count} samples")
    
    # Save the processed data
    print(f"Saving to {output_file}...")
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, 'w') as f:
        json.dump(processed_data, f, indent=2)
    
    print("Processing complete!")

def main():
    # Set paths
    input_file = "/home/syh/mindgames/large_model_game_arena/databottle/mindgames_gpt5_cases_0814.json"
    output_file = "/home/syh/mindgames/large_model_game_arena/databottle/mindgames_gpt5_cases_0814_no_advanced_strategy.json"
    
    # Process the file
    remove_advanced_strategy_content(input_file, output_file)

if __name__ == "__main__":
    main()