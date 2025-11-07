# 模型池配置说明

本项目已配置了三个新的OpenRouter模型，可以在模型池A和B中使用。

## 新增模型

### 1. OpenAI GPT-5
- **模型名称**: `openai/gpt-5`
- **配置文件**: `openai-gpt-5.yaml`
- **适用场景**: 复杂策略推理，高级决策制定

### 2. X-AI Grok-4-Fast-Free
- **模型名称**: `x-ai/grok-4-fast-free`
- **配置文件**: `x-ai-grok-4-fast-free.yaml`
- **适用场景**: 快速响应，实时决策

### 3. Google Gemini-2.5-Pro
- **模型名称**: `google/gemini-2.5-pro`
- **配置文件**: `google-gemini-2.5-pro.yaml`
- **适用场景**: 多模态理解，复杂任务处理

## 配置详情

所有模型配置都包含以下参数：
- `model`: 模型名称
- `api_key`: OpenRouter API密钥
- `api_base`: API基础URL (https://openrouter.ai/api/v1)
- `max_tokens`: 最大令牌数 (4096)
- `temperature`: 温度参数 (0.7)
- `top_p`: Top-p参数 (0.9)
- `frequency_penalty`: 频率惩罚 (0)
- `presence_penalty`: 存在惩罚 (0)
- `extra_headers`: 额外HTTP头部信息
  - `HTTP-Referer`: 网站URL (可选)
  - `X-Title`: 网站标题 (可选)

## 使用方法

### 1. 测试模型配置

运行测试脚本验证所有模型配置是否正确：

```bash
python test_model_config.py
```

### 2. 运行游戏

使用新配置的模型运行游戏：

```bash
# 使用GPT-5 vs Grok-4-Fast-Free进行上校博弈
python run_game_with_new_models.py --game colonel_blotto --model_0 api/openai-gpt-5 --model_1 api/x-ai-grok-4-fast-free

# 使用Gemini-2.5-Pro vs GPT-5进行三玩家囚徒困境
python run_game_with_new_models.py --game three_player_ipd --model_0 api/google-gemini-2.5-pro --model_1 api/openai-gpt-5

# 自定义参数
python run_game_with_new_models.py \
  --game colonel_blotto \
  --model_0 api/google-gemini-2.5-pro \
  --model_1 api/x-ai-grok-4-fast-free \
  --prompt_0 advanced_strategy \
  --prompt_1 simple_role_play \
  --rounds 5
```

### 3. 使用主程序

也可以使用原有的主程序，指定模型名称：

```bash
# 上校博弈
python main_colonel_blotto.py --model_0 api/openai-gpt-5 --model_1 api/x-ai-grok-4-fast-free

# 三玩家囚徒困境
python main_three_player_ipd.py --model_0 api/google-gemini-2.5-pro --model_1 api/openai-gpt-5
```

## 模型池结构

```
model_pool/
├── pool_A/          # 我们的模型池
│   ├── api/
│   │   ├── openai-gpt-5.yaml
│   │   ├── x-ai-grok-4-fast-free.yaml
│   │   └── google-gemini-2.5-pro.yaml
│   └── local/
└── pool_B/          # 对手模型池
    ├── api/
    │   ├── openai-gpt-5.yaml
    │   ├── x-ai-grok-4-fast-free.yaml
    │   └── google-gemini-2.5-pro.yaml
    └── local/
```

## 注意事项

1. **API密钥**: 所有模型使用相同的OpenRouter API密钥，已配置在YAML文件中。
2. **头部信息**: 已配置OpenRouter所需的额外HTTP头部信息，可根据需要修改。
3. **模型可用性**: 请确保在OpenRouter上这些模型可用且配额充足。
4. **错误处理**: 代码已实现错误处理和重试机制，网络问题会自动重试。

## 自定义配置

如需修改模型参数，可以编辑对应的YAML配置文件。例如，要修改GPT-5的温度参数：

```yaml
# model_pool/pool_A/api/openai-gpt-5.yaml
model: "openai/gpt-5"
api_key: "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"
api_base: "https://openrouter.ai/api/v1"
max_tokens: 4096
temperature: 0.5  # 修改温度参数
top_p: 0.9
frequency_penalty: 0
presence_penalty: 0
extra_headers:
  "HTTP-Referer": "<YOUR_SITE_URL>"
  "X-Title": "<YOUR_SITE_NAME>"
```

## 故障排除

如果遇到问题，请检查：
1. 网络连接是否正常
2. API密钥是否有效
3. 模型名称是否正确
4. OpenRouter账户是否有足够配额

可以通过运行测试脚本 `test_model_config.py` 来诊断配置问题。