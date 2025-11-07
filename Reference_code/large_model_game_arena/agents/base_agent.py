from abc import ABC, abstractmethod

class BaseAgent(ABC):
    """Agent的基类，定义通用接口"""
    
    def __init__(self):
        pass
    
    @abstractmethod
    def __call__(self, observation: str) -> str:
        """
        处理观察信息并生成动作
        
        Args:
            observation: 观察信息
            
        Returns:
            动作字符串
        """
        pass