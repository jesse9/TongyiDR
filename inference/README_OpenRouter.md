# OpenRouter API 使用说明

## 概述

Tongyi DeepResearch 现在支持通过 OpenRouter API 进行推理，无需下载和运行本地模型。这对于没有强大 GPU 的用户特别有用。

## 配置步骤

### 1. 获取 OpenRouter API Key

1. 访问 [OpenRouter](https://openrouter.ai/) 注册账户
2. 在账户设置中获取你的 API Key

### 2. 配置环境变量

复制 `.env.example` 到 `.env` 并进行以下配置：

```bash
# 必需：设置 OpenRouter API Key
OPENROUTER_API_KEY=your_openrouter_api_key_here

# 可选：如果需要通过 SOCKS5 代理访问 API
# SOCKS5_PROXY=socks5://127.0.0.1:1080

# 可选：如果需要从 HuggingFace 镜像站下载 tokenizer
# HF_ENDPOINT=https://hf-mirror.com
```

### 3. 安装依赖

确保已安装所需依赖：

```bash
pip install -r requirements.txt
```

## 使用方法

设置了 `OPENROUTER_API_KEY` 环境变量后，系统会自动使用 OpenRouter API 而不是本地 VLLM 服务器。

### 运行推理

```bash
# 使用 OpenRouter API 运行推理
bash run_react_infer.sh
```

脚本会自动检测到 `OPENROUTER_API_KEY` 环境变量的存在，并跳过本地服务器启动步骤，直接通过 OpenRouter API 进行推理。

### 使用方法

运行脚本时不需要指定额外的参数，系统会自动检测环境变量并使用 OpenRouter：

```bash
bash run_react_infer.sh
```

### 使用不同模型

如果要使用 OpenRouter 上其他的模型，可以通过命令行参数指定：

```bash
bash run_react_infer.sh --openrouter_model "openai/gpt-4o"
```

注意：系统会自动尝试下载相应模型的 tokenizer。对于已知模型使用优化映射，未知模型直接使用模型名。

### 单问题执行

如果只需要对单个问题进行推理，可以使用 `run_agent.py` 脚本：

```bash
python run_agent.py "What is the capital of France?" --output /tmp/output
```

或使用文件上传格式：

```bash
python run_agent.py "(Uploaded 1 file: ['hello.txt'])\n\nHello!" --output /tmp/output
```

## 技术细节

- **模型名称**: 可通过 `--openrouter_model` 参数配置，默认为 `alibaba/tongyi-deepresearch-30b-a3b`
- **API 端点**: `https://openrouter.ai/api/v1`
- **推理参数**: 与本地模型相同（温度、top_p、presence_penalty 等）
- **Tokenizer**: 自动选择对应的 tokenizer（已知模型使用特定映射，未知模型使用模型名本身作为 tokenizer）
- **网络配置**: 支持 SOCKS5 代理和 HuggingFace 镜像站

## 故障排除

1. **API Key 无效**: 确保你的 OpenRouter API Key 正确且有效
2. **网络问题**: 如果在中国大陆使用，可能需要配置 SOCKS5 代理或 HF_ENDPOINT
3. **Tokenizer 下载失败**: 如果无法连接 HuggingFace，请设置 `HF_ENDPOINT` 使用镜像站
4. **配额不足**: 检查你的 OpenRouter 账户是否有足够的 credits

## 回退到本地模型

如果要回退到使用本地模型，只需：
1. 移除或注释掉 `.env` 文件中的 `OPENROUTER_API_KEY`
2. 确保设置了正确的 `MODEL_PATH`
3. 重新运行脚本

这样系统会回到原来的本地 VLLM 服务器模式。
