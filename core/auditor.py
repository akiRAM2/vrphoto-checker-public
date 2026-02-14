import urllib.request
import urllib.error
import json
import base64
import logging
import os
import io
import socket
from PIL import Image
from core.safety_checker import SafetyChecker

class Auditor:
    def __init__(self, config):
        self.api_url = config.get("ai_api_url", "http://localhost:11434/api/generate")
        self.base_url = self.api_url.replace("/api/generate", "") # Extract base URL for other endpoints
        self.model = config.get("ai_model", "gemma3:4b")
        self.timeout = config.get("ai_timeout", 60)  # Default 60 seconds for vision inference
        self.rules_path = "rules.md"
        
        # Initialize Local Safety Checker
        self.safety_checker = SafetyChecker()
    
    def check_health(self):
        """Checks if Ollama is running and the model is available with detailed error reporting."""
        print(f"[Auditor] Checking connection to Ollama at {self.base_url}...")
        
        # 1. Check Ollama Connection
        models_data = None
        try:
            with urllib.request.urlopen(f"{self.base_url}/api/tags", timeout=3) as response:
                if response.status == 200:
                    models_data = json.loads(response.read().decode('utf-8'))
                else:
                    logging.error(f"Ollama connected but returned unexpected status: {response.status}")
                    print(f"⚠️  Ollama returned status check: {response.status}")
                    return False

        except urllib.error.URLError as e:
            if isinstance(e.reason, ConnectionRefusedError) or isinstance(e.reason, FileNotFoundError): 
                logging.error(f"Connection refused: {e.reason}")
                print("\n" + "="*50)
                print("❌  Ollama Not Running")
                print(f"Details: {e.reason}")
                print("Action: Please start the 'Ollama' application from your Start Menu or taskbar.")
                print("="*50 + "\n")
            elif isinstance(e.reason, socket.timeout):
                logging.error("Connection timed out.")
                print("\n" + "="*50)
                print("❌  Ollama Connection Timeout")
                print("Action: Check if Ollama is stuck or if the port is blocked by firewall.")
                print("="*50 + "\n")
            else:
                logging.error(f"URL Error: {e}")
                print(f"❌  Ollama Connection Error: {e}")
            return False
        except Exception as e:
            logging.error(f"Unexpected error during health check: {e}")
            return False

        # 2. Check Model Availability
        if models_data:
            available_models = [m['name'] for m in models_data.get('models', [])]
            # Normalize model names checks (ignore :latest tag if not specified, etc)
            model_exists = any(self.model in m for m in available_models)
            
            if not model_exists:
                logging.warning(f"Model '{self.model}' not found in Ollama.")
                print("\n" + "="*50)
                print(f"⚠️  Model '{self.model}' Missing")
                print(f"Found models: {', '.join(available_models) if available_models else 'None'}")
                
                # Smart suggestion logic
                similar_models = [m for m in available_models if 'gemma' in m.lower()]
                if similar_models:
                    print(f"💡 Suggestion: You have '{similar_models[0]}'.")
                    print(f"Action: Update 'config.json' to use '{similar_models[0]}' instead of '{self.model}'.")
                else:
                    print(f"Action: Run the following command in your terminal:")
                    print(f"    ollama pull {self.model}")
                print("="*50 + "\n")
                return False 
                
            print(f"[Auditor] Connection OK. Model '{self.model}' is ready.")
            return True
        return False

    def _read_rules(self):
        if not os.path.exists(self.rules_path):
            return "No rules defined."
        try:
            with open(self.rules_path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            logging.error(f"Failed to read rules file: {e}")
            return "Error reading rules."

    def audit(self, file_path):
        # Read image and encode to base64
        # (Preprocessing is handled in step 0 below)
        # ---------------------------------------------------------
        # 0. Preprocessing: Load & Resize (Compression)
        # ---------------------------------------------------------
        try:
            pil_image = Image.open(file_path).convert("RGB")
            original_size = pil_image.size
            if pil_image.width > 1920 or pil_image.height > 1080:
                logging.info(f"Resizing large image ({original_size}) to max 1920x1080...")
                pil_image.thumbnail((1920, 1080), Image.Resampling.LANCZOS)
            
            # Save to buffer for Base64 encoding
            buffered = io.BytesIO()
            pil_image.save(buffered, format="JPEG", quality=85)
            encoded_string = base64.b64encode(buffered.getvalue()).decode('utf-8')
            
        except Exception as e:
            logging.error(f"Failed to process image {file_path}: {e}")
            return "ERROR", f"Image processing failed: {str(e)}"
            
        # ---------------------------------------------------------
        # 1. Local Safety Check (Hate Symbols & Trademarks)
        # ---------------------------------------------------------
        # This runs on CPU/Local Python and avoids external API calls for these specific critical checks.
        logging.info("Running Local Safety Checker...")
        # Check against resized image for speed
        local_result = self.safety_checker.check_image(pil_image)
        
        if local_result.get("result") == "NG":
            reason = local_result.get("reason", "Detected unsafe content via Local Check.")
            # ... (Rest of existing logic)
            logging.info(f"Local Check Failed: {reason}")
            # Identify specific type of NG to match JSON format if needed, but Auditor returns (Result, Reason) tuple.
            return "NG", f"[Local Safety] {reason}"
            
        logging.info("Local Safety Check PASS. Proceeding to LLM Audit...")
        
        # ---------------------------------------------------------
        # 2. LLM Audit (Ollama / Gemma)
        # ---------------------------------------------------------
        rules_text = self._read_rules()
        
        # Logic Rewrite: Fact-Based Audit (Objective Analysis)
        # Removed all "Strict", "Critical", and emotional directives to prevent hallucinations.
        prompt = f"""
You are a VRChat Safety Auditor.
Your task is to protect users from explicit violations while avoiding false positives.
Be objective. Accidental resemblance to symbols in background patterns is NOT a violation.
Your task is to objectively analyze the image and verify compliance with the rules.

[Reference Rules]
{rules_text}

[Analysis Instruction]
1. First, objectively list what you see in the image (Symbols, Text, Characters, Clothes the chacactors wearing).
2. Then, verify if ANY of the observed items match the [NG] categories in the rules.
3. If no prohibited content is visible, the result is "OK".
[Output Format]
Provide the response in the following JSON format.
**All text fields MUST be in Japanese.**

Example Output (OK):
{{
  "observation": "青い空と海が見える背景。中央にアニメ調の少女のアバターがいる。白と青のワンピースを着ており、露出は少ない。",
  "result": "OK",
  "reason": "禁止されているコンテンツ（性描写、ヘイト、著作権侵害）は見当たらないため。"
}}

Example Output (NG 1 - Hate Symbol):
{{
  "observation": "壁にハーケンクロイツ（ナチスのシンボル）が描かれたポスターがある。",
  "result": "NG",
  "reason": "ナチスのシンボルはヘイトスピーチ規定により禁止されているため。"
}}

Example Output (NG 2 - Sexual Content):
{{
  "observation": "女性アバターが下着姿で写っており、臀部や胸部が大きく露出している。",
  "result": "NG",
  "reason": "性的な表現は禁止されているため。"
}}

Example Output (NG 3 - Copyright):
{{
  "observation": "壁に『ポケットモンスター』のキャラクター『ピカチュウ』のイラストが描かれている。",
  "result": "NG",
  "reason": "著作権で保護されたキャラクターの無断使用は禁止されているため。"
}}

Your JSON Response:
"""
        
        payload = {
            "model": self.model,
            "prompt": prompt,
            "images": [encoded_string],
            "stream": False,
            "format": "json"
        }
        
        try:
            data = json.dumps(payload).encode('utf-8')
            req = urllib.request.Request(self.api_url, data=data, headers={'Content-Type': 'application/json'})
            
            logging.info(f"Sending image to AI (timeout: {self.timeout}s)...")
            with urllib.request.urlopen(req, timeout=self.timeout) as response: # 30s timeout for inference
                response_body = response.read().decode('utf-8')
                result_json = json.loads(response_body)
                
                ai_response_text = result_json.get("response", "{}")
                
                # Debug: Log the raw AI response
                logging.info(f"Raw AI response (first 500 chars): {ai_response_text[:500]}")
                
                # Check if response is empty or just whitespace
                if not ai_response_text or ai_response_text.strip() == "":
                    logging.error("AI returned empty response")
                    return "ERROR", "AI returned empty response"
                
                try:
                    # Clean up if AI adds markdown code blocks
                    if "```json" in ai_response_text:
                        ai_response_text = ai_response_text.split("```json")[1].split("```")[0].strip()
                    elif "```" in ai_response_text:
                        ai_response_text = ai_response_text.split("```")[1].split("```")[0].strip()

                    audit_data = json.loads(ai_response_text)
                    
                    # Debug: Log parsed JSON
                    logging.info(f"Parsed JSON keys: {list(audit_data.keys())}")
                    
                    # Check if JSON is empty
                    if not audit_data:
                        logging.error(f"AI returned empty JSON object {{}}")
                        logging.error(f"Full raw AI response: {ai_response_text}")
                        logging.error(f"Response length: {len(ai_response_text)} chars")
                        return "ERROR", f"AI returned empty JSON. This may indicate model confusion or timeout. Raw: {ai_response_text[:100]}"
                    
                    # Validate keys
                    if "result" not in audit_data or "reason" not in audit_data:
                        logging.warning(f"AI returned incomplete JSON. Keys found: {list(audit_data.keys())}")
                        logging.warning(f"Full JSON: {audit_data}")
                        return "ERROR", f"AI response missing required keys. Got: {list(audit_data.keys())}"

                    return audit_data.get("result", "UNKNOWN"), audit_data.get("reason", "No reason provided")
                    
                except json.JSONDecodeError as e:
                    logging.error(f"Failed to parse AI response JSON: {e}")
                    logging.error(f"Raw text (full): {ai_response_text}")
                    return "ERROR", f"Invalid JSON from AI. Error: {str(e)[:50]}"
                    
        except urllib.error.HTTPError as e:
            logging.error(f"HTTP Error from AI API: {e.code} - {e.reason}")
            return "ERROR", f"AI Server HTTP Error: {e.code}"
        except urllib.error.URLError as e:
            logging.error(f"Connection Error to AI API: {e.reason}")
            return "ERROR", "Failed to connect to AI server during audit."
        except socket.timeout:
            logging.error(f"AI Inference timed out after {self.timeout} seconds.")
            return "ERROR", f"AI Inference timed out (>{self.timeout}s). Try increasing 'ai_timeout' in config.json"
        except Exception as e:
            logging.error(f"Unexpected error during audit: {e}")
            return "ERROR", f"Unexpected error: {str(e)}"
