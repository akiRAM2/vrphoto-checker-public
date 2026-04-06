# Release Notes

## v1.1 — Gemma 4 対応 / OpenCLIP 削除 (2026-04-06)

### 🎉 ハイライト

**画像審査エンジンを Gemma 4（VLM）に完全一本化しました。**
これまで使用していた OpenCLIP（PyTorch ベースのシンボルチェック）を廃止し、LM Studio 上の Vision Language Model だけで全ての審査を行うシンプルなアーキテクチャに刷新しています。

### ✨ 変更点

#### アーキテクチャの刷新
- **OpenCLIP / PyTorch 依存を完全に削除**
  - `core/safety_checker.py`（CLIPベースのシンボルチェッカー）を廃止
  - `torch` / `open_clip_torch` の依存を削除
  - 外部依存が **Pillow のみ** になり、セットアップが大幅に簡素化
- **審査フローの一本化**
  - 旧: CLIP シンボルチェック → VLM 詳細分析の2段階
  - 新: Gemma 4（VLM）による1段階審査
  - 画像内容の理解もシンボル検出も1回の推論で完結

#### AI モデル対応
- **デフォルトモデルを `google/gemma-4-26b-a4b` に変更**
- LM Studio `lms` CLI による自動サーバー起動 & モデルロード機能を追加
- コンテキスト長 8192 で自動ロード（安定動作のため）

#### 信頼性向上
- 画像処理失敗時の自動リトライ（1024→512 ダウンスケール）
- HTTP 400 エラー時のインテリジェントなフォールバック

### 📦 依存関係の変更

| パッケージ | v1.0 | v1.1 |
|-----------|------|------|
| `Pillow` | ✅ | ✅ |
| `torch` | ✅ (約2GB) | ❌ **削除** |
| `open_clip_torch` | ✅ | ❌ **削除** |

### 🚀 アップグレード方法

1. 最新版をダウンロード or `git pull`
2. `pip install -r requirements.txt`（Pillow のみ）
3. LM Studio で `google/gemma-4-26b-a4b` をダウンロード & ロード
4. `config.json` はそのまま使用可能（`ai_model` のデフォルトが変わっていますが、既存設定がある場合はそちらが優先されます）

### ⚠️ 破壊的変更

- `core/safety_checker.py` を削除。このモジュールを直接参照していたカスタムコードがある場合は修正が必要です
- PyTorch / OpenCLIP に依存していた独自拡張は動作しなくなります

---

## v1.0 — Initial Release (2026-03-23)

- VRChat スクリーンショットのリアルタイム監視と AI 審査
- OpenCLIP によるシンボルチェック + VLM による詳細審査の2段階方式
- Web ダッシュボード（履歴閲覧・ルール編集）
- Windows トースト通知
- SQLite による審査履歴の永続化
