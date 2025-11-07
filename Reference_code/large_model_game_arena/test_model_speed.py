#!/usr/bin/env python3
"""
测试模型池中各个模型的连接速度
"""
import os
import sys
import time
import yaml
import argparse
from datetime import datetime
import concurrent.futures
from typing import Dict, List, Tuple, Any

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agents.custom_openai_agent import CustomOpenAIAgent

def load_model_config(model_path: str) -> Dict[str, Any]:
    """加载模型配置文件"""
    try:
        with open(model_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except Exception as e:
        print(f"加载配置文件 {model_path} 失败: {e}")
        return {}

def test_model_connection(model_name: str, config: Dict[str, Any]) -> Tuple[str, float, bool, str]:
    """测试单个模型的连接速度"""
    try:
        # 创建agent实例
        agent = CustomOpenAIAgent(
            model_name=config.get('model', model_name),
            api_key=config.get('api_key', ''),
            api_base=config.get('api_base', 'https://api.openai.com/v1/chat/completions'),
            max_tokens=config.get('max_tokens', 100),
            temperature=config.get('temperature', 0.7),
            top_p=config.get('top_p', 0.9),
            frequency_penalty=config.get('frequency_penalty', 0),
            presence_penalty=config.get('presence_penalty', 0),
            extra_headers=config.get('extra_headers', {}),
            verbose=False,
            use_connection_pool=False,  # 测试时禁用连接池，确保每次都是新连接
            max_retries=1,  # 只尝试一次，不重试
            retry_delay=1
        )
        
        # 发送测试请求
        test_prompt = "请回复'连接测试成功'"
        start_time = time.time()
        response = agent(test_prompt)
        end_time = time.time()
        
        response_time = end_time - start_time
        success = True
        error_msg = ""
        
        return (model_name, response_time, success, error_msg)
        
    except Exception as e:
        return (model_name, float('inf'), False, str(e))

def test_models_sequentially(model_configs: Dict[str, Dict[str, Any]]) -> List[Tuple[str, float, bool, str]]:
    """顺序测试所有模型"""
    results = []
    print("开始顺序测试模型连接速度...")
    
    for model_name, config in model_configs.items():
        print(f"测试模型: {model_name}")
        result = test_model_connection(model_name, config)
        results.append(result)
        
        model_name, response_time, success, error_msg = result
        if success:
            print(f"  ✓ 连接成功，响应时间: {response_time:.2f}秒")
        else:
            print(f"  ✗ 连接失败: {error_msg}")
        
        # 添加短暂延迟，避免请求过于频繁
        time.sleep(1)
    
    return results

def test_models_parallel(model_configs: Dict[str, Dict[str, Any]], max_workers: int = 5) -> List[Tuple[str, float, bool, str]]:
    """并行测试所有模型"""
    results = []
    print(f"开始并行测试模型连接速度 (最大并发数: {max_workers})...")
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        # 提交所有测试任务
        future_to_model = {
            executor.submit(test_model_connection, model_name, config): model_name
            for model_name, config in model_configs.items()
        }
        
        # 收集结果
        for future in concurrent.futures.as_completed(future_to_model):
            model_name = future_to_model[future]
            try:
                result = future.result()
                results.append(result)
                
                model_name, response_time, success, error_msg = result
                if success:
                    print(f"  {model_name}: ✓ {response_time:.2f}秒")
                else:
                    print(f"  {model_name}: ✗ {error_msg}")
            except Exception as e:
                print(f"  {model_name}: 测试异常: {e}")
                results.append((model_name, float('inf'), False, str(e)))
    
    return results

def save_results_to_file(results: List[Tuple[str, float, bool, str]], output_file: str):
    """保存测试结果到文件"""
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("模型连接速度测试结果\n")
        f.write(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 60 + "\n\n")
        
        # 按响应时间排序
        sorted_results = sorted(results, key=lambda x: x[1] if x[1] != float('inf') else float('inf'))
        
        f.write("排名 | 模型名称 | 响应时间(秒) | 状态\n")
        f.write("-" * 60 + "\n")
        
        for i, (model_name, response_time, success, error_msg) in enumerate(sorted_results, 1):
            if success:
                f.write(f"{i:2d} | {model_name:<30} | {response_time:.2f} | 成功\n")
            else:
                f.write(f"{i:2d} | {model_name:<30} | N/A | 失败: {error_msg}\n")

def print_summary(results: List[Tuple[str, float, bool, str]]):
    """打印测试结果摘要"""
    print("\n" + "=" * 60)
    print("模型连接速度测试结果摘要")
    print("=" * 60)
    
    # 统计信息
    total_models = len(results)
    successful_models = sum(1 for _, _, success, _ in results if success)
    failed_models = total_models - successful_models
    
    print(f"总模型数: {total_models}")
    print(f"成功连接: {successful_models}")
    print(f"连接失败: {failed_models}")
    
    if successful_models > 0:
        # 按响应时间排序
        sorted_results = sorted([r for r in results if r[2]], key=lambda x: x[1])
        
        print("\n最快的5个模型:")
        for i, (model_name, response_time, _, _) in enumerate(sorted_results[:5], 1):
            print(f"{i}. {model_name}: {response_time:.2f}秒")
        
        print("\n最慢的5个模型:")
        for i, (model_name, response_time, _, _) in enumerate(sorted_results[-5:], successful_models-4):
            print(f"{i}. {model_name}: {response_time:.2f}秒")
        
        avg_time = sum(r[1] for r in results if r[2]) / successful_models
        print(f"\n平均响应时间: {avg_time:.2f}秒")
    
    print("\n失败的模型:")
    for model_name, _, _, error_msg in results:
        if not _:
            print(f"- {model_name}: {error_msg}")

def main():
    parser = argparse.ArgumentParser(description="测试模型池中各个模型的连接速度")
    parser.add_argument("--pool", type=str, default="pool_B", 
                       help="要测试的模型池 (默认: pool_B)")
    parser.add_argument("--parallel", action="store_true",
                       help="使用并行测试")
    parser.add_argument("--max_workers", type=int, default=5,
                       help="并行测试时的最大并发数 (默认: 5)")
    parser.add_argument("--output", type=str, default="model_speed_test_results.txt",
                       help="结果输出文件名 (默认: model_speed_test_results.txt)")
    
    args = parser.parse_args()
    
    # 构建模型池路径
    pool_path = os.path.join("model_pool", args.pool, "api")
    
    if not os.path.exists(pool_path):
        print(f"错误: 模型池路径 {pool_path} 不存在")
        return
    
    # 加载所有模型配置
    model_configs = {}
    for filename in os.listdir(pool_path):
        if filename.endswith('.yaml'):
            model_name = filename[:-5]  # 移除.yaml后缀
            config_path = os.path.join(pool_path, filename)
            config = load_model_config(config_path)
            if config:
                model_configs[model_name] = config
    
    if not model_configs:
        print(f"错误: 在 {pool_path} 中没有找到有效的模型配置文件")
        return
    
    print(f"找到 {len(model_configs)} 个模型配置")
    
    # 执行测试
    if args.parallel:
        results = test_models_parallel(model_configs, args.max_workers)
    else:
        results = test_models_sequentially(model_configs)
    
    # 保存结果
    save_results_to_file(results, args.output)
    print(f"\n详细结果已保存到: {args.output}")
    
    # 打印摘要
    print_summary(results)

if __name__ == "__main__":
    main()