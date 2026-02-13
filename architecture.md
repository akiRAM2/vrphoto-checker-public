プロジェクト仕様書：vrphoto-checker (Standalone Edition)
VRChatの出展物やスクリーンショットを、ローカルLLM（Gemma 3）を用いてリアルタイムに検閲・監査する、外部依存を極限まで排除したポータブル・システム。

1. コンセプト
「自作アバターの露出確認」や「ブース内の規約違反チェック」を、クラウドを介さず自分のPC内だけで完結させる。外部ライブラリを最小限に抑えることで、環境構築の手間（pip install 等）を減らし、安定したポータブルな監査環境を提供する。

2. システムアーキテクチャ
2.1 モジュール構成（標準ライブラリ主体）
Audit Watcher (標準 pathlib, os 使用):
VRChatのスクショフォルダを定期監視。外部ライブラリ watchdog を使わず、軽量なポーリング方式を採用。

Inference Client (標準 urllib.request 使用):
Ollama等のローカルAPIサーバーと通信。Base64エンコードされた画像を送信し、Gemma 3の視覚能力で検閲を実行。

Database (標準 sqlite3 使用):
判定結果（PASS/FAIL）、AIの根拠、タイムスタンプを永続化。

Censorship Dashboard (標準 http.server 使用):
設定変更や履歴閲覧のためのWebUIを、Python標準のHTTPサーバーでホスト。

3. ディレクトリ構造
Plaintext
vrphoto-checker/
├── main.py              # アプリ起動・監視スレッド管理
├── config.json          # 監視パス・モデル設定 (JSON)
├── rules.md             # 監査ルール定義 (Markdown)
├── core/
│   ├── watcher.py       # フォルダ監視エンジン
│   ├── auditor.py       # Gemma 3 通信・判定ロジック
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

推論要求:

rules.md のテキストをシステムメッセージとして読み込み。

画像を base64 変換し、urllib.request を用いて Ollama 等の推論サーバーに POST。

判定解析: AIが返すJSONレスポンスを解析し、判定結果を抽出。

4.2 監査ルールファイル (rules.md)
ユーザーが「何を検閲すべきか」を自然言語で記述する。

Markdown
# 監査基準

## [絶対禁止: FAIL]
- **ネームタグ**: 他人のユーザーネームプレートが判別できる。
- **テクスチャ不備**: アバターのメッシュが突き抜けて肌が露出している。
- **UI露出**: ソーシャルメニューやチャットログが表示されている。

## [条件付き許可: PASS]
- **自アバター**: 規約に準じた衣装を着用している全身像。
- **公式ロゴ**: VRChatおよびイベント公式ロゴ。
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
VRChatとGPUを奪い合わないよう、config.json でモデルの量子化（4-bit以下推奨）と、CPUへのレイヤーオフロード設定を調整可能にする。

依存関係:
Python 3.10以降の標準配布物のみ。
※AI推論サーバー（Ollama等）は別途ローカルで稼働していることを前提とする。

7. 開発ロードマップ
Phase 1: urllib を用いた Gemma 3 へのプロンプト送信テスト。

Phase 2: os.scandir によるフォルダ監視と SQLite3 への記録。

Phase 3: http.server と HTML による管理画面の実装。

Phase 4: ctypes による Windows トレイ通知の統合。