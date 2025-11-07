# SecretMafia 游戏环境

## 概述

SecretMafia 是一个基于社交欺骗检测的多人游戏环境，玩家被分配不同角色并需要通过社交互动、逻辑推理和策略性决策来实现各自阵营的目标。这个游戏是 Mind Games Challenge 中"社交检测赛道"(Social Detection Track)的核心环境。

## 游戏规则

### 角色

SecretMafia 中有四种角色：

1. **村民 (Villager)**
   - 阵营：村庄 (Village)
   - 目标：通过投票识别并消灭所有黑手党成员
   - 特殊能力：无

2. **黑手党 (Mafia)**
   - 阵营：黑手党 (Mafia)
   - 目标：通过消灭村民直至黑手党人数等于或超过村民人数
   - 特殊能力：每晚可以选择一名玩家进行暗杀

3. **医生 (Doctor)**
   - 阵营：村庄 (Village)
   - 目标：与村民相同
   - 特殊能力：每晚可以选择一名玩家进行保护，使其免受黑手党的暗杀

4. **侦探 (Detective)**
   - 阵营：村庄 (Village)
   - 目标：与村民相同
   - 特殊能力：每晚可以调查一名玩家，立即得知其是否为黑手党成员

### 游戏流程

游戏通过日夜交替的阶段进行：

1. **夜晚阶段 (Night Phase)**
   - **黑手党行动 (Night-Mafia)**: 所有黑手党成员共同选择一名玩家进行暗杀
   - **医生行动 (Night-Doctor)**: 医生选择一名玩家进行保护
   - **侦探行动 (Night-Detective)**: 侦探选择一名玩家进行调查

2. **白天阶段 (Day Phase)**
   - **讨论阶段 (Day-Discussion)**: 所有存活玩家进行多轮讨论
   - **投票阶段 (Day-Voting)**: 所有存活玩家投票决定驱逐一名玩家

### 胜利条件

- **村庄胜利**: 当所有黑手党成员被消灭时
- **黑手党胜利**: 当黑手党成员人数等于或超过村民人数时

## 技术实现

SecretMafia 环境在 `envs/SecretMafia/env.py` 文件中实现，主要类为 `SecretMafiaEnv`。

### 关键组件

1. **角色类 (Role)**
   - 基础抽象类，定义角色的名称、阵营和描述
   - 子类包括 `Villager`, `Mafia`, `Doctor`, `Detective`

2. **阶段枚举 (Phase)**
   - 使用 Python 的 `Enum` 类定义游戏的不同阶段
   - 包括 `NIGHT_MAFIA`, `NIGHT_DOCTOR`, `NIGHT_DETECTIVE`, `DAY_DISCUSSION`, `DAY_VOTING`

3. **投票处理器 (VoteHandler)**
   - 解析玩家投票字符串
   - 统计投票结果并处理平局情况

### 关键方法

1. **`reset(num_players, seed)`**
   - 初始化游戏状态
   - 分配玩家角色
   - 设置初始阶段和观察提示

2. **`_assign_roles(num_players)`**
   - 根据玩家数量分配角色
   - 使用固定比例确定黑手党成员数量

3. **`step(action)`**
   - 处理玩家动作并更新游戏状态
   - 根据当前阶段调用不同的处理函数
   - 检查胜利条件

4. **阶段处理函数**
   - `_handle_discussion`: 处理讨论阶段的发言
   - `_handle_day_vote`: 处理白天投票
   - `_handle_mafia_vote`: 处理黑手党投票
   - `_handle_doctor_action`: 处理医生保护行动
   - `_handle_detective_action`: 处理侦探调查行动

5. **结果处理函数**
   - `_resolve_day_votes`: 处理白天投票结果
   - `_store_mafia_target`: 存储黑手党暗杀目标
   - `_resolve_night_outcome`: 处理夜晚行动结果

6. **游戏结束检查**
   - `_check_win`: 检查胜利条件是否满足

## 代理开发指南

### 观察格式

代理接收的观察字符串包含以下信息：

1. **角色信息**: 玩家的角色、阵营和描述
2. **玩家列表**: 游戏中的所有玩家
3. **游戏阶段**: 当前是哪个阶段
4. **额外信息**: 根据角色不同，可能包含队友信息（黑手党）或调查结果（侦探）

### 动作格式

代理需要根据不同阶段返回不同格式的动作：

1. **讨论阶段**: 自由文本，将广播给所有玩家
2. **投票阶段**: `[Player X]` 格式，表示投票驱逐的目标
3. **黑手党阶段**: `[Player X]` 格式，表示暗杀的目标
4. **医生阶段**: `[Player X]` 格式，表示保护的目标
5. **侦探阶段**: `[Player X]` 格式，表示调查的目标

### 策略提示

1. **村民策略**
   - 仔细观察玩家发言，寻找不一致之处
   - 分析投票模式，寻找可能的黑手党合作行为
   - 保护关键角色（医生和侦探）

2. **黑手党策略**
   - 伪装成村民，避免引起怀疑
   - 协调投票以消灭关键的村方角色
   - 制造混乱和误导，分散村民的注意力

3. **医生策略**
   - 不要透露自己的身份
   - 优先保护可能成为黑手党目标的重要玩家
   - 根据游戏进展调整保护策略

4. **侦探策略**
   - 谨慎分享调查结果，避免被黑手党针对
   - 有策略地选择调查目标
   - 使用调查结果引导村民投票

## 示例

### 观察示例（村民角色）

```
Welcome to Secret Mafia! You are Player 0.
Your role: Villager
Team: Village
Description: A regular villager. Your goal is to identify and eliminate all Mafia members through voting during the day.

Players: Player 0, Player 1, Player 2, Player 3, Player 4, Player 5

The game progresses through Day and Night phases.
- During the Day phase, there are 3 rounds of discussion followed by voting.
- During discussions, everything you say is automatically broadcasted to all players.
- After discussions, all players must vote to eliminate one player.
- During the Night phase, you have no special actions.

The game ends when either all Mafia members are eliminated (Village wins) or
Mafia members equal or outnumber Villagers (Mafia wins).
```

### 动作示例

讨论阶段：
```
I think we should pay attention to Player 3's behavior. They've been quiet and their voting pattern is suspicious.
```

投票阶段：
```
[Player 3]
```

## 总结

SecretMafia 是一个复杂的社交欺骗检测游戏，要求代理具有出色的对话分析、意图识别和战略决策能力。成功的代理需要能够理解游戏规则、分析玩家行为、识别欺骗，并做出有效的决策。
