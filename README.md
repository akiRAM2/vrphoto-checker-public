# VRPhoto Checker

VRChat のスクリーンショットフォルダを監視し、ローカル AI（[LM Studio](https://lmstudio.ai/)）を使って画像を自動審査するツールにゃ。

クラウドへの画像送信は一切なく、完全ローカルで動作するため、プライバシーを保ちながら利用できるにゃ。

## 主な機能

- **自動監視**: VRChat フォトフォルダに追加された新しい画像をリアルタイムで検出
- **ローカル AI 審査**: LM Studio + ビジョン対応モデル（Qwen3-VL など）で画像を分析
- **シンボルチェック**: AI 送信前に専用モデルでヘイトシンボル・商標を事前スクリーニング
- **ポリシー適用**: `rules.md` に定義したルールに基づいて以下を審査:
  - **性的コンテンツ**: 露出・性行為など
  - **著作権侵害**: 無断キャラクター使用（ポケモン・Disney など）
  - **ヘイトシンボル**: 禁止されたアイコン・記号
  - **暴力・違法物品**: 血液描写、薬物など
- **Web ダッシュボード**: ブラウザで審査ログと画像を確認
- **デスクトップ通知**: 違反の可能性がある画像を Windows 通知でアラート
- **自動リトライ**: LM Studio がコンテキスト不足で画像処理に失敗した場合、自動で画像を縮小して再送信

## 必要環境

- **OS**: Windows 10 / 11
- **Python**: 3.10 以上
- **LM Studio**: インストール済みでローカルサーバーが起動していること → [ダウンロード](https://lmstudio.ai/)
- **Python パッケージ**: `Pillow`、`transformers`、`torch`（`pip install -r requirements.txt` でインストール）

## セットアップ

### 1. リポジトリのクローン

```bash
git clone https://github.com/akiRAM2/vrphoto-checker.git
cd vrphoto-checker
```

### 2. Python パッケージのインストール

```bash
pip install Pillow transformers torch
```

### 3. LM Studio の準備

1. [LM Studio](https://lmstudio.ai/) をダウンロード・インストール
2. ビジョン対応モデルをダウンロード（推奨: **Qwen3-VL-4B** Q4_K_M）
3. LM Studio でモデルを読み込み、ローカルサーバーを起動（デフォルト: `http://localhost:1234`）
4. **コンテキスト長の設定（推奨）**: モデル設定の **Context Length** を `8192` 以上に設定するとエラーが発生しにくくなる

### 4. `config.json` の設定

```json
{
    "watch_path": "C:\\Users\\YourName\\Pictures\\VRChat",
    "ai_api_url": "http://localhost:1234/v1/chat/completions",
    "ai_model": "qwen/qwen3-vl-4b",
    "ai_timeout": 180,
    "poll_interval": 5,
    "port": 8080
}
```

| キー | 説明 | デフォルト |
|------|------|-----------|
| `watch_path` | 監視するフォルダのパス | `Pictures/VRChat` |
| `ai_api_url` | LM Studio の API エンドポイント | `http://localhost:1234/v1/chat/completions` |
| `ai_model` | 使用するモデル名（LM Studio 上の ID） | `qwen/qwen3-vl-4b` |
| `ai_timeout` | AI 推論のタイムアウト秒数 | `180` |
| `poll_interval` | フォルダのポーリング間隔（秒） | `5` |
| `port` | Web ダッシュボードのポート番号 | `8080` |

### 5. アプリケーションの起動

```bash
python main.py
```

起動後、ブラウザで `http://localhost:8080` にアクセスするとダッシュボードが表示される。

## 審査フロー

```
新しい画像を検出
    │
    ▼
[シンボルチェック] ─── NG ──→ アラート通知
    │ PASS
    ▼
[AI 画像解析] (LM Studio / Qwen3-VL)
    │ 400エラー (画像処理失敗)
    ├──→ [自動リトライ: 512x512 で再送信]
    │         │
    │         ▼
    │     成功 or エラー
    ▼
審査結果 (OK / NG / ERROR)
    │ NG or ERROR
    ▼
デスクトップ通知 + DB 保存
```

## 審査ルールのカスタマイズ

`rules.md` を編集することで審査基準を変更できる。アプリを再起動せずに、次回審査時から反映される。

## トラブルシューティング

| 症状 | 対処 |
|------|------|
| `AI サーバー HTTP エラー: 400` | LM Studio の Context Length を増やす（8192 以上推奨）。アプリが自動で縮小リトライを行う |
| `AI 推論タイムアウト` | `config.json` の `ai_timeout` を増やす（180〜300 推奨） |
| ポート競合エラー | `config.json` の `port` を別の番号に変更する |
| LM Studio に接続できない | LM Studio のローカルサーバーが起動しているか確認する |

## 免責事項

本ツールは AI モデルによる自動分析を行います。AI はエラーやハルシネーションを起こす場合があります。審査結果はあくまで参考情報として利用してください。
