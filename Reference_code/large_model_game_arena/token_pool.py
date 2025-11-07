#!/usr/bin/env python3
"""
令牌池管理模块
用于管理多个API令牌，实现令牌轮换使用，避免高并发时的令牌竞争
"""

import threading
import time
from typing import List, Dict, Optional, Any
from collections import defaultdict
import random
import yaml
import os

class TokenPool:
    """令牌池管理类"""
    
    def __init__(self, pool_name: str = "default"):
        self.pool_name = pool_name
        self.token_pools = defaultdict(list)  # 按模型名称存储令牌池
        self.token_locks = defaultdict(threading.Lock)  # 每个模型一个锁
        self.token_indices = defaultdict(int)  # 记录当前使用的令牌索引
        self.token_usage_stats = defaultdict(lambda: defaultdict(int))  # 令牌使用统计
        self.lock = threading.Lock()  # 全局锁
        
    def add_tokens(self, model_name: str, tokens: List[str]):
        """为指定模型添加令牌到池中"""
        with self.token_locks[model_name]:
            self.token_pools[model_name].extend(tokens)
            print(f"[{self.pool_name}] 已为模型 {model_name} 添加 {len(tokens)} 个令牌，当前总令牌数: {len(self.token_pools[model_name])}")
    
    def get_token(self, model_name: str) -> Optional[str]:
        """获取指定模型的下一个可用令牌（轮询方式）"""
        with self.token_locks[model_name]:
            if not self.token_pools[model_name]:
                return None
            
            # 轮询获取令牌
            token_index = self.token_indices[model_name] % len(self.token_pools[model_name])
            token = self.token_pools[model_name][token_index]
            
            # 更新索引和使用统计
            self.token_indices[model_name] = (token_index + 1) % len(self.token_pools[model_name])
            self.token_usage_stats[model_name][token] += 1
            
            return token
    
    def get_random_token(self, model_name: str) -> Optional[str]:
        """随机获取指定模型的令牌"""
        with self.token_locks[model_name]:
            if not self.token_pools[model_name]:
                return None
            
            token = random.choice(self.token_pools[model_name])
            self.token_usage_stats[model_name][token] += 1
            return token
    
    def get_usage_stats(self) -> Dict[str, Dict[str, int]]:
        """获取令牌使用统计"""
        return dict(self.token_usage_stats)
    
    def print_usage_stats(self):
        """打印令牌使用统计"""
        print(f"\n=== [{self.pool_name}] 令牌使用统计 ===")
        has_stats = False
        for model_name, stats in self.token_usage_stats.items():
            if stats:  # 只有当有统计数据时才打印
                has_stats = True
                print(f"模型 {model_name}:")
                total_usage = sum(stats.values())
                print(f"  总使用次数: {total_usage}")
                for token, count in stats.items():
                    # 只显示令牌的前8个字符，保护隐私
                    token_preview = token[:8] + "..." if len(token) > 8 else token
                    percentage = (count / total_usage * 100) if total_usage > 0 else 0
                    print(f"  {token_preview}: {count} 次 ({percentage:.1f}%)")
        
        if not has_stats:
            print("暂无令牌使用统计")
        print("===================")

# 全局令牌池实例
colonel_blotto_token_pool = TokenPool("Colonel Blotto")
three_player_ipd_token_pool = TokenPool("Three Player IPD")

def initialize_colonel_blotto_token_pools():
    """初始化上校博弈专用令牌池"""
    # 加载现有令牌
    model_pool_path = "model_pool"
    
    # 遍历所有模型池
    for pool_name in ["pool_A", "pool_B"]:
        pool_path = os.path.join(model_pool_path, pool_name, "api")
        if not os.path.exists(pool_path):
            continue
            
        for filename in os.listdir(pool_path):
            if filename.endswith('.yaml'):
                model_name = filename[:-5]  # 移除.yaml后缀
                config_path = os.path.join(pool_path, filename)
                
                try:
                    with open(config_path, 'r', encoding='utf-8') as f:
                        config = yaml.safe_load(f)
                    
                    # 获取模型名称和令牌
                    actual_model_name = config.get('model', model_name)
                    api_key = config.get('api_key', '')
                    
                    if api_key:
                        # 将现有令牌添加到池中
                        colonel_blotto_token_pool.add_tokens(actual_model_name, [api_key])
                        print(f"已加载模型 {actual_model_name} 的现有令牌到上校博弈令牌池")
                        
                except Exception as e:
                    print(f"加载模型配置 {config_path} 失败: {e}")
    
    # 添加GPT5专用令牌（5个用于上校博弈）
    colonel_blotto_gpt5_tokens = [
        "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",
        "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",
        "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",
        "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",
        "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"
    ]
    
    # 为GPT5添加专用令牌
    colonel_blotto_token_pool.add_tokens("openai/gpt-5", colonel_blotto_gpt5_tokens)
    
    # 为其他模型添加剩余的令牌（3个）
    colonel_blotto_other_tokens = [
        "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",
        "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",
        "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"
    ]
    
    # 为其他高负载模型添加令牌
    colonel_blotto_token_pool.add_tokens("openai/gpt-4o-mini", colonel_blotto_other_tokens)
    colonel_blotto_token_pool.add_tokens("google/gemini-2.5-pro", colonel_blotto_other_tokens)
    colonel_blotto_token_pool.add_tokens("qwen/qwen3-max", colonel_blotto_other_tokens)
    colonel_blotto_token_pool.add_tokens("deepseek/deepseek-chat-v3.1", colonel_blotto_other_tokens)
    
    print("上校博弈令牌池初始化完成")
    colonel_blotto_token_pool.print_usage_stats()

def initialize_three_player_ipd_token_pools():
    """初始化3PIPD专用令牌池"""
    # 加载现有令牌
    model_pool_path = "model_pool"
    
    # 遍历所有模型池
    for pool_name in ["pool_A", "pool_B"]:
        pool_path = os.path.join(model_pool_path, pool_name, "api")
        if not os.path.exists(pool_path):
            continue
            
        for filename in os.listdir(pool_path):
            if filename.endswith('.yaml'):
                model_name = filename[:-5]  # 移除.yaml后缀
                config_path = os.path.join(pool_path, filename)
                
                try:
                    with open(config_path, 'r', encoding='utf-8') as f:
                        config = yaml.safe_load(f)
                    
                    # 获取模型名称和令牌
                    actual_model_name = config.get('model', model_name)
                    api_key = config.get('api_key', '')
                    
                    if api_key:
                        # 将现有令牌添加到池中
                        three_player_ipd_token_pool.add_tokens(actual_model_name, [api_key])
                        print(f"已加载模型 {actual_model_name} 的现有令牌到3PIPD令牌池")
                        
                except Exception as e:
                    print(f"加载模型配置 {config_path} 失败: {e}")
    
    # 添加GPT5专用令牌（5个用于3PIPD）
    three_player_ipd_gpt5_tokens = [
        "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",
        "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",
        "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",
        "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",
        "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"
    ]
    
    # 为GPT5添加专用令牌
    three_player_ipd_token_pool.add_tokens("openai/gpt-5", three_player_ipd_gpt5_tokens)
    
    # 为其他模型添加剩余的令牌（7个）
    three_player_ipd_other_tokens = [
        "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",
        "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",
        "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",
        "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",
        "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",
        "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",
        "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"
    ]
    
    # 为其他高负载模型添加令牌
    three_player_ipd_token_pool.add_tokens("openai/gpt-4o-mini", three_player_ipd_other_tokens)
    three_player_ipd_token_pool.add_tokens("google/gemini-2.5-pro", three_player_ipd_other_tokens)
    three_player_ipd_token_pool.add_tokens("qwen/qwen3-max", three_player_ipd_other_tokens)
    three_player_ipd_token_pool.add_tokens("deepseek/deepseek-chat-v3.1", three_player_ipd_other_tokens)
    
    print("3PIPD令牌池初始化完成")
    three_player_ipd_token_pool.print_usage_stats()

def get_colonel_blotto_model_token(model_name: str) -> Optional[str]:
    """获取上校博弈指定模型的令牌"""
    return colonel_blotto_token_pool.get_token(model_name)

def get_three_player_ipd_model_token(model_name: str) -> Optional[str]:
    """获取3PIPD指定模型的令牌"""
    return three_player_ipd_token_pool.get_token(model_name)

def get_colonel_blotto_model_config_with_token(model_name: str, original_config: Dict[str, Any]) -> Dict[str, Any]:
    """获取上校博弈带有动态令牌的模型配置"""
    # 复制原始配置
    config = original_config.copy()
    
    # 从令牌池获取令牌
    token = get_colonel_blotto_model_token(model_name)
    if token:
        print(f"DEBUG: [上校博弈] 为模型 {model_name} 从令牌池获取令牌: {token[:8]}...")
        config['api_key'] = token
    else:
        print(f"DEBUG: [上校博弈] 模型 {model_name} 未从令牌池获取令牌，使用原始令牌")
    
    return config

def get_three_player_ipd_model_config_with_token(model_name: str, original_config: Dict[str, Any]) -> Dict[str, Any]:
    """获取3PIPD带有动态令牌的模型配置"""
    # 复制原始配置
    config = original_config.copy()
    
    # 从令牌池获取令牌
    token = get_three_player_ipd_model_token(model_name)
    if token:
        print(f"DEBUG: [3PIPD] 为模型 {model_name} 从令牌池获取令牌: {token[:8]}...")
        config['api_key'] = token
    else:
        print(f"DEBUG: [3PIPD] 模型 {model_name} 未从令牌池获取令牌，使用原始令牌")
    
    return config

# 保持向后兼容性
def initialize_token_pools():
    """初始化所有令牌池（向后兼容）"""
    initialize_colonel_blotto_token_pools()
    initialize_three_player_ipd_token_pools()

def get_model_token(model_name: str) -> Optional[str]:
    """获取指定模型的令牌（向后兼容）"""
    return colonel_blotto_token_pool.get_token(model_name)

def get_model_config_with_token(model_name: str, original_config: Dict[str, Any]) -> Dict[str, Any]:
    """获取带有动态令牌的模型配置（向后兼容）"""
    return get_colonel_blotto_model_config_with_token(model_name, original_config)