プロジェクト仕様書：vrphoto-checker (Standalone Edition)
VRChatの出展物やスクリーンショットを、ローカルVLM（LM Studio経由のVision Language Model）を用いてリアルタイムに検閲・監査する、外部依存を極限まで排除したポータブル・システム。

1. コンセプト
「自作アバターの露出確認」や「ブース内の規約違反チェック」を、クラウドを介さず自分のPC内だけで完結させる。外部ライブラリを最小限に抑えることで、環境構築の手間（pip install 等）を減らし、安定したポータブルな監査環境を提供する。

2. システムアーキテクチャ
2.1 モジュール構成
Audit Watcher (標準 pathlib, os 使用):
VRChatのスクショフォルダを定期監視。外部ライブラリ watchdog を使わず、軽量なポーリング方式を採用。

LM Studio VLM Engine (auditor.py):
画像を Vision Language Model（VLM）で審査するエンジン。
- **使用ツール**: LM Studio（`lms` CLI 経由で自動起動）
- **デフォルトモデル**: `google/gemma-4-26b-a4b`（config.json で変更可能）
- **API**: LM Studio が公開する OpenAI 互換エンドポイント (`http://localhost:1234/v1/chat/completions`)
- **処理フロー**:
  1. `auditor.py` 起動時に LM Studio サーバーの稼働を確認。未起動なら `lms server start` を自動実行。
  2. 画像を最大 1024x1024 にリサイズし、JPEG として base64 エンコード（HTTP 400 時は 512x512 にダウングレードして再試行）。
  3. `rules.md` の内容をシステムプロンプトとして渡し、画像の審査結果（OK/NG と根拠）を JSON で返させる。
- **設定項目** (`config.json`):
  - `ai_api_url`: LM Studio エンドポイント URL
  - `ai_model`: 使用モデル名
  - `ai_timeout`: API タイムアウト（秒）

Database (標準 sqlite3 使用):
判定結果（PASS/FAIL）、AIの根拠、タイムスタンプを永続化。

Censorship Dashboard (標準 http.server 使用):
設定変更や履歴閲覧のためのWebUIを、Python標準のHTTPサーバーでホスト。

3. ディレクトリ構造
Plaintext
vrphoto-checker/
├── vrphoto-checker.py   # アプリ起動・監視スレッド管理
├── config.json          # 監視パス・モデル設定 (JSON)
├── rules.md             # 監査ルール定義 (Markdown) - 判断基準はここに集約
├── core/
│   ├── watcher.py       # フォルダ監視エンジン
│   ├── auditor.py       # 監査統括（Local Safety Engine 呼び出し -> LM Studio VLM）

│   ├── notifier.py      # Windows トースト通知 (ctypes)
│   └── database.py      # SQLite3 ログ管理
├── web/
│   ├── server.py        # http.server による簡易API
│   └── index.html       # Vanilla JSによる管理画面
└── logs/
    └── history.db       # 判定履歴データベース
4. 詳細設計仕様
4.1 監査プロセス (The Audit Loop)
検知: watcher.py が新規 .png または .jpg を発見。

待機: 書き込み完了を待つため数秒ディレイを挟み、ハッシュまたはサイズで整合性を確認。

推論要求 (LM Studio VLM Engine):

画像を auditor.py に渡す。

必要に応じて画像をリサイズ（メモリ節約・高速化）。

画像をベース64エンコードし、LM Studio (Gemma 4) へ送信。

判定解析:
- VLMの判定（JSON）が "NG" の場合 -> **FAIL** (即NG)
- それ以外 -> **PASS**

4.2 監査ルールファイル (rules.md)
ユーザーが「何を検閲すべきか」を記述するが、Local Engineは以下のカテゴリを重点的にチェックする。

Markdown
# 重点監査項目

## [絶対禁止: FAIL]
- **ヘイトシンボル**: ナチス(Swastika, SS), KKK, その他政治的過激派の象徴。
- **商標・侵害**: 企業のロゴ、有名なキャラクター（商用利用リスクの排除）。

5. ユーザーインターフェース (UI)
5.1 通知機能
外部通知ライブラリを使わず、ctypes 経由で Windows API を直接叩き、システムトレイ通知（トースト）を表示。

PASS: 静かにログ保存。

FAIL: 音と共に「規約違反の可能性あり」と通知。

5.2 Webダッシュボード
http://localhost:8080 で動作。

履歴画面: 判定された画像の一覧と、AIによる「なぜNGか」の解説を表示。

設定画面: 監視パスの変更、rules.md のオンライン編集。

6. 技術的な制約と対策
VRAM競合回避:
VRChatとGPUを奪い合わないよう、LM Studio側で適切にVRAMのオフロード設定を行うか、軽いモデルを選定する。

依存関係:
Python 3.10以降。
追加ライブラリ: **pillow, requests**
外部ソフトウェア: **LM Studio**（`lms` CLI が PATH または標準インストールパスに存在すること）
※極力標準ライブラリで構成するが、画像認識エンジンと LM Studio HTTP 通信のみ最小限の外部ライブラリを使用。

7. 開発ロードマップ
Phase 1: LM Studio API連携の実装。

Phase 2: 画像リサイズと処理パイプラインの最適化（高速化）。

Phase 3: 誤検知（False Positive）抑制のためのプロンプト調整。

Phase 4: UIへの結果統合と通知機能。