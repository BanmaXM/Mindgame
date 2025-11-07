# MindGames 本地扩展版（Colonel Blotto 等）

> 这是一个以“本地可编辑、易于复现实验”为目标的游戏对战与日志框架。核心改动是用本地 `expansion_src` + `expansion_envs` + `expansion_colonel_blotto` 重写原 TextArena 逻辑，使得环境、管理器、代理、日志统一在本仓库可控范围内，支持快速修改与验证。
> 运行只需在 `expansion_colonel_blotto/` 目录下执行 `python run_multi_config.py` 即可。
## 目录总览

- `expansion_src/`：通用管理器与运行框架（本地改写版）
  - `game_manager.py`：统一的游戏生命周期管理、回合循环、观察与行动回调、日志钩子。
- `expansion_envs/`：各游戏的本地环境实现（可自定义）
  - `ColonelBlotto/`：上校博弈的环境与渲染器。
  - 其他游戏目录（如 `SecretMafia/`、`Codenames/`、`ThreePlayerIPD/`）。
- `expansion_colonel_blotto/`：Colonel Blotto 的可运行脚本与代理配置
  - `run_multi_config.py`：推荐的可配置入口脚本（一次可跑多局）。
  - `run_single_colonel_blotto.py`：单局快速运行与日志保存的脚本。
  - `run_colonel_blotto.py`：与单局脚本对齐的另一个入口（保持兼容）。
  - `agents/`：代理封装（`agent0.py`、`agent1.py`、`openrouter_agent.py`）。
  - `prompts/`：两位代理的提示词文件（`prompt_agent0.txt`、`prompt_agent1.txt`）。
  - `model_pool*/api/*.yaml`：模型与推理参数的 YAML 配置（可自定义模型、token、温度等）。
  - `data/single_runs/<date>/<timestamp>/`：每次运行的日志与摘要会保存在按日期与时间戳划分的子目录内。
- `requirements.txt`：依赖列表。
- `src/` 与 `envs/`：原始版本的参考实现（保留以便对照或备用）。
- `testcode/`：简单的连通性与延迟测试脚本。

## 快速开始

- Python 版本：建议 `Python 3.12+`
- 安装依赖：
  - 在仓库根目录执行：
    - `pip install -r mindgames/requirements.txt`
- 配置 API Key（如使用 OpenRouter）：
  - `export OPENROUTER_API_KEY="<你的密钥>"`

- 运行推荐入口（多局可配置）：
  - `python mindgames/expansion_colonel_blotto/run_multi_config.py`

运行后，日志会保存在：
- `mindgames/expansion_colonel_blotto/data/single_runs/<YYYY-MM-DD>/<YYYY-MM-DD_HH-MM-SS>/`
  - `colonel_blotto.json`：详细逐步日志（包含 observation、action、raw_content、reasoning、meta）。
  - `summary.csv`：简要摘要（每步核心信息）。
  - `agent_info.json`：本局代理与模型的配置信息概览。

## 关键设计

### 1. 本地管理器（`expansion_src/game_manager.py`）
- 统一控制游戏：初始化、添加代理、开始游戏、回合循环。
- 在 `play_game` 中负责：
  - 让环境产生规范化的 `observation`；
  - 调用代理生成 `action`；
  - 将 `observation` 与 `action` 以回调方式记录日志：
    - `on_observation(player_id, observation)`
    - `on_action(player_id, action)`
    - `on_step_complete(done, info)`
- 约定：传入模型的 `user_message` 等于环境累计给出的完整 `observation` 文本（不做二次拼接或额外注入）。

### 2. 本地环境（`expansion_envs/ColonelBlotto/env.py`）
- 负责游戏规则、状态渲染、轮次推进与胜负判定。
- 观察文本格式严格化：每轮包含三段：
  - `[GAME] Round Header`（开局信息与轮次头）
  - `Player Action`（两行：`[Commander X]` + 分配命令行）
  - `[GAME] Round Result`（战斗结算与比分更新）
- 环境在 `step()` 中会将玩家的行动回写到下一次观察里（无需管理器或代理手工注入行动段）。

### 3. 代理封装（`expansion_colonel_blotto/agents/`）
- `Agent0` / `Agent1`：
  - 读取各自的 prompt 与模型 YAML；
  - 通过 `OpenRouterAgent` 调用远端模型；
  - 可在 `run_multi_config.py` 里设置 `reasoning` 模式与推理强度。
- `OpenRouterAgent`：
  - 负责构造系统消息与用户消息，并调用 OpenRouter（OpenAI SDK）。
  - 将模型返回的完整原始文本保存到 `last_raw_content`，可见推理保存到 `last_reasoning`。
  - 从返回文本解析出具体行动字符串（例如分配命令），返回给管理器执行。

### 4. 日志与目录结构
- 每次运行都会新建一个“时间戳子目录”，所有文件集中保存于该目录：
  - 路径格式：`data/single_runs/<date>/<timestamp>/`
  - 这样不会造成同一天多个运行的文件散落；更易于后续分析与归档。
- JSON 逐步日志字段示例：
  - `type: "observation" | "action"`
  - `player_id: 0 | 1`
  - `content: string`（动作或观察的主要内容）
  - `raw_content: string | null`（模型返回的原始文本；错误时可能保留上一轮内容）
  - `reasoning: string | null`（仅当 `reasoning="visible"` 且模型支持时可见）
  - `meta: object`（额外元信息，如 tokens、latency 等）

## 主入口脚本：`run_multi_config.py`

该脚本是推荐的运行入口，支持一次跑多局并集中保存日志。

- 配置入口：直接编辑文件顶部的 `CONFIG` 字典：
  - `num_games: int` — 本次要跑的局数（如 1、3、10）。
  - `rounds: int` — 每局的回合数，传入本地环境的 `num_rounds`。
  - `reasoning: "off" | "on" | "visible"` — 推理模式：
    - `off`：关闭推理，速度最快；
    - `on`：开启隐藏推理（路由侧可能闭门思考，但不返回 `<think>`）；
    - `visible`：开启可见推理（调试用），若模型/路由支持则在日志 `reasoning` 字段中可见；
  - `reasoning_effort: Optional["low"|"medium"|"high"]` — 若模型支持，控制推理强度；
  - `request_timeout: Optional[float]` — 每次请求超时（秒）。
  - `agent0/agent1`：
    - `model_yaml_path` — 自定义 YAML 路径（留空用默认）；
    - `prompt_path` — 自定义 prompt 路径（留空用默认）；
    - `model_name_override` — 直接覆盖 YAML 中的模型名（如 `openai/gpt-5-mini`）。
  - `seed: Optional[int]` — 传入 `GameManager.start_game()` 的随机种子，便于复现实验。

- 运行：
  - `python mindgames/expansion_colonel_blotto/run_multi_config.py`
  - 运行结束后，终端会打印日志目录路径，例如：
    - `.../data/single_runs/2025-11-07/2025-11-07_16-10-39`

## 其他入口脚本与兼容性

- `run_single_colonel_blotto.py`：
  - 单局运行，便于快速验证环境与代理配置；
  - 与 `run_multi_config.py` 使用同一套日志与目录结构。

- `run_colonel_blotto.py`：
  - 保持与单局脚本一致的保存方式与输出结构；
  - 适合需要更简洁入口的场景（例如集成旧流水线）。（暂时没啥用）

## 模型与提示词配置

- YAML 配置示例（位于 `model_pool*/api/*.yaml`）：
  - 可设置 `model_name`、`temperature`、`max_tokens`（例如 `65536`）等参数；
  - 代理内部会保证 `max_tokens >= 4096` 的下限，以避免输出被截断。
- Prompt：位于 `prompts/` 目录，可直接编辑两位代理的提示词文件。
- 在 `run_multi_config.py` 的 `CONFIG.agent0/agent1.model_name_override` 可覆盖 YAML 模型名，便于快速切换模型。

## 工作流说明（核心逻辑）

1. 管理器启动：`GameManager.setup_game()` 选择环境并传入基础 `env_config`（如 `num_rounds`）。
2. 每回合：
   - 环境生成观察文本（包含 `[GAME]` 头、上一轮行动段、结算结果等）。
   - 管理器将完整观察文本作为 `user_message` 传给代理；
   - 代理依据 prompt 与 YAML 配置，调用模型返回行动字符串；
   - 管理器调用 `env.step(action)` 推进游戏状态；
   - 回调记录：`on_observation`、`on_action`、`on_step_complete`。
3. 结束：保存结果与日志到时间戳目录，并打印路径。

## 日志字段差异与常见问题（FAQ）

- `response`（动作字符串） vs `raw_content`（模型原始文本）：
  - 若本轮解析或请求异常，`response` 可能是错误信息字符串；
  - `raw_content` 独立保存最近一次的模型原始输出，异常时可能保留上一轮内容，便于诊断。
- 为什么 `reasoning` 为 `null`？
  - 当 `CONFIG["reasoning"] == "on"` 时表示“隐藏推理”，路由侧启用但不回传 `<think>`，因此日志 `reasoning` 为 `null`；
  - 若希望看到可见思维，请设置为 `"visible"`，且模型/路由需要支持可见思维返回。
- 观察文本的 `[GAME]` 前缀：
  - 每轮观察开头以 `[GAME]` 标识开局/头信息；行动段本身不含 `[GAME]`，但完整 `user_message` 的第一行仍以 `[GAME]` 开始（因为是历史累计的开局头）。

## 开发与扩展建议

- 自定义环境：在 `expansion_envs/<YourGame>/` 新增 `env.py` 与可选 `renderer.py`，参考 `ColonelBlotto` 的三段式观察格式，统一由环境负责把行动回写到下一轮观察。
- 自定义代理：复制 `agents/agent0.py` 或 `agent1.py`，调整 prompt 与 YAML，即可快速引入新代理。
- 性能与稳定性：
  - 可调 `reasoning_effort` 与 `request_timeout`；
  - 网络不稳定时建议降低 `num_games` 或 `rounds`，观察日志中的 `meta` 指标（如 tokens、latency）。

## 测试与排错

- 快速连通性：`python mindgames/expansion_colonel_blotto/run_single_colonel_blotto.py`
- 简易烟雾测试：`mindgames/testcode/smoke_test_gamemanager.py`
- 若遇到解析异常（例如 `list index out of range`）：
  - 查看对应时间戳目录下的 `colonel_blotto.json`，对比 `response` 与 `raw_content`；
  - 必要时调整 prompt 或 YAML（如 `stop_sequences`），并重试。

---

如需在新项目仓库中独立使用，请将本 README 连同 `expansion_src/`、`expansion_envs/`、`expansion_colonel_blotto/` 三个目录一起迁移，并保留 `requirements.txt`。随后按本 README 的“快速开始”与“主入口脚本”章节运行与验证。