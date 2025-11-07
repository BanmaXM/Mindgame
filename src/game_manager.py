import textarena as ta
from typing import Dict, List, Optional, Union, Tuple, Any
import os
import sys
import logging
from agent import Agent, HumanAgent, LLMAgent, OpenAIAgent

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class GameManager:
    """
    游戏管理器类，用于统一管理四种不同的游戏环境
    支持人类与LLM代理的对战
    """
    
    # 支持的游戏环境
    SUPPORTED_GAMES = {
        "secret_mafia": "SecretMafia-v0",
        "three_player_ipd": "ThreePlayerIPD-v0",
        "colonel_blotto": "ColonelBlotto-v0",
        "codenames": "Codenames-v0"
    }
    
    # 每个游戏需要的玩家数量
    GAME_PLAYER_COUNT = {
        "SecretMafia-v0": 7,
        "ThreePlayerIPD-v0": 3,
        "ColonelBlotto-v0": 2,
        "Codenames-v0": 4
    }
    
    def __init__(self):
        """初始化游戏管理器"""
        self.env = None
        self.game_name = None
        self.agents = {}
        self.human_player_ids = []
        self.llm_player_ids = []
    
    def list_available_games(self) -> List[str]:
        """列出所有可用的游戏"""
        return list(self.SUPPORTED_GAMES.keys())
    
    def _validate_game_name(self, game_name: str) -> str:
        """验证并返回规范化的游戏名称"""
        if game_name in self.SUPPORTED_GAMES:
            return self.SUPPORTED_GAMES[game_name]
        elif game_name in self.SUPPORTED_GAMES.values():
            return game_name
        else:
            raise ValueError(f"不支持的游戏: {game_name}. 支持的游戏有: {', '.join(self.SUPPORTED_GAMES.keys())}")
    
    def setup_game(self, game_name: str, seed: Optional[int] = None) -> str:
        """
        设置游戏环境
        
        Args:
            game_name: 游戏名称
            seed: 随机种子
        
        Returns:
            规范化的游戏名称
        """
        self.game_name = self._validate_game_name(game_name)
        logger.info(f"设置游戏环境: {self.game_name}")
        
        # 创建环境
        self.env = ta.make(self.game_name)
        
        # 清空代理列表
        self.agents = {}
        self.human_player_ids = []
        self.llm_player_ids = []
        
        return self.game_name
    
    def add_human_player(self, player_id: Optional[int] = None) -> int:
        """
        添加人类玩家
        
        Args:
            player_id: 可选的玩家ID，如果未提供，将分配下一个可用ID
            
        Returns:
            分配的玩家ID
        """
        # 创建人类代理
        agent = HumanAgent()
        
        # 使用通用的add_agent方法添加
        return self.add_agent(agent, player_id)
    
    def add_agent(self, agent: Agent, player_id: Optional[int] = None) -> int:
        """
        添加任意类型的代理玩家
        
        Args:
            agent: 代理实例，必须是Agent类的子类
            player_id: 可选的玩家ID，如果未提供，将分配下一个可用ID
        
        Returns:
            分配的玩家ID
        """
        if self.env is None:
            raise RuntimeError("请先使用setup_game()设置游戏环境")
        
        # if not isinstance(agent, Agent):
        #     raise TypeError("添加的代理必须是 Agent 类型")
        
        if player_id is None:
            # 分配下一个可用ID
            player_id = self._get_next_available_id()
        
        # 检查ID是否已被使用
        if player_id in self.agents:
            raise ValueError(f"玩家ID {player_id} 已被使用")
        
        # 添加代理玩家
        self.agents[player_id] = agent
        
        # 根据代理类型分类
        if isinstance(agent, HumanAgent):
            self.human_player_ids.append(player_id)
            logger.info(f"添加人类玩家，ID: {player_id}")
        elif isinstance(agent, OpenAIAgent):
            self.llm_player_ids.append(player_id)
            logger.info(f"添加OpenAI玩家，ID: {player_id}，模型: {agent.__class__.__name__}")
        elif isinstance(agent, LLMAgent):
            self.llm_player_ids.append(player_id)
            logger.info(f"添加LLM玩家，ID: {player_id}，模型: {agent.__class__.__name__}")
        else:
            self.llm_player_ids.append(player_id)  # 默认将其他代理视为LLM
            logger.info(f"添加代理玩家，ID: {player_id}，类型: {agent.__class__.__name__}")
        
        return player_id
    
    def add_llm_player(self, model_name: str, player_id: Optional[int] = None, 
                       device: str = "auto", quantize: bool = False, 
                       max_new_tokens: int = 1024, hf_kwargs: dict = None) -> int:
        """
        添加LLM玩家
        
        Args:
            model_name: 模型名称
            player_id: 可选的玩家ID，如果未提供，将分配下一个可用ID
            device: 设备，例如"cuda:0"或"cpu"
            quantize: 是否量化模型
            max_new_tokens: 生成的最大token数
            hf_kwargs: 传递给HuggingFace的额外参数
            
        Returns:
            分配的玩家ID
        """
        # 创建LLM代理
        # agent = LLMAgent(
        #     model_name=model_name, 
        #     device=device, 
        #     quantize=quantize, 
        #     max_new_tokens=max_new_tokens,
        #     hf_kwargs=hf_kwargs or {}
        # )
        agent = OpenAIAgent(
            model_name=model_name, 
        )
        
        # 使用通用的add_agent方法添加
        return self.add_agent(agent, player_id)
    
    def _get_next_available_id(self) -> int:
        """获取下一个可用的玩家ID"""
        if not self.agents:
            return 0
        return max(self.agents.keys()) + 1
    
    def _validate_player_count(self) -> bool:
        """验证玩家数量是否符合游戏要求"""
        required_count = self.GAME_PLAYER_COUNT.get(self.game_name)
        actual_count = len(self.agents)
        
        if required_count != actual_count:
            logger.warning(f"游戏 {self.game_name} 需要 {required_count} 名玩家，当前有 {actual_count} 名")
            return False
        return True
    
    def start_game(self, seed: Optional[int] = None) -> Dict[str, Any]:
        """
        开始游戏，返回初始状态
        
        Args:
            seed: 随机种子
            
        Returns:
            游戏初始状态信息
        """
        if self.env is None:
            raise RuntimeError("请先使用setup_game()设置游戏环境")
        
        if not self._validate_player_count():
            raise ValueError(f"玩家数量不符合游戏要求")
            
        # 重置环境
        num_players = len(self.agents)
        obs = self.env.reset(num_players=num_players, seed=seed)
        
        logger.info(f"游戏 {self.game_name} 已开始，玩家数量: {num_players}")
        return {"status": "started", "num_players": num_players, "initial_observation": obs}
    
    def play_game(self, max_steps: int = 1000, callbacks: Dict[str, callable] = None) -> Dict[str, Any]:
        """
        运行完整的游戏过程
        
        Args:
            max_steps: 最大步数，防止无限循环
            callbacks: 回调函数字典，包含以下可选回调:
                - on_observation(player_id, observation): 当玩家收到观察时调用
                - on_action(player_id, action): 当玩家执行动作时调用
                - on_step_complete(done, info): 当一步完成时调用
            
        Returns:
            游戏结果
        """
        if self.env is None:
            raise RuntimeError("请先使用setup_game()设置游戏环境")
        
        if callbacks is None:
            callbacks = {}
        
        step_count = 0
        game_over = False
        
        while not game_over and step_count < max_steps:
            player_id, observation = self.env.get_observation()
            
            # 回调：观察
            if 'on_observation' in callbacks:
                callbacks['on_observation'](player_id, observation)
            
            # 获取当前玩家的代理
            if player_id not in self.agents:
                raise RuntimeError(f"找不到ID为 {player_id} 的玩家代理")
                
            agent = self.agents[player_id]
            
            # 代理生成动作
            action = agent(observation)
            
            # 回调：动作
            if 'on_action' in callbacks:
                callbacks['on_action'](player_id, action)
            
            # 执行动作
            game_over, step_info = self.env.step(action=action)
            
            # 回调：步骤完成
            if 'on_step_complete' in callbacks:
                callbacks['on_step_complete'](game_over, step_info)
                
            step_count += 1
        
        # 游戏结束，获取奖励
        rewards, game_info = self.env.close()
        
        result = {
            "status": "completed" if step_count < max_steps else "max_steps_reached",
            "steps": step_count,
            "rewards": rewards,
            "game_info": game_info,
            "human_players": self.human_player_ids,
            "llm_players": self.llm_player_ids
        }
        
        logger.info(f"游戏结束，总步数: {step_count}")
        return result
    
    def get_required_players(self) -> int:
        """获取当前游戏需要的玩家数量"""
        if self.game_name is None:
            raise RuntimeError("请先使用setup_game()设置游戏环境")
        return self.GAME_PLAYER_COUNT.get(self.game_name)
    
    def get_current_players(self) -> Dict[str, List[int]]:
        """获取当前已设置的玩家"""
        return {
            "human_players": self.human_player_ids,
            "llm_players": self.llm_player_ids,
            "total": list(self.agents.keys())
        }
