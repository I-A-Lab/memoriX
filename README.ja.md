<h1 align="center">MemoriX</h1>

<p align="center">
  <em>LLMベースのコードエージェントのための制御された永続メモリシステムの設計と評価</em>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/TypeScript-007ACC?style=for-the-badge&logo=typescript&logoColor=white" alt="TypeScript" />
  <img src="https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python" />
  <img src="https://img.shields.io/badge/Bun-000000?style=for-the-badge&logo=bun&logoColor=white" alt="Bun" />
  <img src="https://img.shields.io/badge/PowerShell-5391FE?style=for-the-badge&logo=powershell&logoColor=white" alt="PowerShell" />
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

厳密な A/B ベンチマークを通じて評価されました：
- **+28.0% 成功率向上**: 31.9% から 60.0% へ。
- **完全な分離**: 情報漏洩ゼロ。
- **安全な飽和**: 最大6,000,000のアクティブアイテムまでテスト済み。

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
