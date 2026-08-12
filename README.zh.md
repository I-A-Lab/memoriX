<h1 align="center">Memory AGENTX</h1>

<p align="center">
  <em>基于大型语言模型（LLM）的代码智能体的受控持久内存系统的设计与评估</em>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/language-TypeScript-007ACC?style=flat-square" alt="TypeScript" />
  <img src="https://img.shields.io/badge/language-Python-3776AB?style=flat-square" alt="Python" />
  <img src="https://img.shields.io/badge/runtime-Bun-000000?style=flat-square" alt="Bun" />
  <img src="https://img.shields.io/badge/shell-PowerShell-5391FE?style=flat-square" alt="PowerShell" />
</p>

<p align="center">
  <a href="README.md">English</a> •
  <a href="README.fr.md">Français</a> •
  <a href="README.es.md">Español</a> •
  <a href="README.zh.md">中文</a> •
  <a href="README.ja.md">日本語</a>
</p>

---

## 什么是 MemoriX？

**MemoriX** 是一个为基于LLM的自主编码智能体（如 OpenCode）设计的高级持久内存系统。它将智能体的内存从简单的存储挑战从根本上转变为结构化的**知识治理**问题。它提供明确的准入控制、逻辑遗忘、严格的项目隔离和安全的饱和行为。

---

## 系统架构

MemoriX 受到人类记忆模型的启发，并强制执行严格的生命周期：**观察 → 提议 → 验证 → 检索 → 更新 → 遗忘**。

1. **短期记忆 (STM)**：瞬态日志。
2. **冷站点 (历史存档)**：用于审计的仅追加存档。
3. **项目存档**：结构化项目里程碑。
4. **候选存储 (验证边界)**：等待验证的知识暂存区。
5. **Titan 热站点 (活跃内存)**：检索期间查询的唯一活跃内存系统。

---

## 基准测试与性能

MemoriX 通过严格的 A/B 基准测试进行了评估（使用 `qwen2.5:3b` 在 32 个任务系列中运行 2,048 次）。

### 1. 总体 A/B 基准测试结果

| 指标 | 无内存 | MemoriX | Δ |
| ---- | ------ | ------- | - |
| **总体通过率** | 31.9% (327/1024) | 60.0% (614/1024) | **+28.0pp** |
| **中位数延迟** | 3,384 ms | 3,504 ms | +120 ms |
| **评估系列** | 32 | 32 | — |
| **获胜系列** (Δ > 0) | — | 12 | — |
| **失败系列** (Δ < 0) | — | 4 | — |

### 2. 多智能体 SDLC 工作流

评估跨不同智能体角色的任务成功率，同时严格防止信息泄漏。

| 指标 | 无内存 | MemoriX | Delta |
| ---- | ------ | ------- | ----- |
| **任务成功率** | 25.0% | 37.5% | **+12.5pp** |
| **违规信息使用** | 0.0% | 0.0% | **完美隔离** |
| **工具调用** | 5,000 | 8,750 | — |
| **平均响应时间** | N/A | 257.3 ms | — |

### 3. 基于 BFCL 的检索评估

对检索机制的独立质量评估。

| 阶段 | 结果 | 比率 |
| ---- | ---- | ---- |
| 正确基线 | 0/125 | 0% |
| 语料库包含引用 | 125/125 | 100% |
| 检索包含引用 | 96/125 | **76.8%** |
| 正确的最终答案 | 96/125 | **76.8%** |

### 4. 容量饱和行为

测试内存系统对不断增加的负载和极端超载的反应。

| 活跃项目 | 允许进入 | 压力等级 | 使用率 | 决策延迟 |
| -------- | -------- | -------- | ------ | -------- |
| 10,000 | ✅ | 稳定 | 0.2 | 0.0013 ms |
| **50,000** | ❌ | **关键** | **1.0** | **0.0009 ms** |
| 500,000 | ❌ | 关键 | 10.0 | 0.0024 ms |
| 6,000,000 | ❌ | 关键 | 120.0 | 0.0023 ms |

*注：一旦达到 50,000 的容量限制，MemoriX 优雅地拒绝溢出（❌），而不是静默覆盖现有的记忆，同时保持亚毫秒级的决策延迟。*

---

## 完整安装指南 (从 A 到 Z)

本指南将引导您从零开始安装 MemoriX 和 OpenCode。

### 第 1 步：环境要求

1. **Git**: 用于下载代码。 [git-scm.com](https://git-scm.com/)
2. **Node.js & Bun**: 用于运行 OpenCode。
   - 在 PowerShell 中安装 Bun:
     ```powershell
     powershell -c "irm bun.sh/install.ps1 | iex"
     ```
3. **Python 3.10 或更高版本**: Titan 内存后端需要。
   - [python.org](https://www.python.org/downloads/)
   - **重要提示**：安装时务必勾选 **"Add Python to PATH"**。

### 第 2 步：克隆存储库

打开终端 (推荐 PowerShell)：

```powershell
cd C:\您的文件夹
git clone https://github.com/anomalyco/memoriX.git
cd memoriX
```

### 第 3 步：安装 JavaScript 依赖项

```powershell
bun install
```

### 第 4 步：验证 Python 环境

使用预验证脚本检查配置：

```powershell
.\tools\memorix\runtime\start_opencode_with_memorix.ps1
```
如果成功，您应该会看到 `MemoriXGateway import OK`。

### 第 5 步：启动系统！

运行以下命令即可开始：

```powershell
.\tools\memorix\runtime\start_opencode_with_memorix.ps1
```

---

## 附加文档
- [详细架构](docs/MEMORIX_FINAL_ARCHITECTURE.md)
- [操作手册](docs/MEMORIX_OPERATIONS.md)
