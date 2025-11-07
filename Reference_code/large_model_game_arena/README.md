# 大模型游戏竞技场 (Large Model Game Arena)

## 项目概述

这是一个用于测试和评估大型语言模型在博弈游戏中的表现的系统。支持两种游戏：
- **上校博弈 (Colonel Blotto)** - 双人资源分配游戏
- **三人囚徒困境 (Three Player Iterated Prisoner's Dilemma)** - 三人合作与背叛游戏

## 快速开始

### 1. 环境准备

确保已安装Python 3.8+和必要的依赖：

```bash
# 克隆项目后进入目录
cd large_model_game_arena

# 安装依赖（如果有requirements.txt）
pip install -r requirements.txt

# 或者手动安装核心依赖
pip install pyyaml requests
```

### 2. 配置模型和令牌池

#### 2.1 模型池配置

模型配置文件位于 `model_pool/` 目录下，分为两个池：
- `pool_A/` - 我方模型（Agent 0使用）
- `pool_B/` - 对手模型（Agent 1/2使用）

**添加新模型的方法：**

1. **API模型**：在 `model_pool/pool_A/api/` 或 `model_pool/pool_B/api/` 目录下创建YAML文件

```yaml
# 示例：model_pool/pool_A/api/my-model.yaml
model: "provider/model-name"  # 模型标识符
api_key: "your-api-key-here"  # API密钥
api_base: "https://api.provider.com/v1"  # API端点
max_tokens: 4096
temperature: 0.7
top_p: 0.9
frequency_penalty: 0
presence_penalty: 0
extra_headers:
  "HTTP-Referer": "your-site-url"
  "X-Title": "your-site-name"
```

2. **本地模型**：在 `model_pool/pool_A/local/` 或 `model_pool/pool_B/local/` 目录下创建配置

#### 2.2 令牌池配置

令牌池管理多个API令牌，避免高并发时的令牌竞争。配置在 `token_pool.py` 中：

**修改令牌池的方法：**

1. **编辑 `token_pool.py` 文件**，找到以下函数：
   - `initialize_colonel_blotto_token_pools()` - 上校博弈令牌池
   - `initialize_three_player_ipd_token_pools()` - 三人囚徒困境令牌池

2. **修改令牌列表**：
```python
# 示例：添加新的GPT-5令牌
colonel_blotto_gpt5_tokens = [
    "your-token-1",
    "your-token-2",
    # ... 添加更多令牌
]
```

3. **为不同模型分配令牌**：
```python
# 为特定模型添加令牌
colonel_blotto_token_pool.add_tokens("openai/gpt-5", colonel_blotto_gpt5_tokens)
colonel_blotto_token_pool.add_tokens("google/gemini-2.5-pro", other_tokens)
```

### 3. 运行批量游戏

#### 3.1 上校博弈批量运行

```bash
# 运行上校博弈批量实验
python parallel_run_colonel_blotto.py --runs 10 --processes 4

# 参数说明：
# --runs: 运行的游戏次数（默认：10）
# --processes: 并行进程数（默认：CPU核心数）
# --output: 输出目录（默认：data/colonel_blotto/batch_runs/）
# --config: 配置文件路径（默认：config.yaml）
```

#### 3.2 三人囚徒困境批量运行

```bash
# 运行三人囚徒困境批量实验
python parallel_run_three_player_ipd.py --runs 10 --processes 4

# 参数说明：
# --runs: 运行的游戏次数（默认：10）
# --processes: 并行进程数（默认：CPU核心数）
# --output: 输出目录（默认：data/three_player_ipd/batch_runs/）
# --config: 配置文件路径（默认：config.yaml）
```

### 4. 查看结果

运行完成后，结果将保存在：
- 上校博弈：`data/colonel_blotto/batch_runs/`
- 三人囚徒困境：`data/three_player_ipd/batch_runs/`

每个运行批次包含：
- 游戏日志文件（JSON格式）
- Agent配置信息
- 统计结果

## 详细配置说明

### 配置文件 (`config.yaml`)

主要配置项：

```yaml
# 游戏配置
games:
  colonel_blotto:
    name: "Colonel Blotto"
    max_rounds: 10  # 最大回合数
    
  three_player_ipd:
    name: "Three Player Iterated Prisoner's Dilemma"
    max_rounds: 10

# 模型池配置
model_pools:
  pool_A:
    name: "Our Models"
    description: "Strong models for our agent"
    
  pool_B:
    name: "Opponent Models"
    description: "Various models for opponents"

# 提示池配置
prompt_pools:
  colonel_blotto:
    pool_A: ["advanced_strategy", "zero_shot_cot"]
    pool_B: ["simple_role_play", "direct_command"]
```

### Agent配置

Agent类型：
- **Agent 0**：我方主要测试的模型
- **Agent 1/2**：对手模型

每个Agent使用：
- 指定的模型（从模型池中选择）
- 指定的提示策略（从提示池中选择）
- 令牌池中的可用令牌

## 高级功能

### 1. 自定义提示策略

提示文件位于 `prompt_pool/` 目录：
```
prompt_pool/
├── colonel_blotto/
│   ├── pool_A/
│   │   ├── advanced_strategy.txt
│   │   └── zero_shot_cot.txt
│   └── pool_B/
│       ├── simple_role_play.txt
│       └── direct_command.txt
└── three_player_ipd/
    ├── pool_A/
    └── pool_B/
```

添加新的提示策略：
1. 在对应目录创建 `.txt` 文件
2. 在 `config.yaml` 的 `prompt_pools` 部分添加策略名称

### 2. 数据分析工具

项目包含多个分析脚本：

```bash
# 分析Agent 0的胜率
python analyze_agent0_win_rate.py

# 分析所有Agent的胜率
python analyze_all_agents_win_rate.py

# 分析批量运行结果
python analyze_batch_results.py
```

### 3. 模型速度测试

```bash
# 测试模型响应速度
python test_model_speed.py
```

## 故障排除

### 常见问题

1. **API密钥错误**
   - 检查令牌池配置中的API密钥是否正确
   - 确保令牌有足够的配额

2. **模型不可用**
   - 检查模型名称是否正确（provider/model-name格式）
   - 确认API端点可访问

3. **内存不足**
   - 减少并行进程数：`--processes 2`
   - 减少批量运行次数

4. **文件权限问题**
   - 确保有写入数据目录的权限
   - 检查磁盘空间是否充足

### 日志和调试

- 日志级别在 `config.yaml` 中配置
- 详细日志保存在 `logs/` 目录（如果启用）
- 使用 `--verbose` 参数获取更详细的输出

## 技术支持

如有问题，请检查：
1. 配置文件是否正确
2. API密钥是否有效
3. 网络连接是否正常
4. 依赖包是否安装完整

## 文件结构

```
large_model_game_arena/
├── config.yaml                 # 主配置文件
├── token_pool.py              # 令牌池管理
├── parallel_run_*.py         # 批量运行脚本
├── model_pool/               # 模型配置
│   ├── pool_A/              # 我方模型池
│   └── pool_B/              # 对手模型池
├── prompt_pool/             # 提示策略
├── data/                    # 游戏数据
├── agents/                  # Agent实现
└── analysis_scripts/        # 分析工具
```

---

**注意**：运行前请确保已正确配置所有API密钥和模型设置。首次运行建议先进行小规模测试。