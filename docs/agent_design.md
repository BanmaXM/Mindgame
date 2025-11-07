# 代理设计指南

本指南将帮助您为 Mind Games Challenge 设计和开发高效的游戏代理。

## 代理基础

在 Mind Games Challenge 中，所有代理必须继承自基础 `Agent` 类并实现 `__call__` 方法。这个方法接收游戏环境的观察结果，并返回代理的行动。

基础 `Agent` 类结构如下：

```python
class Agent(ABC):
    """ 定义代理基本结构的通用代理类 """
    @abstractmethod
    def __call__(self, observation: str) -> str:
        """
        处理观察并返回行动。

        参数:
            observation (str): 要处理的输入字符串。

        返回:
            str: 代理生成的响应。
        """
        pass
```

## 代理类型

### 人类代理 (HumanAgent)

`HumanAgent` 类允许人类玩家通过终端输入操作参与游戏。这对于测试游戏环境和了解游戏规则非常有用。

```python
class HumanAgent(Agent):
    """ 允许用户手动输入动作的人类代理类 """
    def __init__(self):
        super().__init__()

    def __call__(self, observation: str) -> str:
        print("\n\n+++ +++ +++")  # 便于可视化每个回合的观察
        return input(f"当前观察: {observation}\n请输入动作: ")
```

### LLM代理 (LLMAgent)

`LLMAgent` 类利用大型语言模型(LLM)基于游戏状态做出决策。这是一个强大的基线实现，可用于多种游戏环境。

```python
class LLMAgent(Agent):
    def __init__(self, model_name: str, device: str = "auto", quantize: bool = False, 
                 max_new_tokens: int = 1024, hf_kwargs: dict = None):
        """
        初始化Hugging Face本地代理。
        
        参数:
            model_name (str): 模型的名称。
            device (str): 用于模型推理的设备 (默认: "auto")。
            quantize (bool): 是否以8位量化格式加载模型 (默认: False)。
        """
        super().__init__()
        
        # 初始化Hugging Face模型和tokenizer
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        if quantize:
            self.model = AutoModelForCausalLM.from_pretrained(
                model_name, load_in_8bit=True, device_map=device, **hf_kwargs
            )
        else:
            self.model = AutoModelForCausalLM.from_pretrained(
                model_name, device_map=device, **hf_kwargs
            )
        self.system_prompt = STANDARD_GAME_PROMPT
        self.pipeline = pipeline(
            'text-generation', 
            max_new_tokens=max_new_tokens, 
            model=self.model, 
            tokenizer=self.tokenizer
        )
    
    def __call__(self, observation: str) -> str:
        """
        使用Hugging Face模型处理观察并返回动作。
        
        参数:
            observation (str): 要处理的输入字符串。
        
        返回:
            str: 模型生成的响应。
        """
        try:
            # 生成响应
            response = self.pipeline(
                self.system_prompt + "\n" + observation, 
                num_return_sequences=1, 
                return_full_text=False
            )
            action = response[0]['generated_text'].strip()  # 提取并返回文本输出
            return action
        except Exception as e:
            return f"发生错误: {e}"
```

## 开发高效代理的提示

1. **理解游戏规则**: 详细研究每个游戏环境的规则和机制，了解胜利条件和有效的策略。

2. **观察格式化**: 确保您的代理能够正确解析游戏环境提供的观察字符串。每个游戏环境的观察格式可能不同。

3. **动作格式化**: 确保您的代理生成符合游戏环境期望格式的动作字符串。不正确的格式将导致无效动作。

4. **提示工程**: 如果使用LLM代理，精心设计系统提示可以显著提高性能。考虑包含游戏规则、策略提示和期望输出格式的详细说明。

5. **记忆机制**: 实现一个记忆机制以跟踪游戏历史，帮助代理做出更明智的决策。

6. **自适应策略**: 开发能够根据对手行为调整策略的代理。

## 代理训练方法

1. **有监督微调**: 从人类专家或现有强大代理收集游戏数据，然后使用监督学习微调您的模型。

2. **强化学习**: 使用强化学习算法（如PPO或DQN）通过自我对弈或与其他代理对战来训练您的代理。

3. **混合方法**: 结合有监督学习和强化学习，首先通过模仿学习获得基本能力，然后通过强化学习进一步提高性能。

## 高级优化

1. **量化**: 使用模型量化减少内存占用和提高推理速度，这对于Efficient Division特别重要。

2. **集成学习**: 结合多个不同的代理或策略来提高整体性能。

3. **元学习**: 开发能够快速适应不同游戏环境的代理架构。

4. **知识蒸馏**: 从大型模型中蒸馏知识到更小的模型，保持性能的同时提高效率。

## 测试和评估

使用提供的 `offline_evaluation.py` 脚本来评估您的代理性能。该脚本允许您在多个游戏环境中与固定对手进行测试，并收集性能指标。

示例：
```python
python src/offline_evaluation.py
```

定期测试您的代理，确保它能够有效地处理各种游戏情况，并在提交前修复任何发现的问题。

## 代理行为指南

- 确保您的代理始终遵循游戏规则。
- 避免使用超出比赛范围的外部资源或信息。
- 保持代码高效，特别是当参加Efficient Division时。
- 考虑代理的可解释性，这可以帮助您识别和解决问题。

开发成功的游戏代理是一个迭代过程。通过持续测试、分析和改进，您可以创建在Mind Games Challenge中表现出色的代理。
