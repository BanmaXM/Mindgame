import os
import yaml
from typing import Dict, Any
from .openrouter_agent import OpenRouterAgent


class Agent1:
    """Agent1: loads its own prompt and model config from model_pool1.

    Parameters mirror Agent0 (reasoning, reasoning_effort, request_timeout).
    """
    def __init__(self,
                 game_type: str = "colonel_blotto",
                 model_yaml_path: str = None,
                 prompt_path: str = None,
                 reasoning: str = "off",
                 reasoning_effort: str | None = None,
                 request_timeout: float | None = 40.0):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.game_type = game_type
        self.model_yaml_path = model_yaml_path or os.path.join(base_dir, "model_pool1", "api", "openai_gpt5mini.yaml")
        self.prompt_path = prompt_path or os.path.join(base_dir, "prompts", "prompt_agent1.txt")

        self.model_config = self._load_model_config(self.model_yaml_path)
        self.prompt = self._load_prompt(self.prompt_path)
        self.agent_instance = self._create_agent_instance(
            reasoning=reasoning,
            reasoning_effort=reasoning_effort,
            request_timeout=request_timeout,
        )
        # 在代理内部维护观察历史，确保传给模型的是累计输入
        self._obs_history: str | None = None

    def _load_model_config(self, path: str) -> Dict[str, Any]:
        if not os.path.exists(path):
            raise FileNotFoundError(f"Model config not found: {path}")
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    def _load_prompt(self, path: str) -> str:
        if not os.path.exists(path):
            raise FileNotFoundError(f"Prompt file not found: {path}")
        with open(path, "r", encoding="utf-8") as f:
            return f.read()

    def _create_agent_instance(self, *, reasoning: str = "off", reasoning_effort: str | None = None, request_timeout: float | None = 40.0) -> OpenRouterAgent:
        cfg = self.model_config
        agent = OpenRouterAgent(
            model_name=cfg.get("model", "openai/gpt-5-mini"),
            api_key=cfg.get("api_key", ""),
            base_url=cfg.get("api_base", "https://openrouter.ai/api/v1"),
            temperature=cfg.get("temperature", 0.7),
            max_tokens=max(4096, int(cfg.get("max_tokens", 4096))),
            top_p=cfg.get("top_p", 1.0),
            frequency_penalty=cfg.get("frequency_penalty", 0.0),
            presence_penalty=cfg.get("presence_penalty", 0.0),
        )
        # Configure reasoning behavior
        reasoning = (reasoning or "off").lower()
        if reasoning == "off":
            agent.enable_reasoning = False
            agent.include_reasoning = False
            agent.stop_sequences = ["\n", "</think>"]
        elif reasoning == "on":
            agent.enable_reasoning = True
            agent.include_reasoning = False
            agent.stop_sequences = ["</think>"]
        elif reasoning == "visible":
            agent.enable_reasoning = True
            agent.include_reasoning = True
            agent.stop_sequences = None
        else:
            agent.enable_reasoning = False
            agent.include_reasoning = False
            agent.stop_sequences = ["\n", "</think>"]

        if reasoning_effort:
            agent.reasoning_effort = reasoning_effort

        agent.request_timeout = request_timeout
        agent.system_prompt = self.prompt
        return agent

    def __call__(self, observation: str) -> str:
        s = observation if isinstance(observation, str) else str(observation)
        prev = self._obs_history
        if prev is None:
            combined = s
        else:
            if s.startswith(prev) or (prev in s):
                combined = s
            elif prev.startswith(s) or (s in prev):
                combined = prev
            else:
                combined = prev + "\n" + s
        self._obs_history = combined
        return self.agent_instance(combined)

    def get_model_info(self) -> Dict[str, Any]:
        return {
            "agent_type": "Agent1",
            "model_name": self.model_config.get("model"),
            "prompt_name": os.path.basename(self.prompt_path),
            "game_type": self.game_type,
            "config": {k: v for k, v in self.model_config.items() if k != "api_key"},
            "system_prompt": self.prompt,
        }