# SAUOS

**Screen Automation Universal Operating System** - AI驱动的智能桌面自动化系统

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Website](https://img.shields.io/badge/Website-sauos.net-blue)](https://sauos-aient.sauos.net)

**官网**: [https://sauos-aient.sauos.net](https://sauos-aient.sauos.net)

## 简介

SAUOS 通过大语言模型和视觉理解能力，实现自然语言驱动的计算机操作自动化。让AI像人一样"看"屏幕、"理解"界面、"执行"操作。

## 核心特性

- **视觉理解** - 实时截屏分析，识别UI元素、文本内容、按钮位置
- **智能决策** - 基于LLM的任务规划，自动分解复杂操作步骤
- **精准操控** - 鼠标点击/拖拽、键盘输入、热键组合、窗口管理
- **多模型支持** - OpenAI、Claude、阿里百炼、DeepSeek等8+大模型一键切换
- **私有部署** - 支持Ollama本地模型，数据不出内网

## 支持的AI模型

| 服务商 | 模型 |
|--------|------|
| OpenAI | GPT-4o, GPT-4-turbo |
| Claude | claude-3.5-sonnet |
| 阿里百炼 | qwen-max, qwen-vl |
| DeepSeek | deepseek-chat |
| 智谱AI | glm-4 |
| MiniMax | abab6.5s-chat |
| 火山引擎 | doubao-pro |
| Moonshot | moonshot-v1-8k |
| Ollama | 本地私有部署 |

## 快速开始

```bash
# 克隆项目
git clone https://github.com/wwwsauoscom/sauos-aient.git
cd sauos-aient

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/macOS
# venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt

# 启动Web界面
python web.py  # 访问 http://localhost:5678

# 或启动CLI
python run.py
```

## 项目结构

```
sauos/
├── sauos/
│   ├── core/           # 核心模块
│   │   ├── screen.py   # 屏幕截图
│   │   ├── mouse.py    # 鼠标控制
│   │   ├── keyboard.py # 键盘输入
│   │   ├── window.py   # 窗口管理
│   │   └── image.py    # 图像匹配
│   ├── ai/             # AI模块
│   │   ├── llm.py      # LLM适配器
│   │   ├── vision.py   # 视觉分析
│   │   ├── agent.py    # AI代理
│   │   └── config.py   # 配置管理
│   ├── automation.py   # 自动化主类
│   └── scheduler.py    # 任务调度
├── web.py              # Web界面
├── run.py              # CLI入口
└── website/            # 静态官网
```

## 系统要求

- Python 3.9+
- macOS / Windows / Linux
- 屏幕录制权限（macOS需要在系统偏好设置中授权）

## 许可证

MIT License
