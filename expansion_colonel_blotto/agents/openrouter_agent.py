import os
from typing import Any, Dict, Optional, List, Tuple


class OpenRouterAgent:
    """
    Minimal agent that calls OpenRouter via OpenAI client.
    Exposes a __call__(observation) -> action string and a system_prompt attribute.
    """
    def __init__(self, model_name: str, api_key: str, base_url: str,
                 temperature: float = 0.7, max_tokens: int = 1024,
                 top_p: float = 1.0, frequency_penalty: float = 0.0,
                 presence_penalty: float = 0.0):
        try:
            from openai import OpenAI
        except Exception as e:
            raise ImportError("OpenAI library is required. Install it with: pip install openai") from e

        self.model_name = model_name
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.top_p = top_p
        self.frequency_penalty = frequency_penalty
        self.presence_penalty = presence_penalty

        # Allow env override but prefer explicit args
        api_key = api_key or os.getenv("OPENAI_API_KEY", "")
        base_url = base_url or os.getenv("OPENAI_BASE_URL", "https://openrouter.ai/api/v1")

        # Create client pointed at OpenRouter
        self._client = OpenAI(api_key=api_key, base_url=base_url)

        # Default system prompt; should be set by caller
        self.system_prompt = "You are a competitive game player. Read instructions and follow output format strictly."
        # Two preambles depending on whether we allow visible thinking
        self._preamble_no_think = (
            "IMPORTANT: Respond with a SINGLE line action only. "
            "Do NOT include <think>, chain-of-thought, or any explanations. "
            "Only output like: [A10 B5 C5]."
        )
        self._preamble_allow_think = (
            "You may privately use <think>...</think> briefly. "
            "After thinking, output ONLY one line final action: [Ax By Cz]."
        )
        # Store last response details for logging
        self.last_raw_content: str = ""
        self.last_reasoning: Optional[str] = None
        self.last_action: Optional[str] = None
        self.last_response_meta: Dict[str, Any] = {}

        # Control generation behavior
        self.enable_reasoning: bool = False
        self.include_reasoning: bool = False
        # Optional reasoning effort hint ("low"|"medium"|"high") if supported by model/router
        self.reasoning_effort: Optional[str] = None
        # Default stop sequences when not reasoning: stop at first newline or end-think
        self.stop_sequences: Optional[List[str]] = ["\n", "</think>"]
        self.request_timeout: Optional[float] = None

    def __call__(self, observation: str) -> str:
        try:
            # Ensure observation is a clean string for the chat API
            observation = self._stringify_observation(observation)
            # Choose preamble according to reasoning visibility
            preamble = self._preamble_allow_think if (self.enable_reasoning or self.include_reasoning) else self._preamble_no_think
            system_message = {"role": "system", "content": f"{preamble}\n\n{self.system_prompt}"}
            user_message = {"role": "user", "content": observation}
            # Request reasoning tokens where supported
            extra_body = None
            if self.enable_reasoning or self.include_reasoning:
                extra_body = {"reasoning": {"enabled": True}}
                if self.reasoning_effort in {"low", "medium", "high"}:
                    # Some routers/models accept effort hints
                    extra_body["reasoning"]["effort"] = self.reasoning_effort
                if self.include_reasoning:
                    extra_body["include_reasoning"] = True

            # Dynamic stops: when reasoning is on, don't stop on first newline
            stops = None if (self.enable_reasoning or self.include_reasoning) else self.stop_sequences

            resp = self._client.chat.completions.create(
                model=self.model_name,
                messages=[system_message, user_message],
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                top_p=self.top_p,
                frequency_penalty=self.frequency_penalty,
                presence_penalty=self.presence_penalty,
                stop=stops,
                # Optional OpenRouter-specific body
                extra_body=extra_body,
                timeout=self.request_timeout,
            )
            msg = resp.choices[0].message
            content = getattr(msg, "content", "") or ""
            reasoning = getattr(msg, "reasoning", None)

            # Save for external logging
            self.last_raw_content = content
            self.last_reasoning = reasoning
            # Try to extract strict action format to avoid extra text
            action = self._extract_action(content)
            self.last_action = action
            # Store minimal meta
            self.last_response_meta = {
                "id": getattr(resp, "id", None),
                "created": getattr(resp, "created", None),
                "model": getattr(resp, "model", None),
            }
            return action
        except Exception as e:
            return f"An error occurred: {e}"

    def get_model_info(self) -> Dict[str, Any]:
        return {
            "model_name": self.model_name,
            "config": {
                "temperature": self.temperature,
                "max_tokens": self.max_tokens,
                "top_p": self.top_p,
                "frequency_penalty": self.frequency_penalty,
                "presence_penalty": self.presence_penalty,
            }
        }

    def get_last_output(self) -> Dict[str, Any]:
        """Expose last raw content, reasoning, and action for logging."""
        return {
            "raw_content": self.last_raw_content,
            "reasoning": self.last_reasoning,
            "action": self.last_action,
            "meta": self.last_response_meta,
        }

    def _extract_action(self, text: str) -> str:
        """Extract the first occurrence of [Ax By Cz] ignoring extra text."""
        import re
        # Common variations include spaces or labels before brackets
        pattern = re.compile(r"\[\s*A\s*(\d+)\s*B\s*(\d+)\s*C\s*(\d+)\s*\]")
        matches = pattern.findall(text)
        if matches:
            a, b, c = matches[-1]  # prefer the last if multiple
            return f"[A{a} B{b} C{c}]"
        # Fallback: return first bracketed group to avoid empty
        bracket = re.search(r"\[[^\]]+\]", text)
        return bracket.group(0) if bracket else text.strip()

    def _stringify_observation(self, obs: Any) -> str:
        """Coerce observations from env into a readable string.

        Handles cases where the env returns a list of tuples like
        (to_id, message, type) or nested lists. We join all message
        strings with newlines. Falls back to str(obs) otherwise.
        """
        if isinstance(obs, str):
            return obs
        try:
            # Typical TextArena observation: List[Tuple[to_id, message, type]]
            if isinstance(obs, (list, tuple)):
                parts: List[str] = []
                for item in obs:
                    if isinstance(item, (list, tuple)):
                        # expect something like (-1, message, kind)
                        if len(item) >= 2 and isinstance(item[1], str):
                            parts.append(item[1])
                        else:
                            parts.append(str(item))
                    else:
                        parts.append(str(item))
                return "\n".join(parts)
        except Exception:
            pass
        return str(obs)