from typing import Dict, List, Optional, Tuple, Any, Union
import importlib
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class GameManager:
    """
    游戏管理器类，用于统一管理四种不同的游戏环境
    支持人类与LLM代理的对战
    """
    
    # 受支持的本地游戏键名（统一内部使用小写短名）
    SUPPORTED_GAMES = {
        "secret_mafia",
        "three_player_ipd",
        "colonel_blotto",
        "codenames",
    }

    # 兼容旧的 textarena 环境 ID 到内部键名的映射
    _ALIASES = {
        "SecretMafia-v0": "secret_mafia",
        "ThreePlayerIPD-v0": "three_player_ipd",
        "ColonelBlotto-v0": "colonel_blotto",
        "Codenames-v0": "codenames",
    }

    # 本地环境类注册信息：模块路径与类名
    _ENV_REGISTRY: Dict[str, Tuple[str, str]] = {
        "secret_mafia": ("expansion_envs.SecretMafia.env", "SecretMafiaEnv"),
        "three_player_ipd": ("expansion_envs.ThreePlayerIPD.env", "ThreePlayerIPDEnv"),
        "colonel_blotto": ("expansion_envs.ColonelBlotto.env", "ColonelBlottoEnv"),
        "codenames": ("expansion_envs.Codenames.env", "CodenamesEnv"),
    }

    # 玩家人数规则：可以是精确人数 int，或区间 (min, max)
    GAME_PLAYER_COUNT: Dict[str, Union[int, Tuple[int, int]]] = {
        "secret_mafia": (6, 15),       # SecretMafia 允许 6-15 人（与 env 中断言一致）
        "three_player_ipd": 3,
        "colonel_blotto": 2,
        "codenames": 4,
    }
    
    def __init__(self):
        """初始化游戏管理器"""
        self.env = None
        self.game_name: Optional[str] = None  # 统一为内部键名
        self.agents = {}
        self.human_player_ids = []
        self.llm_player_ids = []
    
    def list_available_games(self) -> List[str]:
        """列出所有可用的游戏（内部键名）"""
        return sorted(list(self.SUPPORTED_GAMES))
    
    def _normalize_game_name(self, game_name: str) -> str:
        """将传入的游戏名（短名或旧 ID）规范化为内部键名。"""
        if game_name in self.SUPPORTED_GAMES:
            return game_name
        if game_name in self._ALIASES:
            return self._ALIASES[game_name]
        raise ValueError(
            f"不支持的游戏: {game_name}. 支持的游戏有: {', '.join(sorted(self.SUPPORTED_GAMES))} 或 {'/'.join(self._ALIASES.keys())}"
        )
    
    def setup_game(self, game_name: str, seed: Optional[int] = None, env_config: Optional[Dict[str, Any]] = None) -> str:
        """
        设置游戏环境
        
        Args:
            game_name: 游戏名称
            seed: 随机种子
            env_config: 传递给本地 Env 构造函数的自定义参数（字典）
        
        Returns:
            规范化的游戏名称
        """
        env_key = self._normalize_game_name(game_name)
        self.game_name = env_key
        logger.info(f"设置游戏环境(本地): {env_key}")

        # 动态导入并实例化本地环境类
        module_path, class_name = self._ENV_REGISTRY[env_key]
        module = importlib.import_module(module_path)
        env_cls = getattr(module, class_name)
        cfg = env_config or {}
        try:
            self.env = env_cls(**cfg)
        except TypeError as e:
            # 当入参不匹配时给出更友好的错误
            raise TypeError(f"实例化环境 {class_name} 失败，检查 env_config 是否包含无效参数: {cfg}") from e
        
        # 清空代理列表
        self.agents = {}
        self.human_player_ids = []
        self.llm_player_ids = []
        
        return env_key
    
    def add_human_player(self, player_id: Optional[int] = None) -> int:
        """
        添加人类玩家
        
        Args:
            player_id: 可选的玩家ID，如果未提供，将分配下一个可用ID
            
        Returns:
            分配的玩家ID
        """
        # 简化：不强制依赖具体 HumanAgent 类型，使用 duck typing。
        # 这里创建一个最简单的人类占位代理，后续可替换为自定义实现。
        class _HumanAgent:
            def __call__(self, observation: str) -> str:
                # 人类玩家可在外层通过自定义回调接管，这里提供占位返回
                return "[pass]"

        agent = _HumanAgent()
        
        # 使用通用的add_agent方法添加
        return self.add_agent(agent, player_id)
    
    def add_agent(self, agent: Any, player_id: Optional[int] = None) -> int:
        """
        添加任意类型的代理玩家
        
        Args:
            agent: 代理实例，需实现 __call__(observation: str) -> str
            player_id: 可选的玩家ID，如果未提供，将分配下一个可用ID
        
        Returns:
            分配的玩家ID
        """
        if self.env is None:
            raise RuntimeError("请先使用setup_game()设置游戏环境")
        
        # 采用 duck typing：仅验证可调用性
        if not callable(getattr(agent, "__call__", None)):
            raise TypeError("添加的代理必须实现 __call__(observation: str) -> str 接口")
        
        if player_id is None:
            # 分配下一个可用ID
            player_id = self._get_next_available_id()
        
        # 检查ID是否已被使用
        if player_id in self.agents:
            raise ValueError(f"玩家ID {player_id} 已被使用")
        
        # 添加代理玩家
        self.agents[player_id] = agent
        
        # 分类（尽量不依赖具体类）：如果有 is_human 属性则按其分类，否则默认 LLM/自动代理
        if getattr(agent, "is_human", False):
            self.human_player_ids.append(player_id)
            logger.info(f"添加人类玩家，ID: {player_id}")
        else:
            self.llm_player_ids.append(player_id)
            logger.info(f"添加代理玩家，ID: {player_id}，类型: {agent.__class__.__name__}")
        
        return player_id
    
    def add_llm_player(self, *args, **kwargs) -> int:
        """
        添加 LLM 玩家（占位接口）。

        为避免引入特定 LLM 实现依赖（如 transformers 或某 API SDK），此方法不再直接构造模型，
        请改用 `add_agent(your_agent_instance)` 传入自定义实现。
        """
        raise NotImplementedError(
            "请直接构造代理实例并调用 add_agent(agent, player_id)。例如：manager.add_agent(MyLLMAgent(...))."
        )
    
    def _get_next_available_id(self) -> int:
        """获取下一个可用的玩家ID"""
        if not self.agents:
            return 0
        return max(self.agents.keys()) + 1
    
    def _validate_player_count(self) -> bool:
        """验证玩家数量是否符合游戏要求"""
        rule = self.GAME_PLAYER_COUNT.get(self.game_name)
        actual = len(self.agents)

        if isinstance(rule, int):
            ok = (actual == rule)
            if not ok:
                logger.warning(f"游戏 {self.game_name} 需要 {rule} 名玩家，当前有 {actual} 名")
            return ok
        elif isinstance(rule, tuple) and len(rule) == 2:
            min_p, max_p = rule
            ok = (min_p <= actual <= max_p)
            if not ok:
                logger.warning(f"游戏 {self.game_name} 需要玩家数在区间 [{min_p}, {max_p}]，当前有 {actual} 名")
            return ok
        else:
            # 未配置规则，放行
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
        # 按玩家累计观察文本，确保传递给代理与回调的是历史完整观察
        obs_history: Dict[int, str] = {}
        
        def _stringify_observation(obs: Any) -> str:
            try:
                # 结构化列表/元组：形如 [(pid, text, ObservationType.X), ...]
                if isinstance(obs, (list, tuple)):
                    role_map = getattr(self.env.state, "role_mapping", {})
                    parts: List[str] = []
                    for item in obs:
                        if isinstance(item, (list, tuple)):
                            pid = None
                            msg = None
                            typ = None
                            if len(item) >= 1:
                                pid = item[0]
                            if len(item) >= 2 and isinstance(item[1], str):
                                msg = item[1]
                            if len(item) >= 3:
                                typ = str(item[2])
                            if msg is None:
                                continue
                            if typ and "PLAYER_ACTION" in typ:
                                role = role_map.get(pid, f"Player {pid}")
                                parts.append(f"[{role}]")
                                parts.append(msg)
                            else:
                                parts.append(msg)
                        elif isinstance(item, str):
                            parts.append(item)
                    if parts:
                        return "\n".join(parts)
                # 已是字符串，直接返回
                return obs if isinstance(obs, str) else str(obs)
            except Exception:
                return str(obs)

        while not game_over and step_count < max_steps:
            player_id, observation = self.env.get_observation()
            # 统一字符串化与历史累积
            s = _stringify_observation(observation)
            prev = obs_history.get(player_id)
            if prev is None:
                combined_obs = s
            else:
                if s.startswith(prev) or (prev in s):
                    combined_obs = s
                elif prev.startswith(s) or (s in prev):
                    combined_obs = prev
                else:
                    combined_obs = prev + "\n" + s
            obs_history[player_id] = combined_obs
            
            # 回调：观察
            if 'on_observation' in callbacks:
                callbacks['on_observation'](player_id, combined_obs)
            
            # 获取当前玩家的代理
            if player_id not in self.agents:
                raise RuntimeError(f"找不到ID为 {player_id} 的玩家代理")
                
            agent = self.agents[player_id]
            
            # 代理生成动作
            action = agent(combined_obs)

            # 回调：动作
            if 'on_action' in callbacks:
                callbacks['on_action'](player_id, action)

            # 不再手工注入行动段，统一依赖环境的 PLAYER_ACTION 观察 + 上面的字符串化逻辑

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
    
    def get_required_players(self) -> Union[int, Tuple[int, int]]:
        """获取当前游戏需要的玩家数量规则（精确值或区间）。"""
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
