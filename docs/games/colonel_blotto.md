# ColonelBlotto 游戏环境

## 概述

ColonelBlotto（布洛托上校）是一个经典的资源分配策略游戏，玩家必须在多个战场上分配有限的兵力资源。这个游戏测试玩家的资源分配策略和对对手心理的预判能力。ColonelBlotto 是 Mind Games Challenge 中"泛化赛道"(Generalization Track)的其中一个环境。

## 游戏规则

### 基本机制

1. **玩家**: 游戏有2名玩家，分别为"指挥官阿尔法"(Commander Alpha)和"指挥官贝塔"(Commander Beta)
2. **战场**: 游戏有多个战场（默认为3个，由字母A-Z标识）
3. **回合**: 游戏进行多个回合（默认为10回合）
4. **资源**: 每名玩家每回合有固定数量的单位可以分配（默认为20个单位）

### 每回合流程

1. 每名玩家在各个战场上秘密分配自己的兵力单位
2. 分配完成后，比较每个战场上的兵力数量
3. 在每个战场上，分配兵力较多的玩家获胜
4. 赢得大多数战场的玩家赢得该回合

### 资源限制

- 玩家必须分配所有可用单位（默认20个）
- 单位分配必须是非负整数
- 单位可以不均匀分配（某些战场可以为0）

### 胜利条件

- 赢得大多数回合的玩家获得最终胜利
- 如果达到预设的回合数上限，拥有更多回合胜利的玩家获胜
- 如达到可以确保胜利的回合胜利数（如10回合中赢得6回合），游戏提前结束

## 技术实现

ColonelBlotto环境在`envs/ColonelBlotto/env.py`文件中实现，主要类为`ColonelBlottoEnv`。

### 初始化参数

```python
def __init__(self, num_fields: int = 3, num_total_units: int = 20, num_rounds: int = 10):
```

- `num_fields`: 战场数量（2-26，以英文字母A-Z命名）
- `num_total_units`: 每名玩家每回合可分配的总单位数
- `num_rounds`: 游戏的最大回合数

### 游戏状态

游戏状态包含以下关键信息:

```python
game_state = {
    'fields': [{'name': field_name, 'value': 1, 'player_0_units': 0, 'player_1_units': 0} 
               for field_name in self.field_names],
    'current_round': 1, 
    'scores': {0: 0, 1: 0},
    'player_states': {0: copy.copy(self._player_states), 1: copy.copy(self._player_states)}
}
```

其中`_player_states`为：

```python
{
    'units_remaining': self.num_total_units,
    'current_allocation': {field_name: 0 for field_name in self.field_names}, 
    'allocation_complete': False
}
```

### 关键方法

1. **`reset(num_players, seed)`**
   - 初始化游戏状态
   - 设置初始提示和战场

2. **`step(action)`**
   - 处理玩家动作并更新游戏状态
   - 执行资源分配

3. **`_execute_player_move(action)`**
   - 解析玩家的资源分配命令
   - 验证分配是否有效
   - 更新游戏状态

4. **`_parse_allocation_input(action_string)`**
   - 将玩家输入的字符串解析为资源分配字典
   - 处理格式如`[A4 B2 C2]`的输入

5. **`_validate_allocation(allocation_dict)`**
   - 验证分配是否符合游戏规则
   - 检查战场名称、单位数量和总分配量

6. **`_resolve_battle()`**
   - 确定每个战场的胜者
   - 计算回合胜利者
   - 更新得分和游戏状态

7. **`_check_gameover()`**
   - 检查游戏是否结束
   - 确定最终胜者

## 代理开发指南

### 观察格式

代理接收的观察字符串包含以下信息:

```
=== COLONEL BLOTTO - Round X/10 ===
Rounds Won - Commander Alpha: X, Commander Beta: Y
Available fields: A, B, C
Units to allocate: 20
Format: '[A4 B2 C2]'.
```

### 动作格式

代理需要返回资源分配命令，格式如下：

```
[A4 B10 C6]
```

其中字母表示战场，数字表示分配到该战场的单位数量。所有分配的单位总和必须等于可用总单位数（默认20）。

### 策略提示

1. **均衡分配**:
   - 在所有战场上平均分配资源
   - 降低风险，但可能没有突出优势

2. **不对称分配**:
   - 集中资源在少数战场上
   - 增加某些战场胜利的概率，但放弃其他战场

3. **混合策略**:
   - 随机变化资源分配
   - 降低被对手预测的可能性

4. **反应式策略**:
   - 分析对手过去的分配模式
   - 针对性调整资源分配

5. **博弈论最优策略**:
   - 考虑纳什均衡
   - 实施混合策略均衡

### 高级考量

1. **心理战术**:
   - 建立可预测的模式，然后突然改变
   - 利用对手可能的过度反应

2. **价值评估**:
   - 评估不同战场的相对重要性
   - 将更多资源分配到高价值战场

3. **回合动态**:
   - 考虑游戏进程中的得分情况
   - 根据当前得分调整冒险程度

## 示例

### 观察示例

```
=== COLONEL BLOTTO - Round 1/10 ===
Rounds Won - Commander Alpha: 0, Commander Beta: 0
Available fields: A, B, C
Units to allocate: 20
Format: '[A4 B2 C2]'.
```

### 动作示例

```
[A7 B6 C7]
```

### 结果示例

```
Round 1
Commander Alpha allocated: A: 7, B: 6, C: 7
Commander Beta allocated:  A: 5, B: 10, C: 5
Winner: Commander Alpha
```

## 总结

ColonelBlotto是一个测试资源分配策略和对手预测能力的经典游戏。成功的代理需要能够制定有效的资源分配策略，同时预测和应对对手的行动。这个游戏环境特别适合研究混合策略、博弈论平衡和适应性决策。
