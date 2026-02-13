# VRPhoto Checker (Standalone Edition)

VRChatのスクリーンショットをローカルAI（Gemma 3）で自動的に監査し、「自作アバターの露出確認」や「UI映り込みチェック」を行うツールです。
クラウドにアップロードせず、あなたのPC内だけですべて完結します。

## 🚀 特徴
- **完全ローカル動作**: 画像がネットに流出するリスクはありません。
- **Gemma 3 (via Ollama)**: 最新の軽量高性能モデルで画像を視覚的に理解します。
- **超軽量**: 外部ライブラリほぼ不要。Python標準機能で動作します。

## 📦 導入方法 (Getting Started)

### 1. 前提条件: Ollamaのインストール
このツールはAIエンジンとして「Ollama」を使用します。まだ持っていない場合はインストールしてください。

1. [Ollama公式サイト](https://ollama.com/) からダウンロードしてインストール。
2. インストール後、コマンドプロンプト（PowerShell）を開き、以下のコマンドでAIモデルを準備します。

```powershell
ollama pull gemma3:4b
```
※ 本ツールは `gemma3` 系モデルを前提としています。`gemma3:1b` (軽量) や `gemma3:12b` (高精度) も利用可能です。

### 2. インストール
このリポジトリを適当な場所に保存します。

```powershell
git clone <repository-url>
cd vrphoto-checker
```

### 3. 設定 (config.json)
初回起動時に `config.json` が自動生成されますが、必要に応じて編集してください。
特に `watch_path` (監視するフォルダ) はあなたのVRChatスクショ保存先に合わせてください。

```json
{
    "watch_path": "C:\\Users\\User\\Pictures\\VRChat", 
    "ai_api_url": "http://localhost:11434/api/generate",
    "ai_model": "gemma3:4b",
    "poll_interval": 5,
    "port": 8080
}
```
※ Windowsのパス区切り文字 `\` は `\\` と記述する必要があります。

## 使い方

### プログラムの実行
フォルダ内の `main.py` を実行するだけです。

```powershell
python main.py
```

起動時、自動的に以下のチェックが行われます：
- Ollamaが起動しているか？
- 指定されたAIモデル（gemma2など）が使える状態か？

問題があればエラーメッセージが表示されます。

### 監査の実行
1. ツールが起動している状態で、指定したフォルダ（例: VRChatのスクショフォルダ）に新しい画像を保存します。
2. ツールが自動的に画像を検知し、AIに判定させます。
3. 通知はまだ実装されていませんが、ログに `PASS` または `FAIL` が表示されます。

### 結果の確認
ブラウザで以下のアドレスを開くと、履歴と判定理由を確認できます。
[http://localhost:8080](http://localhost:8080)

## 判定ルールの変更
`rules.md` ファイルを編集することで、AIの判定基準を自由に変更できます。

例:
```markdown
# 監査基準
- [FAIL] ネームタグが映り込んでいる
- [PASS] UIが消えている綺麗な写真
```

## トラブルシューティング
**Q. "Ollama Connection Failed" と出る**
A. Ollamaアプリが起動していない可能性があります。タスクトレイを確認するか、スタートメニューからOllamaを起動してください。

**Q. "Model 'gemma3:4b' missing" と出る**
A. `ollama pull gemma3:4b` コマンドを実行してモデルをダウンロードしてください。設定で使用するモデルを変更した場合は、そちらをpullしてください。

---
Author: akiRAM
