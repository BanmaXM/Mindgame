#!/usr/bin/env python3
"""
移除JSON文件中包含空content的样例
"""

import json

def remove_empty_content_cases(input_file, output_file):
    """
    移除包含空content的样例
    """
    print(f"正在读取文件: {input_file}")
    
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print(f"原始文件包含 {len(data)} 个样例")
    
    # 过滤掉包含空content的样例
    filtered_data = []
    removed_count = 0
    
    for i, case in enumerate(data):
        messages = case.get('messages', [])
        has_empty_content = False
        
        # 检查每个消息的content是否为空
        for j, message in enumerate(messages):
            content = message.get('content', '')
            # 如果content是空字符串或只包含空白字符
            if not content or content.strip() == '':
                print(f"发现空content: 样例 {i+1}, 消息 {j+1}, 角色: {message.get('role', 'unknown')}")
                has_empty_content = True
                break
        
        if has_empty_content:
            removed_count += 1
            print(f"移除样例 {i+1}: 包含空content")
        else:
            filtered_data.append(case)
    
    print(f"移除了 {removed_count} 个包含空content的样例")
    print(f"剩余 {len(filtered_data)} 个有效样例")
    
    # 保存处理后的数据
    print(f"正在保存到: {output_file}")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(filtered_data, f, ensure_ascii=False, indent=2)
    
    print("处理完成！")

if __name__ == "__main__":
    input_file = "/home/syh/mindgames/large_model_game_arena/databottle/mindgames_gpt5_cases_0814_no_thinking.json"
    output_file = "/home/syh/mindgames/large_model_game_arena/databottle/mindgames_gpt5_cases_0814_cleaned.json"
    
    remove_empty_content_cases(input_file, output_file)