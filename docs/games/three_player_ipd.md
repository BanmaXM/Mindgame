# ThreePlayerIPD 游戏环境

## 概述

ThreePlayerIPD（三人囚徒困境）是一个扩展自经典囚徒困境的多人博弈理论游戏环境。在该环境中，三名玩家必须在合作与背叛之间做出决策，平衡短期个人收益和长期集体利益。这个游戏是Mind Games Challenge中"泛化赛道"(Generalization Track)的其中一个环境。

## 游戏规则

### 基本机制

1. **玩家**: 游戏中有3名玩家
2. **回合**: 游戏进行多个回合（默认为5回合）
3. **每回合流程**:
   - 交流阶段: 玩家可以自由交流（默认3轮对话）
   - 决策阶段: 每名玩家对其他两名玩家做出合作(cooperate)或背叛(defect)的决定

### 支付矩阵

对于每对玩家之间的互动，根据他们的决策应用以下支付矩阵:

- 双方合作: 两人各得 R 分（合作奖励，默认3分）
- 双方背叛: 两人各得 P 分（双方背叛惩罚，默认1分）
- 一方背叛，一方合作: 
  - 背叛者得 T 分（背叛奖励，默认5分）
  - 合作者得 S 分（受害者惩罚，默认0分）

### 胜利条件

游戏结束时（所有回合完成后），得分最高的玩家获胜。如有平局，平分奖励。

## 技术实现

ThreePlayerIPD环境在`envs/ThreePlayerIPD/env.py`文件中实现，主要类为`ThreePlayerIPDEnv`。

### 初始化参数

```python
def __init__(self, num_rounds: int=5, communication_turns: int=3, 
             cooperate_reward: int=3, defect_reward: int=5, 
             sucker_reward: int=0, mutual_defect_reward: int=1):
```

- `num_rounds`: 游戏回合数
- `communication_turns`: 每回合的交流轮数
- `cooperate_reward` (R): 双方合作的奖励
- `defect_reward` (T): 背叛者的奖励
- `sucker_reward` (S): 被背叛者的奖励
- `mutual_defect_reward` (P): 双方背叛的奖励

### 游戏状态

游戏状态包含以下关键信息:

```python
game_state = {
    "round": 1,                    # 当前回合
    "num_rounds": self.num_rounds, # 总回合数
    "phase": "conversation",       # 当前阶段 (conversation或decision)
    "conversation_round": 0,       # 当前交流轮数
    "total_conversation_rounds": self.conversation_rounds, # 每回合总交流轮数
    "decisions": {p: {q: None for q in range(num_players) if q != p} for p in range(num_players)}, # 决策矩阵
    "scores": {p: 0 for p in range(num_players)}, # 玩家得分
    "acted": {p: False for p in range(num_players)}, # 玩家是否已行动
}
```

### 关键方法

1. **`reset(num_players, seed)`**
   - 初始化游戏状态
   - 设置初始提示

2. **`step(action)`**
   - 处理玩家动作并更新游戏状态
   - 根据当前阶段调用不同处理函数

3. **`_conversation_phase(msg)`**
   - 处理交流阶段的消息
   - 将消息广播给其他玩家
   - 检查是否完成所有交流轮次

4. **`_decision_phase(msg)`**
   - 解析玩家的决策命令
   - 记录玩家对其他玩家的合作/背叛决定
   - 检查是否所有玩家都已做出决策

5. **`_resolve_round()`**
   - 计算玩家间的得分
   - 更新总分
   - 显示回合结果

6. **`_end_game()`**
   - 计算最终排名
   - 设置游戏结果和奖励

## 代理开发指南

### 观察格式

代理接收的观察字符串包含以下信息:

1. **游戏规则**: 游戏机制、回合数和支付矩阵
2. **当前状态**: 当前阶段（交流或决策）和回合数
3. **历史信息**: 其他玩家的过去行为和对话

### 动作格式

代理需要根据当前阶段返回不同格式的动作:

1. **交流阶段**: 自由文本，会被广播给所有其他玩家
2. **决策阶段**: 对每个其他玩家的决策，格式如下:
   - `[<玩家ID> cooperate]` - 选择与该玩家合作
   - `[<玩家ID> defect]` - 选择背叛该玩家
   - 例如: `[1 defect] [2 cooperate]` 表示背叛玩家1，与玩家2合作

如果没有明确指定决策，默认为`cooperate`（合作）。

### 策略提示

1. **建立信任**:
   - 在早期回合尝试建立合作关系
   - 使用交流阶段协调战略和建立联盟

2. **报复与宽恕**:
   - 考虑对背叛者实施有限报复
   - 实施"针锋相对"(Tit-for-Tat)等策略

3. **联盟形成**:
   - 尝试与另一名玩家结成联盟，共同背叛第三名玩家
   - 注意联盟的稳定性和背叛风险

4. **声誉管理**:
   - 维护可靠合作伙伴的声誉
   - 评估其他玩家的可信度

5. **终局策略**:
   - 注意最后回合可能出现的"终局效应"（更多的背叛行为）
   - 考虑提前背叛以保护自己的利益

## 示例

### 观察示例

```
You are Player 0 in a 3-player Iterated Prisoner's Dilemma. The match lasts 5 rounds.
Round structure:
• 3 free-chat turns
• 1 decision turn - submit one token per opponent: '[<opp-id> cooperate]' or '[<opp-id> defect]' (i.e. '[1 defect] [2 cooperate]'; the default is 'cooperate'). 
Pair-wise payoff matrix (applied to each unordered pair):
  - Both cooperate  ->  3
  - Both defect     ->  1
  - You defect, they cooperate -> 5
  - You cooperate, they defect -> 0
The player(s) with the highest score at the end of all rounds wins.

─── Starting Round 1 ───	You can converse freely for the next 3 rounds.
```

### 动作示例

交流阶段:
```
I propose we all cooperate to maximize our collective score. What do you think?
```

决策阶段:
```
[1 cooperate] [2 cooperate]
```

### 结果示例

```
### Round 1 - Results:
	 Player 0 vs Player 1 chose to cooperate and cooperate respectively (Player 0 gained 3, Player 1 gained 3)
	 Player 0 vs Player 2 chose to cooperate and defect respectively (Player 0 gained 0, Player 2 gained 5)
	 Player 1 vs Player 2 chose to defect and cooperate respectively (Player 1 gained 5, Player 2 gained 0)
-> Current scores: Player 0 (3); Player 1 (8); Player 2 (5)
```

## 总结

ThreePlayerIPD是一个复杂的多人博弈环境，测试代理的协作能力、策略思维和适应性。成功的代理需要能够理解游戏规则、分析对手行为、有效沟通，并做出明智的决策，在合作与竞争之间找到最佳平衡点。

最佳策略往往取决于其他玩家的行为，需要动态调整。代理可能需要实施多种策略组合，如条件合作、联盟形成和控制报复，以在这个环境中取得成功。
