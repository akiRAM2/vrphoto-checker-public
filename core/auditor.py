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
        self.timeout = config.get("ai_timeout", 60)  # Default 60 seconds for vision inference
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
        
        # Hybrid logic: Strict for Safety, Relaxed for Copyright.
        prompt = f"""
You are a content moderation AI for VRChat.

MODERATION RULES (Read carefully):
{rules_text}

JUDGMENT POLICY (Follow these priorities):
1. **SAFETY (Sexual, Hate, Violence)**: [STRICT]
   - Any sign of hate symbols (Swastika, etc.), sexual organs, or gore must be flagged as **NG** immediately.
   - Do NOT overlook hate symbols.

2. **COPYRIGHT**: [RELAXED]
   - Only flag as NG if it is an **EXACT COPY** of a copyrighted character/logo.
   - Cosplay, inspired looks, or generic anime avatars are **OK**.

OUTPUT REQUIREMENT:
- Output MUST be valid JSON.
- **ALL TEXT FIELDS MUST BE IN JAPANESE.** (判定理由や説明は必ず日本語で書いてください)

JSON FORMAT EXAMPLE:
{{
    "observation": "画像には[説明]が写っています。",
    "result": "OK" or "NG",
    "reason": "[理由]のため、[OK/NG]と判定します。"
}}

Your Task:
Analyze the image and output the result in the JSON format above.
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
