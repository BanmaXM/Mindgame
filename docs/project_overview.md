# Mind Games Challenge 项目概述

## 项目背景

Mind Games Challenge 是一个专注于人工智能代理在多种游戏环境中的表现测试的竞赛。该竞赛旨在推动人工智能在社交检测和战略决策方面的能力发展，涵盖了从心理博弈到资源分配的多种智力挑战。

## 竞赛赛道

Mind Games Challenge 分为两个主要赛道：

1. **社交检测赛道 (Social Detection Track)**
   - 环境: SecretMafia-v0
   - 关注点: 测试代理识别欺骗和社交操纵的能力
   - 参与脚本: `online_play_track1.py`

2. **泛化赛道 (Generalization Track)**
   - 环境: 
     - Codenames-v0
     - ColonelBlotto-v0
     - ThreePlayerIPD-v0
   - 关注点: 测试代理在多种不同游戏类型中泛化能力
   - 参与脚本: `online_play_track2.py`

## 竞赛分组

竞赛分为两个组别：

1. **开放组 (Open Division)** - 默认组别，对模型大小和计算资源没有限制
2. **高效组 (Efficient Division)** - 针对资源高效的代理，专注于较小模型和优化性能

## 项目结构

```
mindgames-starter-kit/
├── src/                           # 源代码目录
│   ├── agent.py                   # 代理基础类和示例实现
│   ├── offline_play.py            # 离线游戏测试脚本
│   ├── offline_evaluation.py      # 离线评估脚本
│   ├── online_play_track1.py      # 社交检测赛道参与脚本
│   └── online_play_track2.py      # 泛化赛道参与脚本
│
├── envs/                          # 游戏环境目录
│   ├── SecretMafia/               # 社交欺骗检测游戏
│   ├── ThreePlayerIPD/            # 三人囚徒困境游戏
│   ├── ColonelBlotto/             # 资源分配策略游戏
│   └── Codenames/                 # 词汇关联游戏
│
└── docs/                          # 文档目录
```

## 核心组件

### Agent 类 

位于 `src/agent.py`，定义了代理的基本接口。所有参赛代理必须继承自此类并实现 `__call__` 方法。

### 游戏环境

通过 TextArena 库实现的多种游戏环境，每个环境测试不同的AI能力。

### 在线和离线脚本

- **离线脚本**: 用于本地测试和训练
- **在线脚本**: 用于连接到竞赛服务器参与比赛

## 参与流程

1. **注册团队** - 通过官方表单注册并获取团队验证代码
2. **开发代理** - 设计并实现游戏代理
3. **本地测试** - 使用离线脚本测试代理性能
4. **参与竞赛** - 使用在线脚本连接到竞赛服务器

## 技术依赖

- **textarena** - 核心游戏环境和代理接口库
- **transformers** (可选) - 用于实现基于大语言模型的代理

## 注意事项

- 确保使用一致的模型名称和描述，以便正确识别您的提交
- 每个团队可以提交多个模型，但必须使用不同的模型名称
- 小心处理团队验证代码 (team_hash)，这是您参与竞赛的唯一标识
