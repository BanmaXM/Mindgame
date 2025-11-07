# Prompt Pool 文件夹说明

## 概述

`prompt_pool` 文件夹是大型模型游戏竞技场项目中用于存储和管理各种游戏策略提示词的核心资源库。该文件夹包含了针对不同游戏类型（上校博弈和三人囚徒困境）的多种策略提示词，用于指导AI代理在游戏中采取不同的行为模式和决策策略。

## 文件夹结构

```
prompt_pool/
├── colonel_blotto/          # 上校博弈游戏提示词
│   ├── pool_A/              # A类提示词池
│   │   └── advanced_strategy.txt
│   └── pool_B/              # B类提示词池
│       ├── 1_OneFront_Aggressor.txt
│       ├── 2_TwoFront_Power.txt
│       ├── 3_Balanced_Defender.txt
│       ├── 4_One_Front_Balanced.txt
│       ├── 5_Two_Front_Balanced.txt
│       ├── 6_One_Front_Two_Front.txt
│       ├── Dogmatic_Player.txt
│       ├── Stubborn_Player.txt
│       ├── Versatile_Tactician.txt
│       └── simple_role_play.txt
└── three_player_ipd/        # 三人囚徒困境游戏提示词
    ├── pool_A/              # A类提示词池
    │   ├── 1_Liar_0.txt
    │   ├── advanced_strategy.txt
    │   └── simple_role_play.txt
    └── pool_B/              # B类提示词池
        ├── 1_Liar_0.txt
        ├── 1_Liar_1.txt
        ├── 1_Liar_2.txt
        ├── 1_Liar_3.txt
        ├── 1_Liar_4.txt
        ├── 2_Fair_Retaliator_0.txt
        ├── 2_Fair_Retaliator_1.txt
        ├── 2_Fair_Retaliator_2.txt
        ├── 2_Fair_Retaliator_3.txt
        ├── 3_Principle_0.txt
        ├── 3_Principle_1.txt
        ├── 3_Principle_2.txt
        ├── advanced_strategy.txt
        ├── simple_role_play.txt
        ├── simple_role_play_1.txt
        ├── simple_role_play_2.txt
        ├── simple_role_play_3.txt
        ├── simple_role_play_4.txt
        ├── simple_role_play_4_copy.txt
        ├── simple_role_play_5.txt
        └── simple_role_play_5_copy.txt
```

## 提示词分类

### 上校博弈游戏 (Colonel Blotto)

上校博弈游戏是一种资源分配策略游戏，两名玩家同时将20个单位分配到三个战场（A、B、C），目标是赢得至少两个战场。

#### Pool_A 提示词

- **advanced_strategy.txt**: 高级策略提示词，采用"石头剪刀布"式的反制策略，根据对手上一轮的行动模式选择相应的反制策略。包括三种主要战术原型及其反制方法：
  - 单线推进反制：采用平衡策略
  - 双线推进反制：采用单线推进
  - 平衡策略反制：采用双线推进

#### Pool_B 提示词

- **1_OneFront_Aggressor.txt**: 单线侵略者策略，专注于在一个战场上分配大量兵力（13-16个单位），其余兵力分配到其他两个战场。
- **2_TwoFront_Power.txt**: 双线力量策略，在两个战场上分配大量兵力（8-12个单位），牺牲第三个战场。
- **3_Balanced_Defender.txt**: 平衡防御者策略，均衡分配兵力到三个战场。
- **4_One_Front_Balanced.txt**: 单线平衡策略，结合单线推进和平衡分配的特点。
- **5_Two_Front_Balanced.txt**: 双线平衡策略，结合双线推进和平衡分配的特点。
- **6_One_Front_Two_Front.txt**: 单线双线混合策略，在不同轮次交替使用单线和双线策略。
- **Dogmatic_Player.txt**: 教条式玩家策略，坚持特定的战术模式。
- **Stubborn_Player.txt**: 固执玩家策略，不易改变战术。
- **Versatile_Tactician.txt**: 多变战术家策略，灵活使用多种战术。
- **simple_role_play.txt**: 简单角色扮演策略，提供基本游戏规则和输出格式，不指定具体策略。

### 三人囚徒困境游戏 (Three Player IPD)

三人囚徒困境游戏是一种多人重复博弈游戏，玩家在每轮选择合作或背叛，通过讨论和决策两个阶段交替进行，目标是最大化个人得分。

#### Pool_A 提示词

- **1_Liar_0.txt**: 欺骗者策略，专注于通过欺骗和背叛来最大化个人得分，同时假装是合作者。
- **advanced_strategy.txt**: 高级策略，包含两种主要路径：
  - 欺骗赌注：前两轮合作，之后始终背叛
  - 自适应报复：根据对手前两轮的行动进行报复或结盟
- **simple_role_play.txt**: 简单角色扮演策略，提供基本游戏规则和输出格式，不指定具体策略。

#### Pool_B 提示词

- **1_Liar_0.txt 至 1_Liar_4.txt**: 欺骗者策略的变体，专注于通过欺骗和背叛来最大化个人得分。
- **2_Fair_Retaliator_0.txt 至 2_Fair_Retaliator_3.txt**: 公平报复者策略的变体，采用"以牙还牙"策略，根据对手上一轮的行动决定本轮行动。
- **3_Principle_0.txt 至 3_Principle_2.txt**: 原则性玩家策略的变体，遵循特定的道德或行为准则。
- **advanced_strategy.txt**: 高级策略，与Pool_A中的类似但可能有细微差别。
- **simple_role_play.txt 至 simple_role_play_5_copy.txt**: 简单角色扮演策略的多个变体，提供基本游戏规则和输出格式，不指定具体策略。

## 提示词结构

所有提示词文件都遵循相似的结构，包含以下主要部分：

1. **基本指令**：所有提示词都包含相同的基本指令，要求AI代理：
   - 仔细阅读游戏规则和当前状态
   - 在`<think>`标签内思考策略
   - 仅以所需格式输出下一步行动
   - 不包含解释、评论或对未来游戏状态的预测
   - 不重复游戏状态或棋盘
   - 仅在思考块后以所需格式输出单个行动

2. **游戏特定部分**：根据游戏类型（上校博弈或三人囚徒困境）提供特定的：
   - 游戏目标
   - 游戏规则
   - 策略说明

3. **输出格式**：严格定义的输出格式，确保AI代理的输出符合游戏要求：
   - 上校博弈：`[Ax By Cz]`格式，其中x+y+z=20
   - 三人囚徒困境：讨论阶段使用`[<your-id> chat] 消息`格式，决策阶段使用`[<opp-id> cooperate]`或`[<opp-id> defect]`格式

## 提示词池的应用

提示词池在大型模型游戏竞技场项目中有多种应用：

1. **AI代理行为控制**：通过为不同的AI代理分配不同的提示词，控制其在游戏中的行为模式和决策策略。

2. **策略多样性研究**：使用不同的提示词可以研究不同策略在游戏中的表现和效果。

3. **模型能力评估**：通过测试模型在不同策略提示下的表现，评估其理解复杂指令和执行特定策略的能力。

4. **对抗性训练**：使用不同策略的AI代理进行对抗性训练，提高模型的策略思维和适应能力。

5. **数据生成**：通过运行不同策略的AI代理进行游戏，生成用于训练和评估的数据集。

## 提示词设计原则

提示词池的设计遵循以下原则：

1. **明确性**：每个提示词都清晰明确地定义了AI代理应该遵循的策略和行为模式。

2. **一致性**：所有提示词都遵循相同的结构，便于理解和维护。

3. **多样性**：提示词池包含多种不同的策略，从简单到复杂，从合作到竞争，从固定到适应。

4. **可扩展性**：提示词池的结构允许轻松添加新的策略提示词。

5. **游戏特定性**：每个提示词都针对特定游戏类型进行了优化，确保策略与游戏机制相匹配。

## 使用示例

以下是如何在代码中使用提示词池的示例：

```python
# 选择游戏类型
game_type = "colonel_blotto"  # 或 "three_player_ipd"

# 选择提示词池
pool_type = "pool_A"  # 或 "pool_B"

# 选择特定策略
strategy_name = "advanced_strategy"  # 或其他策略名称

# 构建提示词文件路径
prompt_path = f"prompt_pool/{game_type}/{pool_type}/{strategy_name}.txt"

# 读取提示词内容
with open(prompt_path, 'r') as f:
    prompt = f.read()

# 将提示词分配给AI代理
agent = Agent(model="gpt-4", prompt=prompt)
```

## 总结

`prompt_pool` 文件夹是大型模型游戏竞技场项目的核心组件，提供了丰富的策略提示词资源，用于控制AI代理在不同游戏中的行为。通过精心设计的提示词，可以研究不同策略的效果，评估模型的能力，并生成高质量的训练数据。提示词池的结构清晰，内容多样，易于扩展，为项目提供了强大的灵活性和可定制性。