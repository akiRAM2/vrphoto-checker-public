# VRPhoto Checker

VRChat のスクリーンショットフォルダを監視し、ローカル AI（[LM Studio](https://lmstudio.ai/)）を使って画像を自動審査するツール。

クラウドへの画像送信は一切なく、完全ローカルで動作するため、プライバシーを保ちながら利用できる。

## 主な機能

- **自動監視**: VRChat フォトフォルダに追加された新しい画像をリアルタイムで検出
- **ローカル AI 審査**: LM Studio + ビジョン対応モデル（Qwen3-VL など）で画像を分析
- **シンボルチェック**: AI 送信前に CLIP モデルでヘイトシンボル・商標を事前スクリーニング
- **ポリシー適用**: `rules.md` に定義したルールに基づいて以下を審査:
  - **性的コンテンツ**: 露出・性行為など
  - **著作権侵害**: 無断キャラクター使用（ポケモン・Disney など）
  - **ヘイトシンボル**: 禁止されたアイコン・記号
  - **暴力・違法物品**: 血液描写、薬物など
- **Web ダッシュボード**: ブラウザで審査ログと画像を確認
- **デスクトップ通知**: 違反の可能性がある画像を Windows 通知でアラート
- **自動リトライ**: LM Studio がコンテキスト不足で画像処理に失敗した場合、自動で画像を縮小して再送信

---

## 必要環境

| 項目 | 要件 |
|------|------|
| OS | Windows 10 / 11 |
| Python | 3.10 以上 |
| LM Studio | 最新版（ビジョン対応モデルのローカルサーバー起動が必要） |
| VRAM / RAM | シンボルチェック (CLIP): CPU で動作。LM Studio 側は 4B モデルで 4GB VRAM 以上推奨 |

---

## セットアップ

### 1. リポジトリのクローン

```bash
git clone https://github.com/akiRAM2/vrphoto-checker.git
cd vrphoto-checker
```

---

### 2. Python パッケージのインストール

このツールが使用する外部ライブラリは以下の 3 つ。それ以外はすべて Python 標準ライブラリ。

| ライブラリ | 用途 | バージョン目安 |
|-----------|------|--------------|
| `Pillow` | 画像の読み込み・リサイズ・JPEG 変換 | 10.0 以上 |
| `open_clip_torch` | シンボルチェック用の CLIP モデル読み込み | 2.24 以上 |
| `torch` | CLIP モデルの実行エンジン（PyTorch） | 2.0 以上 |

**インストール手順:**

```bash
pip install -r requirements.txt
```

または個別にインストールする場合:

```bash
pip install Pillow open_clip_torch torch
```

> **GPU を使わない場合（CPU のみ）**
>
> PyTorch はデフォルトで CUDA 対応版がインストールされることがある。
> CPU 版で十分な場合（シンボルチェックは CPU 動作のみ）は以下のコマンドで CPU 専用の軽量版を取得できる:
>
> ```bash
> pip install torch --index-url https://download.pytorch.org/whl/cpu
> pip install Pillow open_clip_torch
> ```

> **仮想環境を推奨**
>
> システム環境を汚染しないよう venv の使用を推奨する:
>
> ```bash
> python -m venv venv
> venv\Scripts\activate
> pip install -r requirements.txt
> ```

> **`transformers` は不要**
>
> 古い情報や別ツールと混同して `transformers` をインストールする必要はない。このツールでは使用していない。

---

### 3. LM Studio のインストールと設定

#### 3-1. LM Studio のインストール

[https://lmstudio.ai/](https://lmstudio.ai/) からインストーラーをダウンロードして実行する。

#### 3-2. ビジョン対応モデルのダウンロード

LM Studio の「Discover」タブで以下のモデルを検索してダウンロードする。

| モデル | 推奨量子化 | VRAM 目安 | 備考 |
|--------|-----------|----------|------|
| **Qwen3-VL-4B** | Q4_K_M | 4GB | 推奨。速度と品質のバランスが良い |
| Qwen2.5-VL-7B | Q4_K_M | 8GB | より高精度だが重い |

#### 3-3. ローカルサーバーの起動

1. LM Studio の左メニューから「Local Server」を開く
2. 画面上部でダウンロードしたモデルを選択し「Load Model」をクリック
3. 「Start Server」をクリック（デフォルトポート: `1234`）

#### 3-4. コンテキスト長の設定（推奨）

モデルロード時、または「Model Settings」から **Context Length を `8192` 以上** に設定する。
設定が低すぎると画像処理時に HTTP 400 エラーが発生する（アプリが自動で縮小リトライするが、設定しておくと安定する）。

> **lms CLI によるコマンドライン操作について**
>
> LM Studio 0.3 以降では `lms` コマンドラインツールが同梱されている。
> このツールはアプリ起動時に LM Studio のサーバー起動とモデルロードを `lms` CLI 経由で自動化しようとする。
> `lms` が見つからない場合は自動化をスキップし、手動で LM Studio を操作する必要がある。

---

### 4. `config.json` の設定

初回起動時に自動生成されるが、以下を参考に必要な箇所を編集する。

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

| キー | 説明 | デフォルト値 |
|------|------|------------|
| `watch_path` | 監視するフォルダのパス | `~/Pictures/VRChat` |
| `ai_api_url` | LM Studio の API エンドポイント | `http://localhost:1234/v1/chat/completions` |
| `ai_model` | LM Studio にロードしたモデルの ID（LM Studio の「Loaded Models」に表示される名前） | `qwen/qwen3-vl-4b` |
| `ai_timeout` | AI 推論のタイムアウト秒数。重いモデルや低スペック PC では増やす | `180` |
| `poll_interval` | フォルダのポーリング間隔（秒） | `5` |
| `port` | Web ダッシュボードのポート番号 | `8080` |

> **`ai_model` の確認方法**
>
> LM Studio の「Local Server」画面でモデルをロードした後、
> `http://localhost:1234/v1/models` にブラウザでアクセスすると利用可能なモデル ID の一覧が JSON で表示される。
> その `id` フィールドの値を `config.json` の `ai_model` にそのままコピーする。

---

### 5. 審査ルールのカスタマイズ（任意）

`rules.md` を編集することで審査基準を変更できる。アプリを再起動せずに、次回審査時から反映される。

---

### 6. アプリケーションの起動

```bash
python main.py
```

起動後、自動でブラウザが開きダッシュボード（`http://localhost:8080`）が表示される。

---

## 審査フロー

```
新しい画像を検出
    │
    ▼
[シンボルチェック] (CLIP / ViT-B-32 モデル / CPU)
    │  NG (ヘイトシンボル・商標ロゴ検出)
    ├──────────────────→ アラート通知 + DB 保存
    │ PASS
    ▼
[AI 画像解析] (LM Studio / Qwen3-VL)
    │  HTTP 400 (画像処理失敗 / コンテキスト不足)
    ├──→ [自動リトライ: 512x512 に縮小して再送信]
    │         │
    │         ▼ 成功 or 再度エラー
    ▼
審査結果 (OK / NG / ERROR)
    │  NG または ERROR
    ▼
デスクトップ通知 + DB 保存
```

---

## トラブルシューティング

| 症状 | 原因 | 対処 |
|------|------|------|
| `AI サーバー HTTP エラー: 400` | LM Studio のコンテキスト長不足 | LM Studio のモデル設定で Context Length を `8192` 以上に増やす。アプリが自動で 512x512 に縮小リトライする |
| `AI 推論タイムアウト` | PC スペック不足またはモデルが重い | `config.json` の `ai_timeout` を `300` 以上に増やす。より軽いモデル（4B 以下）を使用する |
| `LM Studio が起動していません` | サーバーが未起動 | LM Studio を起動し「Local Server」からサーバーを開始する |
| モデルが見つからない | `ai_model` の ID が違う | `http://localhost:1234/v1/models` で表示された `id` を `config.json` にコピーする |
| ポート競合エラー | 8080 番が使用中 | `config.json` の `port` を `8081` などに変更する |
| `open_clip` のインストールエラー | パッケージ名の間違い | `open_clip` ではなく `open_clip_torch` が正しいパッケージ名。`pip install open_clip_torch` を実行する |
| PyTorch のインストールが重い | CUDA 版が自動選択されている | CPU 専用版をインストールする: `pip install torch --index-url https://download.pytorch.org/whl/cpu` |
| シンボルチェックモデルのダウンロードに時間がかかる | 初回起動時に CLIP モデルを自動ダウンロードする | 初回のみ数百 MB のダウンロードが発生する。2 回目以降はキャッシュが使われる |

---

## 免責事項

本ツールは AI モデルによる自動分析を行います。AI はエラーやハルシネーションを起こす場合があります。審査結果はあくまで参考情報として利用してください。
