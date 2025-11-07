#!/usr/bin/env python3
"""
测试模型配置的脚本
"""

import os
import sys
import yaml
from pathlib import Path

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agents.agent_0 import Agent0
from agents.agent_1 import Agent1

def test_model_config():
    """测试模型配置"""
    print("🚀 测试模型配置")
    print("=" * 50)
    
    # 测试模型池A的模型
    models_to_test = [
        "api/openai-gpt-5",
        "api/x-ai-grok-4-fast-free",
        "api/google-gemini-2.5-pro"
    ]
    
    for model_name in models_to_test:
        print(f"\n🔄 测试模型: {model_name}")
        try:
            # 创建Agent0实例（使用模型池A）
            agent = Agent0(game_type="colonel_blotto", model_name=model_name, prompt_name="advanced_strategy")
            model_info = agent.get_model_info()
            print(f"✅ 模型配置加载成功!")
            print(f"   模型: {model_info.get('model_name', 'N/A')}")
            print(f"   API Base: {model_info.get('config', {}).get('api_base', 'N/A')}")
            print(f"   Extra Headers: {model_info.get('config', {}).get('extra_headers', {})}")
            
            # 创建Agent1实例（使用模型池B）
            agent_b = Agent1(game_type="colonel_blotto", model_name=model_name, prompt_name="simple_role_play")
            model_info_b = agent_b.get_model_info()
            print(f"✅ 对手模型配置加载成功!")
            print(f"   模型: {model_info_b.get('model_name', 'N/A')}")
            print(f"   API Base: {model_info_b.get('config', {}).get('api_base', 'N/A')}")
            print(f"   Extra Headers: {model_info_b.get('config', {}).get('extra_headers', {})}")
            
        except Exception as e:
            print(f"❌ 模型配置加载失败: {e}")
    
    print("\n✅ 所有模型配置测试完成!")

if __name__ == "__main__":
    test_model_config()