# Mind Games Challenge 使用指南

本目录包含了使用Mind Games Challenge游戏环境的示例代码，以及人类与LLM代理对战的工具。

## 快速开始

### 安装依赖

首先，安装所需的依赖：

```bash
pip install -r ../requirements.txt
```

### 命令行方式运行游戏

您可以使用命令行示例运行人类与LLM的对战：

```bash
# 运行默认游戏(三人囚徒困境)
python human_vs_llm_example.py

# 指定游戏
python human_vs_llm_example.py --game secret_mafia

# 指定游戏和模型
python human_vs_llm_example.py --game colonel_blotto --model_name deepseek-ai/DeepSeek-R1-0528-Qwen3-8B

# 指定人类玩家数量
python human_vs_llm_example.py --game codenames --human_players 2

# 使用固定随机种子
python human_vs_llm_example.py --game three_player_ipd --seed 42
```

### 使用WebUI进行游戏

您可以启动基于Gradio的WebUI来与LLM代理对战：

```bash
# 启动本地WebUI
python ../src/webui.py

# 指定端口
python ../src/webui.py --port 8080

# 创建公共链接分享
python ../src/webui.py --share
```

## 支持的游戏

1. **SecretMafia** (`secret_mafia`) - 社交推理游戏，探测玩家身份
2. **ThreePlayerIPD** (`three_player_ipd`) - 三人囚徒困境，测试合作与背叛
3. **ColonelBlotto** (`colonel_blotto`) - 资源分配策略游戏
4. **Codenames** (`codenames`) - 基于词汇联想的2v2团队游戏

## 使用游戏管理器进行自定义开发

您可以在自己的代码中使用`GameManager`类来实现自定义功能：

```python
from src.game_manager import GameManager

# 创建游戏管理器
manager = GameManager()

# 查看可用游戏
games = manager.list_available_games()
print(f"可用游戏: {games}")

# 设置游戏环境
game_name = manager.setup_game("three_player_ipd")

# 获取所需玩家数
required_players = manager.get_required_players()

# 添加人类和LLM玩家
human_id = manager.add_human_player()
llm_ids = [manager.add_llm_player("deepseek-ai/DeepSeek-R1-0528-Qwen3-8B") 
          for _ in range(required_players - 1)]

# 设置回调函数
callbacks = {
    "on_observation": lambda player_id, obs: print(f"玩家{player_id}的观察: {obs[:50]}..."),
    "on_action": lambda player_id, action: print(f"玩家{player_id}的动作: {action}")
}

# 开始游戏
manager.start_game()

# 运行游戏
result = manager.play_game(callbacks=callbacks)
print(f"游戏结果: {result}")
```

## 扩展开发

您可以基于提供的工具进行扩展开发，例如：

1. 创建自定义代理类继承自`Agent`基类
2. 开发AI对AI的自动对战系统
3. 实现多轮比赛和统计分析
4. 创建更丰富的可视化界面

有关更多信息，请参阅项目文档。
