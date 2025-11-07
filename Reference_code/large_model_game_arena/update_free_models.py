#!/usr/bin/env python3
"""
更新模型配置脚本，将所有free模型替换为非free模型
"""

import os
import yaml
import shutil
from pathlib import Path

def update_free_models():
    """更新所有free模型为非free模型"""
    model_pool_path = "model_pool/pool_B/api"
    
    # 遍历所有模型配置文件
    for filename in os.listdir(model_pool_path):
        if filename.endswith('.yaml'):
            # 获取文件路径
            file_path = os.path.join(model_pool_path, filename)
            
            try:
                # 读取配置文件
                with open(file_path, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)
                
                # 获取原始模型名称
                original_model = config.get('model', '')
                
                # 检查是否为free模型
                if ':free' in original_model or '-free' in filename:
                    # 替换free模型为非free模型
                    new_model = original_model.replace(':free', '')
                    config['model'] = new_model
                    
                    # 创建新文件名
                    new_filename = filename.replace(':free', '').replace('-free', '')
                    new_file_path = os.path.join(model_pool_path, new_filename)
                    
                    # 保存新配置
                    with open(new_file_path, 'w', encoding='utf-8') as f:
                        yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
                    
                    print(f"已更新模型配置: {original_model} -> {new_model}")
                    print(f"新配置文件: {new_file_path}")
                    
                    # 删除旧文件
                    os.remove(file_path)
                    print(f"已删除旧配置文件: {file_path}")
                    
            except Exception as e:
                print(f"处理文件 {filename} 时出错: {e}")

if __name__ == "__main__":
    print("开始更新free模型为非free模型...")
    update_free_models()
    print("更新完成!")