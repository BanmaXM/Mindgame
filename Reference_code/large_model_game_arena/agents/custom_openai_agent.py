import os
import sys
import time
import logging
import threading
from typing import Optional, Dict, Any

# 添加项目路径，以便导入src中的模块
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from textarena.core import Agent

# 导入令牌池
try:
    from token_pool import (
        get_model_config_with_token, 
        initialize_token_pools,
        get_colonel_blotto_model_config_with_token,
        get_three_player_ipd_model_config_with_token,
        initialize_colonel_blotto_token_pools,
        initialize_three_player_ipd_token_pools
    )
    TOKEN_POOL_AVAILABLE = True
except ImportError:
    TOKEN_POOL_AVAILABLE = False
    print("Warning: token_pool module not found. Token pooling will be disabled.")

# 全局连接池字典，每个API端点一个连接池
_connection_pools = {}
_pool_lock = threading.Lock()

class CustomOpenAIAgent(Agent):
    """自定义的OpenAI兼容Agent，支持任意API端点"""
    
    def __init__(
        self,
        model_name: str,
        api_key: str,
        api_base: str = "https://api.openai.com/v1/chat/completions",
        system_prompt: Optional[str] = "You are a competitive game player. Make sure you read the game instructions carefully, and always follow the required format.",
        verbose: bool = False,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        top_p: float = 0.9,
        frequency_penalty: float = 0,
        presence_penalty: float = 0,
        extra_headers: Optional[Dict[str, str]] = None,
        max_retries: int = 3,
        retry_delay: int = 5,
        stream: bool = False,
        use_connection_pool: bool = True,
        use_token_pool: bool = True,
        token_pool_type: str = "colonel_blotto",  # 新增参数，可选值: "colonel_blotto", "three_player_ipd", "default"
        **kwargs
    ) -> None:
        super().__init__()
        
        # 如果启用了令牌池，尝试从令牌池获取令牌
        if TOKEN_POOL_AVAILABLE and use_token_pool:
            print(f"DEBUG: 令牌池可用且已启用，正在初始化{token_pool_type}令牌池...")
            
            # 根据令牌池类型初始化相应的令牌池
            if token_pool_type == "colonel_blotto":
                initialize_colonel_blotto_token_pools()
            elif token_pool_type == "three_player_ipd":
                initialize_three_player_ipd_token_pools()
            else:  # default或其他值
                initialize_token_pools()
            
            # 创建原始配置字典
            original_config = {
                'model': model_name,
                'api_key': api_key,
                'api_base': api_base,
                'max_tokens': max_tokens,
                'temperature': temperature,
                'top_p': top_p,
                'frequency_penalty': frequency_penalty,
                'presence_penalty': presence_penalty,
                'extra_headers': extra_headers or {}
            }
            
            # 根据令牌池类型从相应的令牌池获取带有动态令牌的配置
            if token_pool_type == "colonel_blotto":
                config = get_colonel_blotto_model_config_with_token(model_name, original_config)
            elif token_pool_type == "three_player_ipd":
                config = get_three_player_ipd_model_config_with_token(model_name, original_config)
            else:  # default或其他值
                config = get_model_config_with_token(model_name, original_config)
            
            # 使用令牌池提供的配置
            self.model_name = config.get('model', model_name)
            self.api_key = config.get('api_key', api_key)
            self.api_base = config.get('api_base', api_base)
            self.max_tokens = config.get('max_tokens', max_tokens)
            self.temperature = config.get('temperature', temperature)
            self.top_p = config.get('top_p', top_p)
            self.frequency_penalty = config.get('frequency_penalty', frequency_penalty)
            self.presence_penalty = config.get('presence_penalty', presence_penalty)
            self.extra_headers = config.get('extra_headers', extra_headers or {})
        else:
            print(f"DEBUG: 令牌池不可用或已禁用，TOKEN_POOL_AVAILABLE={TOKEN_POOL_AVAILABLE}, use_token_pool={use_token_pool}")
            # 不使用令牌池，直接使用提供的参数
            self.model_name = model_name
            self.api_key = api_key
            self.api_base = api_base
            self.max_tokens = max_tokens
            self.temperature = temperature
            self.top_p = top_p
            self.frequency_penalty = frequency_penalty
            self.presence_penalty = presence_penalty
            self.extra_headers = extra_headers or {}
        
        self.system_prompt = system_prompt or ""
        self.verbose = verbose
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.stream = stream
        self.use_connection_pool = use_connection_pool
        self.use_token_pool = use_token_pool
        self.token_pool_type = token_pool_type
        self.kwargs = kwargs
        
        try:
            from openai import OpenAI
        except Exception as exc:
            raise ImportError(
                "OpenAI package is required for CustomOpenAIAgent. Install it with: pip install openai"
            ) from exc
        
        # 处理API基础URL，确保不包含重复的路径
        # 如果api_base已经包含了/chat/completions，我们需要移除它
        base_url = api_base
        if base_url.endswith('/chat/completions'):
            base_url = base_url[:-16]  # 移除'/chat/completions'
        elif base_url.endswith('/v1/chat/completions'):
            base_url = base_url[:-19]  # 移除'/v1/chat/completions'
        
        # 创建或获取连接池
        if self.use_connection_pool:
            pool_key = f"{model_name}_{base_url}"  # 使用模型名称而不是API密钥作为键
            with _pool_lock:
                if pool_key not in _connection_pools:
                    _connection_pools[pool_key] = OpenAI(
                        api_key=self.api_key,  # 使用当前API密钥
                        base_url=base_url, 
                        default_headers=self.extra_headers,
                        # 设置连接池相关参数
                        http_client=None  # 使用默认的httpx客户端
                    )
                    if self.verbose:
                        print(f"Created new connection pool for {model_name} at {base_url}")
                else:
                    # 如果连接池已存在，更新API密钥
                    _connection_pools[pool_key].api_key = self.api_key
                self.client = _connection_pools[pool_key]
        else:
            self.client = OpenAI(api_key=api_key, base_url=base_url, default_headers=self.extra_headers)
        
        if self.verbose:
            print(f"Initialized CustomOpenAIAgent with model: {model_name}")
            print(f"API Base: {api_base}")
            print(f"Connection pool: {'Enabled' if self.use_connection_pool else 'Disabled'}")
    
    def _make_request(self, observation: str) -> str:
        """发送请求到API"""
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": observation}
        ]
        
        # 准备请求参数，只包含基本必需的参数
        request_kwargs = {
            "model": self.model_name,
            "messages": messages,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "stream": self.stream,
        }
        
        # 添加可选参数，如果它们不是默认值
        if self.top_p != 0.9:
            request_kwargs["top_p"] = self.top_p
        if self.frequency_penalty != 0:
            request_kwargs["frequency_penalty"] = self.frequency_penalty
        if self.presence_penalty != 0:
            request_kwargs["presence_penalty"] = self.presence_penalty
        
        # 添加额外头部信息（如果存在）
        if self.extra_headers:
            request_kwargs["extra_headers"] = self.extra_headers
        
        # 添加其他自定义参数
        request_kwargs.update(self.kwargs)
        
        try:
            completion = self.client.chat.completions.create(**request_kwargs)
            
            # 处理流式响应
            if self.stream:
                content = ""
                for chunk in completion:
                    if chunk.choices[0].delta.content is not None:
                        content += chunk.choices[0].delta.content
                return content.strip()
            else:
                return completion.choices[0].message.content.strip()
        except Exception as e:
            # 如果参数不被支持，尝试使用基本参数
            if "is not supported" in str(e) or "unsupported_parameter" in str(e):
                basic_kwargs = {
                    "model": self.model_name,
                    "messages": messages,
                    "max_tokens": self.max_tokens,
                    "temperature": self.temperature,
                    "stream": self.stream,
                }
                completion = self.client.chat.completions.create(**basic_kwargs)
                
                # 处理流式响应
                if self.stream:
                    content = ""
                    for chunk in completion:
                        if chunk.choices[0].delta.content is not None:
                            content += chunk.choices[0].delta.content
                    return content.strip()
                else:
                    return completion.choices[0].message.content.strip()
            else:
                # 其他错误直接抛出
                raise e
    
    def _retry_request(self, observation: str, retries: int = None, delay: int = None) -> str:
        """带重试的请求"""
        # 使用自定义参数或默认参数
        if retries is None:
            retries = self.max_retries
        if delay is None:
            delay = self.retry_delay
            
        last_exception = None
        
        for attempt in range(1, retries + 1):
            try:
                response = self._make_request(observation)
                if self.verbose:
                    print(f"\nObservation: {observation[:100]}...\nResponse: {response[:100]}...")
                return response
            except Exception as exc:
                last_exception = exc
                if self.verbose:
                    print(f"Attempt {attempt} failed with error: {exc}")
                if attempt < retries:
                    if self.verbose:
                        print(f"Retrying in {delay} seconds...")
                    time.sleep(delay)
                else:
                    if self.verbose:
                        print(f"All {retries} attempts failed. Using fallback.")
                    break
        
        # 如果所有重试都失败，返回错误信息
        if last_exception:
            return f"I apologize, but I'm having technical difficulties (Error: {last_exception}). Please proceed with the game."
        else:
            raise RuntimeError("Unexpected error: no exception recorded but retries exhausted.")
    
    def __call__(self, observation: str) -> str:
        """处理观察信息并生成响应"""
        if not isinstance(observation, str):
            raise ValueError(f"Observation must be a string. Received type: {type(observation)}")
        
        if self.verbose:
            print(f"CustomOpenAIAgent ({self.model_name}) processing observation: {observation[:100]}...")
        
        response = self._retry_request(observation)
        
        if self.verbose:
            print(f"CustomOpenAIAgent response: {response[:100]}...")
        
        return response