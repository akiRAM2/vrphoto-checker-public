import urllib.request
import json
import base64
import logging

class Auditor:
    def __init__(self, config):
        self.api_url = config["ai_api_url"]
        self.model = config["ai_model"]
        self.rules_path = "rules.md"
    
    def _read_rules(self):
        if not os.path.exists(self.rules_path):
            return "No rules defined."
        with open(self.rules_path, "r", encoding="utf-8") as f:
            return f.read()

    def audit(self, file_path):
        import os # Imported here to be explicit about dependencies
        
        # Read image and encode to base64
        with open(file_path, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
        
        rules_text = self._read_rules()
        
        prompt = f"""
        You are a content censorship AI. Review the image based on the following rules:
        
        {rules_text}
        
        Respond with a JSON object containing two keys: "result" (either "PASS" or "FAIL") and "reason" (a brief explanation).
        Do not include markdown formatting in your response. Just the JSON.
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
                
                # Ollama returns 'response' field with the generated text
                ai_response_text = result_json.get("response", "{}")
                
                try:
                    audit_data = json.loads(ai_response_text)
                    return audit_data.get("result", "UNKNOWN"), audit_data.get("reason", "No reason provided")
                except json.JSONDecodeError:
                    logging.error(f"Failed to parse AI response JSON: {ai_response_text}")
                    return "ERROR", "Invalid JSON from AI"
                    
        except Exception as e:
            logging.error(f"AI Request failed: {e}")
            return "ERROR", str(e)
