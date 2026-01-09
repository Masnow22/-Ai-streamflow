# 🤖 AI ArXiv Streamflow
**基于 Gemini/Gemma 的自动化学术论文早/晚报助手**

[![GitHub Actions](https://img.shields.io/badge/Actions-Automated-green.svg)](https://github.com/Masnow22/-Ai-streamflow/actions)
[![Python](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/)
[![Model](https://img.shields.io/badge/AI-Gemma%203%2027B-7D4EB1.svg)](https://ai.google.dev/gemma)

这是一个专为 AI 研究者和开发者设计的自动化工具。它每天定时从 ArXiv 抓取最新的 AI 论文，利用 Google 最新的 AI 模型进行深度总结，并精准推送到你的微信机器人。



---

## ✨ 核心功能

* **双时段推送**：自动识别北京时间，生成“早报”与“晚报”不同抬头，符合阅读习惯。
* **智能去重**：通过 `read_papers.json` 持久化记录已读论文 ID，确保绝不重复推送。
* **深度总结**：不仅给出摘要，还包含 **核心贡献**、**大白话启发** 以及 **5个专业名词解释**。
* **频率保护**：内置安全冷却机制（10s 间隔），完美绕开免费版 API 的 `429 Too Many Requests` 频率限制。
* **2026 最新架构**：采用 Google 最新的 `google-genai` SDK，兼容 Gemini 3.0/2.0 及 Gemma 3 系列模型。

---

## 🚀 快速开始

### 1. 配置环境变量 (Secrets)
在你的 GitHub 仓库中，进入 `Settings -> Secrets and variables -> Actions`，添加以下两个关键变量：
* `GEMINI_KEY`: 你的 Google AI Studio API Key。
* `WECHAT_WEBHOOK`: 你的微信机器人 Webhook 链接。

### 2. 自定义订阅主题
在 `main.py` 中修改 `TOPIC` 变量以关注你感兴趣的领域：
```python
TOPIC = "cs.AI"  # 可选: cs.CV (视觉), cs.LG (机器学习), cs.CL (自然语言处理)
