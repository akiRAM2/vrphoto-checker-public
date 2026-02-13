import urllib.request
import urllib.error
import json
import base64
import logging
import os
import socket

class Auditor:
    def __init__(self, config):
        self.api_url = config.get("ai_api_url", "http://localhost:11434/api/generate")
        self.base_url = self.api_url.replace("/api/generate", "") # Extract base URL for other endpoints
        self.model = config.get("ai_model", "gemma3:4b")
        self.rules_path = "rules.md"
    
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
        try:
            with open(file_path, "rb") as image_file:
                encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
        except FileNotFoundError:
            logging.error(f"File not found: {file_path}")
            return "ERROR", "File not found during audit process."
        except PermissionError:
            logging.error(f"Permission denied: {file_path}")
            return "ERROR", "Permission denied when reading file."
        except Exception as e:
            logging.error(f"Failed to read file {file_path}: {e}")
            return "ERROR", f"File read exception: {type(e).__name__}"
        
        rules_text = self._read_rules()
        
        # Optimized prompt for Gemma
        prompt = f"""
        ACT AS A CONTENT MODERATION AI.
        CONTEXT: VRChat screenshots (Anime/Cartoon style).
        TASK: Analyze the image visual content and check for rule violations.
        LANGUAGE: JAPANESE (The 'reason' field MUST be in Japanese).
        
        INSTRUCTIONS:
        1. First, visually analyze the image components (characters, clothing, text, background).
        2. Strictly evaluate against the rules below.
        3. "Anime/Cartoon style" logic:
           - Standard swimwear/cosplay -> OK
           - Exposed genitalia/nipples -> NG
           - Sexual acts -> NG
        
        RULES:
        {rules_text}
        
        OUTPUT FORMAT:
        Return ONLY a JSON object.
        {{
            "result": "OK" or "NG",
            "reason": "視覚的特徴: [画像に何が映っているか具体的に描写]. 判定理由: [ルールに基づく判定の根拠]."
        }}
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
            
            with urllib.request.urlopen(req, timeout=30) as response: # 30s timeout for inference
                response_body = response.read().decode('utf-8')
                result_json = json.loads(response_body)
                
                ai_response_text = result_json.get("response", "{}")
                
                try:
                    # Clean up if AI adds markdown code blocks
                    if "```json" in ai_response_text:
                        ai_response_text = ai_response_text.split("```json")[1].split("```")[0].strip()
                    elif "```" in ai_response_text:
                        ai_response_text = ai_response_text.split("```")[1].split("```")[0].strip()

                    audit_data = json.loads(ai_response_text)
                    
                    # Validate keys
                    if "result" not in audit_data or "reason" not in audit_data:
                        logging.warning(f"AI returned incomplete JSON: {audit_data}")
                        return "ERROR", "AI response missing 'result' or 'reason' keys."

                    return audit_data.get("result", "UNKNOWN"), audit_data.get("reason", "No reason provided")
                    
                except json.JSONDecodeError:
                    logging.error(f"Failed to parse AI response JSON. Raw text: {ai_response_text[:100]}...")
                    return "ERROR", f"Invalid JSON from AI. Raw: {ai_response_text[:20]}..."
                    
        except urllib.error.HTTPError as e:
            logging.error(f"HTTP Error from AI API: {e.code} - {e.reason}")
            return "ERROR", f"AI Server HTTP Error: {e.code}"
        except urllib.error.URLError as e:
            logging.error(f"Connection Error to AI API: {e.reason}")
            return "ERROR", "Failed to connect to AI server during audit."
        except socket.timeout:
            logging.error("AI Inference timed out.")
            return "ERROR", "AI Inference timed out (too slow)."
        except Exception as e:
            logging.error(f"Unexpected error during audit: {e}")
            return "ERROR", f"Unexpected error: {str(e)}"
