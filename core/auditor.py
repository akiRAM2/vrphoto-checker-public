import urllib.request
import urllib.error
import json
import base64
import logging
import os
import io
import time
import socket
import subprocess
from PIL import Image
from core.safety_checker import SafetyChecker

class Auditor:
    def __init__(self, config):
        self.api_url = config.get("ai_api_url", "http://localhost:1234/v1/chat/completions")
        # LM Studio: base URL is e.g. http://localhost:1234
        self.base_url = self.api_url.split("/v1/")[0] if "/v1/" in self.api_url else self.api_url
        self.model = config.get("ai_model", "qwen2-vl-4b-instruct-q4_k_m")
        self.timeout = config.get("ai_timeout", 180)
        self.rules_path = "rules.md"
        
        # Initialize Local Safety Checker
        self.safety_checker = SafetyChecker()
        self.lms_exe = self._find_lms_exe()
    
    def _find_lms_exe(self):
        """lms.exe の場所を特定する。"""
        # PATH から検索
        try:
            from shutil import which
            path = which("lms")
            if path:
                return path
        except:
            pass
        
        # Windows 標準インストール場所（%USERPROFILE%\.lmstudio\bin\lms.exe）
        default_path = os.path.join(os.path.expanduser("~"), ".lmstudio", "bin", "lms.exe")
        if os.path.exists(default_path):
            return default_path
        
        return None

    def ensure_ai_server(self):
        """LM Studio サーバーが起動し、モデルがロードされていることを確認する。"""
        if not self.lms_exe:
            logging.warning("lms CLI ツールが見つかりません。自動起動はスキップします。")
            return False

        try:
            # 1. サーバー状態の確認
            status_proc = subprocess.run([self.lms_exe, "server", "status"], capture_output=True, text=True)
            if "Server: OFF" in status_proc.stdout or status_proc.returncode != 0:
                logging.info("LM Studio サーバーが停止しています。起動中...")
                subprocess.run([self.lms_exe, "server", "start"], check=True)
                time.sleep(3) # 起動待ち

            # 2. モデルのロード状況確認
            status_proc = subprocess.run([self.lms_exe, "status"], capture_output=True, text=True)
            if self.model.lower() not in status_proc.stdout.lower():
                logging.info(f"モデル '{self.model}' をロード中...")
                # コンテキスト長を 8192 に設定してロード（エラー回避のため）
                subprocess.run([self.lms_exe, "load", self.model, "--context-length", "8192"], check=True)
                logging.info("モデルのロードが完了しました。")
            
            return True
        except Exception as e:
            logging.error(f"LM Studio の自動制御中にエラーが発生しました: {e}")
            return False

    def check_health(self):
        """LM Studioが起動しているか、モデルが利用可能かを確認する。"""
        print(f"[Auditor] LM Studio への接続を確認中: {self.base_url} ...")
        
        # 1. LM Studio の接続確認（/v1/models エンドポイントを使用）
        models_data = None
        try:
            with urllib.request.urlopen(f"{self.base_url}/v1/models", timeout=5) as response:
                if response.status == 200:
                    models_data = json.loads(response.read().decode('utf-8'))
                else:
                    logging.error(f"LM Studio から予期しないステータスが返されました: {response.status}")
                    print(f"⚠️  LM Studio ステータス確認: {response.status}")
                    return False

        except urllib.error.URLError as e:
            if isinstance(e.reason, (ConnectionRefusedError, FileNotFoundError)):
                logging.error(f"接続拒否: {e.reason}")
                print("\n" + "="*50)
                print("❌  LM Studio が起動していません")
                print(f"詳細: {e.reason}")
                print("対処: LM Studio を起動し、ローカルサーバーを開始してください（デフォルト: http://localhost:1234）")
                print("="*50 + "\n")
            elif isinstance(e.reason, socket.timeout):
                logging.error("接続タイムアウト。")
                print("\n" + "="*50)
                print("❌  LM Studio 接続タイムアウト")
                print("対処: LM Studio が起動しているか、ポートがファイアウォールでブロックされていないか確認してください。")
                print("="*50 + "\n")
            else:
                logging.error(f"URL エラー: {e}")
                print(f"❌  LM Studio 接続エラー: {e}")
            return False
        except Exception as e:
            logging.error(f"ヘルスチェック中に予期しないエラー: {e}")
            return False

        # 2. モデルの利用可能性を確認
        if models_data:
            available_models = [m.get('id', '') for m in models_data.get('data', [])]
            model_exists = any(self.model.lower() in m.lower() for m in available_models)
            
            if not model_exists:
                logging.warning(f"モデル '{self.model}' が LM Studio に見つかりません。")
                print("\n" + "="*50)
                print(f"⚠️  モデル '{self.model}' が見つかりません")
                print(f"検出されたモデル: {', '.join(available_models) if available_models else 'なし（モデルが読み込まれていない可能性があります）'}")
                print(f"対処: LM Studio でモデルを読み込んでから再試行してください。")
                print("="*50 + "\n")
                # モデルが読み込まれていなくても接続自体はOKなので、警告のみで続行
                # （LM Studio はモデルを動的に読み込む場合があるため）
                return False
                
            print(f"[Auditor] 接続OK。モデル '{self.model}' が利用可能です。")
            return True
        return False

    def _read_rules(self):
        if not os.path.exists(self.rules_path):
            return "No rules defined."
        try:
            with open(self.rules_path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            logging.error(f"ルールファイルの読み込みに失敗: {e}")
            return "Error reading rules."

    def _encode_image(self, pil_image, max_size, quality=75):
        """画像を指定サイズ以下にリサイズしてBase64エンコードする。"""
        img = pil_image.copy()
        if img.width > max_size or img.height > max_size:
            logging.info(f"大きな画像 ({img.size}) を最大 {max_size}x{max_size} にリサイズ中...")
            img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
        buffered = io.BytesIO()
        img.save(buffered, format="JPEG", quality=quality)
        encoded = base64.b64encode(buffered.getvalue()).decode('utf-8')
        logging.info(f"画像をエンコード完了: サイズ={img.size}, base64長={len(encoded):,} chars")
        return encoded

    def audit(self, file_path):
        # ---------------------------------------------------------
        # 0. 前処理: 画像の読み込み
        # ---------------------------------------------------------
        try:
            pil_image = Image.open(file_path).convert("RGB")
        except Exception as e:
            logging.error(f"画像処理失敗 {file_path}: {e}")
            return "ERROR", f"画像処理に失敗しました: {str(e)}"

        try:
            # 通常は最大 1024x1024 でエンコード
            encoded_string = self._encode_image(pil_image, max_size=1024, quality=75)
        except Exception as e:
            logging.error(f"画像エンコード失敗 {file_path}: {e}")
            return "ERROR", f"画像エンコードに失敗しました: {str(e)}"
            
        # ---------------------------------------------------------
        # 1. シンボルチェック（ヘイトシンボル & 商標）
        # ---------------------------------------------------------
        logging.info("[シンボルチェック] 実行中...")
        local_result = self.safety_checker.check_image(pil_image)
        
        if local_result.get("result") == "NG":
            reason = local_result.get("reason", "シンボルチェックで問題が検出されました。")
            logging.info(f"[シンボルチェック] NG: {reason}")
            return "NG", f"[シンボルチェック] {reason}"
            
        logging.info("[シンボルチェック] PASS → 画像解析チェックへ...")
        
        # ---------------------------------------------------------
        # 2. 画像解析チェック（LM Studio / Qwen3 VL）
        # OpenAI Chat Completions API 互換形式を使用
        # ---------------------------------------------------------
        rules_text = self._read_rules()
        
        system_message = (
            "あなたは画像審査アシスタントです。"
            "提供されたルールに基づいて、画像を客観的に分析・判定します。"
            "必ず指定されたJSON形式のみで返答してください。マークダウンなどの修飾や説明文は一切含めないでください。"
        )
        
        user_message = f"""以下のルールに基づいて画像を審査してください。

[参照ルール]
{rules_text}

[分析手順]
1. 画像に写っているものを客観的に観察し、文章で説明する
2. 観察内容がルールの条件に該当するか検証し、"OK" または "NG" の結果を判定する
3. 判定した結果の理由を簡潔に記載する

[出力形式]
以下のJSON形式のみで返答すること。**すべてのテキストフィールドは日本語で記述**すること。

{{
  "observation": "画像に写っているものの客観的な観察結果",
  "result": "OK または NG",
  "reason": "OKまたはNGと判定した具体的な理由"
}}
"""
        
        # OpenAI Chat Completions API 形式のペイロード（画像はbase64 data URL として埋め込む）
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": system_message
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{encoded_string}"
                            }
                        },
                        {
                            "type": "text",
                            "text": user_message
                        }
                    ]
                }
            ],
            "temperature": 0.1,
            "max_tokens": 512,
            "stream": False,
        }
        
        # HTTP 400 "failed to process image" 発生時のリトライ用フラグ
        retry_with_smaller = False

        for attempt in range(2):  # 最大2回試行: 1024x1024 → 512x512
            if attempt == 1:
                # リトライ: 512x512 に縮小して再エンコード
                logging.warning("[画像解析チェック] 画像処理失敗のため 512x512 に縮小してリトライ中...")
                try:
                    encoded_string = self._encode_image(pil_image, max_size=512, quality=70)
                    # ペイロードの画像URLを更新
                    payload["messages"][1]["content"][0]["image_url"]["url"] = (
                        f"data:image/jpeg;base64,{encoded_string}"
                    )
                except Exception as e:
                    logging.error(f"リトライ用画像エンコード失敗: {e}")
                    return "ERROR", f"リトライ用画像エンコードに失敗しました: {str(e)}"

            try:
                data = json.dumps(payload).encode('utf-8')
                req = urllib.request.Request(
                    self.api_url,
                    data=data,
                    headers={'Content-Type': 'application/json'}
                )
                
                attempt_label = f"(試行 {attempt + 1}/2)" if attempt > 0 else ""
                logging.info(f"[画像解析チェック] LM Studio に送信中 {attempt_label} (timeout: {self.timeout}s)...")
                logging.info(f"送信先: {self.api_url} | モデル: {self.model} | ペイロードサイズ: {len(data):,} bytes")
                with urllib.request.urlopen(req, timeout=self.timeout) as response:
                    response_body = response.read().decode('utf-8')
                    result_json = json.loads(response_body)
                    
                    # OpenAI 互換レスポンスから content を取得
                    choices = result_json.get("choices", [])
                    if not choices:
                        logging.error("AI レスポンスに choices が含まれていません")
                        return "ERROR", "AI からの応答に choices が含まれていません"
                    
                    ai_response_text = choices[0].get("message", {}).get("content", "")
                    
                    # デバッグ: 生の AI 応答をログ出力
                    logging.info(f"AI 生レスポンス (先頭500文字): {ai_response_text[:500]}")
                    
                    # 空レスポンスのチェック
                    if not ai_response_text or ai_response_text.strip() == "":
                        logging.error("AI が空のレスポンスを返しました")
                        return "ERROR", "AI が空のレスポンスを返しました"
                    
                    try:
                        # AI がマークダウンのコードブロックを付加した場合の除去
                        if "```json" in ai_response_text:
                            ai_response_text = ai_response_text.split("```json")[1].split("```")[0].strip()
                        elif "```" in ai_response_text:
                            ai_response_text = ai_response_text.split("```")[1].split("```")[0].strip()

                        audit_data = json.loads(ai_response_text)
                        
                        # デバッグ: パースされた JSON をログ出力
                        logging.info(f"パース済み JSON キー: {list(audit_data.keys())}")
                        
                        # 空の JSON オブジェクトのチェック
                        if not audit_data:
                            logging.error(f"AI が空の JSON オブジェクト {{}} を返しました")
                            logging.error(f"AI 生レスポンス全文: {ai_response_text}")
                            return "ERROR", f"AI が空の JSON を返しました。Raw: {ai_response_text[:100]}"
                        
                        # 必須キーの検証
                        if "result" not in audit_data or "reason" not in audit_data:
                            logging.warning(f"AI が不完全な JSON を返しました。検出されたキー: {list(audit_data.keys())}")
                            logging.warning(f"JSON 全文: {audit_data}")
                            return "ERROR", f"AI レスポンスに必須キーが不足しています。検出: {list(audit_data.keys())}"

                        return audit_data.get("result", "UNKNOWN"), audit_data.get("reason", "理由が提供されていません")
                        
                    except json.JSONDecodeError as e:
                        logging.error(f"AI レスポンスの JSON パースに失敗: {e}")
                        logging.error(f"生テキスト (全文): {ai_response_text}")
                        return "ERROR", f"AI からの無効な JSON。エラー: {str(e)[:50]}"
                        
            except urllib.error.HTTPError as e:
                logging.error(f"AI API からの HTTP エラー: {e.code} - {e.reason}")
                # エラーボディを読み込んで詳細を確認
                try:
                    error_body = e.read().decode('utf-8')
                    logging.error(f"HTTP エラーボディ: {error_body}")
                except Exception as read_err:
                    error_body = ""
                    logging.error(f"エラーボディの読み込みに失敗: {read_err}")

                # HTTP 400 かつ "failed to process image" ならリトライ
                if e.code == 400 and "failed to process image" in error_body and attempt == 0:
                    logging.warning("[画像解析チェック] LM Studio が画像処理に失敗 (コンテキスト不足の可能性)。縮小してリトライします。")
                    continue  # 次のループで 512x512 にリトライ

                print("\n" + "="*60)
                print(f"❌  LM Studio HTTP {e.code} エラー詳細:")
                print(error_body)
                print("="*60 + "\n")
                return "ERROR", f"AI サーバー HTTP エラー: {e.code}"
            except urllib.error.URLError as e:
                logging.error(f"AI API への接続エラー: {e.reason}")
                return "ERROR", "AI サーバーへの接続に失敗しました。"
            except socket.timeout:
                logging.error(f"AI 推論が {self.timeout} 秒でタイムアウトしました。")
                return "ERROR", f"AI 推論タイムアウト (>{self.timeout}s)。config.json の 'ai_timeout' を増やしてみてください。"
            except Exception as e:
                logging.error(f"審査中に予期しないエラー: {e}")
                return "ERROR", f"予期しないエラー: {str(e)}"

        # ループ終了（2回とも失敗した場合）
        return "ERROR", "AI サーバー HTTP エラー: 400 (画像縮小リトライも失敗)"
