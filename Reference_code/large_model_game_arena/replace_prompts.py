#!/usr/bin/env python3
import json
import re

def replace_non_system_prompts(json_file_path, strategy_file_path, output_file_path):
    """
    将JSON文件中所有提示词的非系统提示词部分替换为策略文件的内容
    
    参数:
        json_file_path: 原始JSON文件路径
        strategy_file_path: 策略文件路径
        output_file_path: 输出JSON文件路径
    """
    # 读取策略文件内容
    with open(strategy_file_path, 'r', encoding='utf-8') as f:
        strategy_content = f.read()
    
    # 读取JSON文件
    with open(json_file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # 定义系统提示词的正则表达式模式
    # 匹配以 [GAME] You are Commander Alpha 或 Beta 开头的内容
    system_prompt_pattern = r'(\[GAME\] You are Commander (Alpha|Beta) in a game of ColonelBlotto\. Each round, you have to allocate exactly 20 units across fields: A, B, C\nFormat: \'\[A4 B2 C2\]\'\nWin the majority of fields to win the round!)'
    
    # 处理每个对话
    for conversation in data:
        for message in conversation['messages']:
            if message['role'] == 'user':
                content = message['content']
                
                # 查找系统提示词部分
                match = re.search(system_prompt_pattern, content)
                if match:
                    system_prompt = match.group(1)
                    
                    # 构建新的内容：策略内容 + 系统提示词
                    new_content = strategy_content + "\n\n" + system_prompt
                    
                    # 添加系统提示词之后的所有内容
                    remaining_content = content[match.end():]
                    new_content += remaining_content
                    
                    # 替换原始内容
                    message['content'] = new_content
    
    # 将修改后的数据写入输出文件
    with open(output_file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"处理完成，结果已保存到 {output_file_path}")

if __name__ == "__main__":
    # 文件路径
    json_file = "/home/syh/mindgames/large_model_game_arena/databottle/mindgames_gpt5_cases_0814.json"
    strategy_file = "/home/syh/mindgames/large_model_game_arena/prompt_pool/colonel_blotto/pool_A/advanced_strategy.txt"
    output_file = "/home/syh/mindgames/large_model_game_arena/databottle/mindgames_gpt5_cases_0814_modified.json"
    
    # 执行替换
    replace_non_system_prompts(json_file, strategy_file, output_file)