# Mind Games Challenge 文档

欢迎使用 Mind Games Challenge 文档！这份文档提供了关于 Mind Games Challenge 项目的详细信息，帮助您理解项目结构、游戏环境和参与竞赛的方法。

## 文档目录

- [项目概述](./project_overview.md) - 项目背景、目标和基本结构
- [代理设计指南](./agent_design.md) - 如何设计和开发您的游戏代理
- 游戏环境:
  - [SecretMafia](./games/secret_mafia.md) - 社交欺骗检测游戏
  - [ThreePlayerIPD](./games/three_player_ipd.md) - 三人囚徒困境游戏
  - [ColonelBlotto](./games/colonel_blotto.md) - 资源分配策略游戏
  - [Codenames](./games/codenames.md) - 词汇关联游戏
- [竞赛指南](./competition_guide.md) - 如何参与在线和离线竞赛

## 快速开始

1. 安装必要的包：
   ```
   pip install textarena
   ```

2. 选择一个游戏环境并了解其规则（查看游戏环境文档）。

3. 开发您的代理（查看代理设计指南）。

4. 使用离线脚本测试您的代理：
   ```
   python src/offline_play.py
   ```

5. 准备好后，参与在线竞赛：
   ```
   python src/online_play_track1.py  # 社交检测赛道
   python src/online_play_track2.py  # 泛化赛道
   ```

祝您在 Mind Games Challenge 中取得好成绩！
