import urllib.request
import urllib.error
import json
import base64
import logging
import os

class Auditor:
    def __init__(self, config):
        self.api_url = config.get("ai_api_url", "http://localhost:11434/api/generate")
        self.base_url = self.api_url.replace("/api/generate", "") # Extract base URL for other endpoints
        self.model = config.get("ai_model", "gemma2") # Default changed to gemma2 as a realistic placeholder, user can change to gemma3
        self.rules_path = "rules.md"
    
    def check_health(self):
        """Checks if Ollama is running and the model is available."""
        print(f"[Auditor] Checking connection to Ollama at {self.base_url}...")
        
        # 1. Check Ollama Connection
        try:
            with urllib.request.urlopen(f"{self.base_url}/api/tags") as response:
                if response.status != 200:
                    logging.error(f"Ollama is reachable but returned status {response.status}.")
                    return False
                models_data = json.loads(response.read().decode('utf-8'))
        except urllib.error.URLError:
            logging.error("Could not connect to Ollama. Make sure Ollama is installed and running.")
            print("\n" + "="*50)
            print("❌  Ollama Connection Failed")
            print("Please download and install Ollama from https://ollama.com/")
            print("After installation, launch the Ollama application.")
            print("="*50 + "\n")
            return False

        # 2. Check Model Availability
        available_models = [m['name'] for m in models_data.get('models', [])]
        # Normalize model names checks (ignore :latest tag if not specified, etc)
        # Simple check: exact match or match before colon
        model_exists = any(self.model in m for m in available_models)
        
        if not model_exists:
            logging.warning(f"Model '{self.model}' not found in Ollama.")
            print("\n" + "="*50)
            print(f"⚠️  Model '{self.model}' missing")
            print(f"To install the required model, run the following command in your terminal:")
            print(f"    ollama pull {self.model}")
            print("="*50 + "\n")
            return False # Strictly returning False to stop startup or warn user heavily? 
            # Depending on UX, we might want to continue if user promises to install it, 
            # but returning False and stopping main loop is safer for "usability" (fail fast).
            
        print(f"[Auditor] Connection OK. Model '{self.model}' is ready.")
        return True

    def _read_rules(self):
        if not os.path.exists(self.rules_path):
            return "No rules defined."
        with open(self.rules_path, "r", encoding="utf-8") as f:
            return f.read()

    def audit(self, file_path):
        import os 
        
        # Read image and encode to base64
        try:
            with open(file_path, "rb") as image_file:
                encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
        except Exception as e:
            logging.error(f"Failed to read file {file_path}: {e}")
            return "ERROR", f"File read error: {e}"
        
        rules_text = self._read_rules()
        
        # Optimized prompt for Gemma
        prompt = f"""
        ACT AS A CONTENT MODERATION AI.
        TASK: Review the provided image against the following safety rules.
        
        RULES:
        {rules_text}
        
        OUTPUT FORMAT:
        Return ONLY a JSON object. No markdown, no explanations outside the JSON.
        {{
            "result": "PASS" or "FAIL",
            "reason": "Detailed explanation of why it passed or failed."
        }}
        """
        
        payload = {
            "model": self.model,
            "prompt": prompt,
            "images": [encoded_string],
            "stream": False,
            "format": "json"
        }
        
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(self.api_url, data=data, headers={'Content-Type': 'application/json'})
        
        try:
            with urllib.request.urlopen(req) as response:
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
                    return audit_data.get("result", "UNKNOWN"), audit_data.get("reason", "No reason provided")
                except json.JSONDecodeError:
                    logging.error(f"Failed to parse AI response JSON: {ai_response_text}")
                    return "ERROR", f"Invalid JSON from AI: {ai_response_text[:50]}..."
                    
        except Exception as e:
            logging.error(f"AI Request failed: {e}")
            return "ERROR", str(e)
