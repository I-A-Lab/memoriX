<h1 align="center">Memory AGENTX</h1>

<p align="center">
  <em>LLMベースのコードエージェントのための制御された永続メモリシステムの設計と評価</em>
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

## MemoriX とは？

**MemoriX** は、自律型コーディングエージェント（OpenCodeなど）向けに設計された高度な永続メモリシステムです。エージェントのメモリを単純なストレージの課題から、構造化された**知識ガバナンス**の問題へと根本的に移行させます。

---

## システムアーキテクチャ

システムは人間の記憶モデルに触発されており、**観察 → 提案 → 検証 → 検索 → 更新 → 忘却**という厳密なライフサイクルを強制します。

1. **短期メモリ (STM)**: 一時的な履歴。
2. **コールドサイト (Cold Site)**: 監査可能性のための追記専用アーカイブ。
3. **プロジェクトアーカイブ**: 構造化されたプロジェクトのマイルストーン。
4. **候補ストア (Candidate Store)**: 提案された知識の検証待ちエリア。
5. **Titan ホットサイト (Hot Site)**: 検索に使用されるアクティブな検証済みメモリ。

---

## ベンチマークとパフォーマンス

MemoriXは、厳密なA/Bベンチマークを通じて評価されました（`qwen2.5:3b` を使用し、32のタスクファミリーで2,048回実行）。

### 1. 全体的な A/B ベンチマーク結果

| メトリック | メモリなし | MemoriX | Δ |
| ---------- | ---------- | ------- | - |
| **全体成功率** | 31.9% (327/1024) | 60.0% (614/1024) | **+28.0pp** |
| **遅延中央値** | 3,384 ms | 3,504 ms | +120 ms |
| **評価ファミリー** | 32 | 32 | — |
| **勝ったファミリー** (Δ > 0) | — | 12 | — |
| **負けたファミリー** (Δ < 0) | — | 4 | — |

### 2. マルチエージェント SDLC ワークフロー

情報漏洩を厳密に防ぎながら、異なるエージェント役割にわたるタスクの成功を評価します。

| メトリック | メモリなし | MemoriX | Delta |
| ---------- | ---------- | ------- | ----- |
| **タスク成功率** | 25.0% | 37.5% | **+12.5pp** |
| **禁止情報の使用** | 0.0% | 0.0% | **完全な分離** |
| **ツール呼び出し** | 5,000 | 8,750 | — |
| **平均応答時間** | N/A | 257.3 ms | — |

### 3. BFCL ベースの検索評価

検索品質メカニズムの独立した評価。

| ステージ | 結果 | レート |
| -------- | ---- | ------ |
| 正しいベースライン | 0/125 | 0% |
| コーパスに参照を含む | 125/125 | 100% |
| 検索に参照を含む | 96/125 | **76.8%** |
| 正しい最終回答 | 96/125 | **76.8%** |

### 4. 容量の飽和状態の挙動

増大する負荷と極端な過負荷に対するメモリシステムの反応をテストします。

| アクティブアイテム | 受け入れ許可 | 圧力レベル | 使用率 | 決定遅延 |
| ------------------ | ------------ | ---------- | ------ | -------- |
| 10,000 | ✅ | 安定 | 0.2 | 0.0013 ms |
| **50,000** | ❌ | **臨界** | **1.0** | **0.0009 ms** |
| 500,000 | ❌ | 臨界 | 10.0 | 0.0024 ms |
| 6,000,000 | ❌ | 臨界 | 120.0 | 0.0023 ms |

*注：容量制限（50,000）に達すると、MemoriX は既存のメモリを暗黙のうちに上書きするのではなく、オーバーフローをエレガントに拒否（❌）し、ミリ秒未満の決定レイテンシを維持します。*

---

## 完全なインストールガイド (A から Z)

このガイドでは、MemoriX と OpenCode をゼロからインストールする手順を説明します。

### ステップ 1: 前提条件

1. **Git**: コードをダウンロードするため。 [git-scm.com](https://git-scm.com/)
2. **Node.js と Bun**: OpenCode を実行するため。
   - PowerShell で Bun をインストール:
     ```powershell
     powershell -c "irm bun.sh/install.ps1 | iex"
     ```
3. **Python 3.10 以上**: Titan バックエンドに必要。
   - [python.org](https://www.python.org/downloads/)
   - **重要**: インストール時に **"Add Python to PATH"** にチェックを入れてください。

### ステップ 2: リポジトリのクローン

PowerShell を開きます:

```powershell
cd C:\Your\Folder
git clone https://github.com/anomalyco/memoriX.git
cd memoriX
```

### ステップ 3: JavaScript 依存関係のインストール

```powershell
bun install
```

### ステップ 4: Python 環境の確認

検証スクリプトを実行します:

```powershell
.\tools\memorix\runtime\start_opencode_with_memorix.ps1 -ValidateOnly
```
成功すると `MemoriXGateway import OK` と表示されます。

### ステップ 5: システムの起動！

検証が成功したら、以下を実行します:

```powershell
.\tools\memorix\runtime\start_opencode_with_memorix.ps1
```

---

## ドキュメント
- [詳細アーキテクチャ](docs/MEMORIX_FINAL_ARCHITECTURE.md)
- [操作マニュアル](docs/MEMORIX_OPERATIONS.md)
