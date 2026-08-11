# MemoriX

<p align="center">
  <em>基于大型语言模型（LLM）的代码智能体的受控持久内存系统的设计与评估</em>
</p>

<p align="center">
  <a href="README.md">English</a> •
  <a href="README.fr.md">Français</a> •
  <a href="README.es.md">Español</a> •
  <a href="README.zh.md">中文</a> •
  <a href="README.ja.md">日本語</a>
</p>

---

## 📖 什么是 MemoriX？

**MemoriX** 是一个为基于LLM的自主编码智能体（如 OpenCode）设计的高级持久内存系统。它将智能体的内存从简单的存储挑战从根本上转变为结构化的**知识治理**问题。它提供明确的准入控制、逻辑遗忘、严格的项目隔离和安全的饱和行为。

---

## 🧠 系统架构

MemoriX 受到人类记忆模型的启发，并强制执行严格的生命周期：**观察 → 提议 → 验证 → 检索 → 更新 → 遗忘**。

1. **短期记忆 (STM)**：瞬态日志。
2. **冷站点 (历史存档)**：用于审计的仅追加存档。
3. **项目存档**：结构化项目里程碑。
4. **候选存储 (验证边界)**：等待验证的知识暂存区。
5. **Titan 热站点 (活跃内存)**：检索期间查询的唯一活跃内存系统。

---

## 🚀 基准测试与性能

通过严格的 A/B 基准测试（32 个任务系列中的 2,048 次运行）：
- **+28.0% 通过率**：从 31.9% 提升至 60.0%。
- **完美隔离**：零信息泄漏。
- **安全饱和度**：已成功测试至 6,000,000 个活跃项目。

---

## 📦 完整安装指南 (从 A 到 Z)

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
   - ⚠️ **重要提示**：安装时务必勾选 **"Add Python to PATH"**。

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
.\tools\memorix\runtime\start_opencode_with_memorix.ps1 -ValidateOnly
```
如果成功，您应该会看到 `MemoriXGateway import OK`。

### 第 5 步：启动系统！

运行以下命令即可开始：

```powershell
.\tools\memorix\runtime\start_opencode_with_memorix.ps1
```

---

## 📖 附加文档
- [详细架构](docs/MEMORIX_FINAL_ARCHITECTURE.md)
- [操作手册](docs/MEMORIX_OPERATIONS.md)
