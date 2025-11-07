#!/usr/bin/env python3
"""
移除JSON文件中所有思考部分的脚本
思考部分被标记为 <think> 和 </think> 之间的内容
"""

import json
import re

def remove_thinking_parts(content):
    """
    移除内容中所有 <think> 和 </think> 之间的思考部分
    """
    # 使用正则表达式匹配 <think> 和 </think> 之间的所有内容
    # re.DOTALL 让 . 匹配包括换行符在内的所有字符
    pattern = r'<think>.*?</think>'
    
    # 替换所有匹配的思考部分为空字符串
    cleaned_content = re.sub(pattern, '', content, flags=re.DOTALL)
    
    return cleaned_content

def process_json_file(input_file, output_file):
    """
    处理JSON文件，移除所有思考部分
    """
    print(f"正在读取文件: {input_file}")
    
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print(f"找到 {len(data)} 个游戏案例")
    
    # 处理每个游戏案例
    for i, case in enumerate(data):
        messages = case.get('messages', [])
        
        for j, message in enumerate(messages):
            if 'content' in message:
                original_content = message['content']
                
                # 检查是否包含思考部分
                if '<think>' in original_content and '</think>' in original_content:
                    print(f"案例 {i+1}, 消息 {j+1}: 发现思考部分")
                    
                    # 移除思考部分
                    cleaned_content = remove_thinking_parts(original_content)
                    message['content'] = cleaned_content
    
    # 保存处理后的数据
    print(f"正在保存到: {output_file}")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print("处理完成！")

if __name__ == "__main__":
    input_file = "/home/syh/mindgames/large_model_game_arena/databottle/mindgames_gpt5_cases_0814_modified.json"
    output_file = "/home/syh/mindgames/large_model_game_arena/databottle/mindgames_gpt5_cases_0814_no_thinking.json"
    
    process_json_file(input_file, output_file)