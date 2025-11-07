import os
import sys
import random
import yaml
from typing import Dict, Any, List
from .base_agent import BaseAgent

# 添加项目路径，以便导入src中的模块
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class Agent0(BaseAgent):
    """
    我们的Agent，从A池选择模型和Prompt
    """
    
    def __init__(self, game_type: str = "colonel_blotto", model_name: str = None, prompt_name: str = None, token_pool_type: str = "colonel_blotto"):
        super().__init__()
        self.game_type = game_type
        self.model_name = model_name
        self.prompt_name = prompt_name
        self.token_pool_type = token_pool_type
        self.model_config = None
        self.prompt = None
        self.agent_instance = None
        
        # 初始化模型和提示
        self._initialize_model_and_prompt()
    
    def _initialize_model_and_prompt(self):
        """初始化模型和提示"""
        # 如果没有指定模型，从A池随机选择一个
        if not self.model_name:
            self.model_name = self._random_select_model_from_pool("A")
        
        # 如果没有指定提示，从A池随机选择一个
        if not self.prompt_name:
            self.prompt_name = self._random_select_prompt_from_pool("A")
        
        # 加载模型配置
        self.model_config = self._load_model_config("A", self.model_name)
        
        # 加载提示
        self.prompt = self._load_prompt("A", self.prompt_name)
        
        # 创建agent实例
        self.agent_instance = self._create_agent_instance()
    
    def _random_select_model_from_pool(self, pool: str) -> str:
        """从指定池中随机选择一个模型"""
        pool_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "model_pool", f"pool_{pool}")
        
        # 收集所有可用的模型
        available_models = []
        
        # 检查API模型
        api_dir = os.path.join(pool_dir, "api")
        if os.path.exists(api_dir):
            for file in os.listdir(api_dir):
                if file.endswith(".yaml"):
                    available_models.append(f"api/{file[:-5]}")  # 去掉.yaml后缀
        
        # 检查本地模型
        local_dir = os.path.join(pool_dir, "local")
        if os.path.exists(local_dir):
            for file in os.listdir(local_dir):
                if file.endswith(".py"):
                    available_models.append(f"local/{file[:-3]}")  # 去掉.py后缀
        
        if not available_models:
            raise ValueError(f"No models found in pool {pool}")
        
        return random.choice(available_models)
    
    def _random_select_prompt_from_pool(self, pool: str) -> str:
        """从指定池中随机选择一个提示"""
        pool_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "prompt_pool", self.game_type, f"pool_{pool}")
        
        if not os.path.exists(pool_dir):
            raise ValueError(f"Prompt pool directory not found: {pool_dir}")
        
        # 收集所有可用的提示
        available_prompts = []
        for file in os.listdir(pool_dir):
            if file.endswith(".txt"):
                available_prompts.append(file[:-4])  # 去掉.txt后缀
        
        if not available_prompts:
            raise ValueError(f"No prompts found in pool {pool} for game {self.game_type}")
        
        return random.choice(available_prompts)
    
    def _load_model_config(self, pool: str, model_name: str) -> Dict[str, Any]:
        """加载模型配置"""
        model_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "model_pool", f"pool_{pool}", f"{model_name}.yaml")
        
        if not os.path.exists(model_path):
            # 尝试添加.py后缀（本地模型）
            model_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "model_pool", f"pool_{pool}", f"{model_name}.py")
        
        if not os.path.exists(model_path):
            raise ValueError(f"Model config not found: {model_name}")
        
        with open(model_path, 'r', encoding='utf-8') as f:
            if model_path.endswith('.yaml'):
                config = yaml.safe_load(f)
            else:
                # 对于.py文件，我们需要执行它来获取配置
                exec_globals = {}
                exec(f.read(), exec_globals)
                # 提取配置变量，排除内置变量和函数
                config = {}
                for key, value in exec_globals.items():
                    if not key.startswith('__') and not callable(value) and not isinstance(value, type):
                        config[key] = value
        
        return config
    
    def _load_prompt(self, pool: str, prompt_name: str) -> str:
        """加载提示"""
        prompt_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "prompt_pool", self.game_type, f"pool_{pool}", f"{prompt_name}.txt")
        
        if not os.path.exists(prompt_path):
            raise ValueError(f"Prompt not found: {prompt_name}")
        
        with open(prompt_path, 'r', encoding='utf-8') as f:
            prompt = f.read()
        
        return prompt
    
    def _create_agent_instance(self):
        """创建agent实例"""
        # 根据模型类型创建不同的agent
        if self.model_name.startswith("api/"):
            # API模型
            from .custom_openai_agent import CustomOpenAIAgent
            
            # 提取API配置
            api_config = self.model_config
            
            # 创建API agent
            agent = CustomOpenAIAgent(
                model_name=api_config.get("model", "gpt-3.5-turbo"),
                api_key=api_config.get("api_key", ""),
                api_base=api_config.get("api_base", "https://api.openai.com/v1/chat/completions"),
                system_prompt=self.prompt,
                verbose=True,
                max_tokens=api_config.get("max_tokens", 4096),
                temperature=api_config.get("temperature", 0.7),
                top_p=api_config.get("top_p", 0.9),
                frequency_penalty=api_config.get("frequency_penalty", 0),
                presence_penalty=api_config.get("presence_penalty", 0),
                extra_headers=api_config.get("extra_headers", {}),
                use_token_pool=True,  # 启用令牌池
                token_pool_type=self.token_pool_type  # 指定令牌池类型
            )
        else:
            # 本地模型
            from src.agents.local_qwen_agent_2 import LocalQwenAgent
            
            # 提取本地模型配置
            model_config = self.model_config
            
            # 创建本地agent
            agent = LocalQwenAgent(
                model_path=model_config.get("model_path", "/home/syh/mindgames/Qwen3-8B_modelscope/qwen/Qwen3-8B"),
                max_new_tokens=model_config.get("max_new_tokens", 4096),
                temperature=model_config.get("temperature", 0.7),
                device=model_config.get("device", "auto"),
                verbose=True
            )
        
        # 设置提示
        if hasattr(agent, 'system_prompt'):
            agent.system_prompt = self.prompt
        
        return agent
    
    def __call__(self, observation: str) -> str:
        """
        处理观察信息并生成动作
        
        Args:
            observation: 观察信息
            
        Returns:
            动作字符串
        """
        return self.agent_instance(observation)
    
    def get_model_info(self) -> Dict[str, Any]:
        """获取模型信息"""
        # 确保config可以被JSON序列化
        config = self.model_config.copy() if self.model_config else {}
        
        # 处理可能的非序列化对象
        if isinstance(config, dict):
            # 移除可能存在的函数或类对象
            keys_to_remove = []
            for key, value in config.items():
                if callable(value) or isinstance(value, type):
                    keys_to_remove.append(key)
            
            for key in keys_to_remove:
                config.pop(key, None)
        
        return {
            "model_name": self.model_name,
            "prompt_name": self.prompt_name,
            "game_type": self.game_type,
            "config": config
        }