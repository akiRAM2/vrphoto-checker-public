import torch
import open_clip
from PIL import Image
import logging

class SafetyChecker:
    def __init__(self):
        self.device = "cpu"  # Keep CPU to avoid VRChat conflict as per requirements
        self.model_name = "ViT-B-32" 
        self.pretrained = "laion2b_s34b_b79k"
        
        logging.info(f"Loading Local Safety Model: {self.model_name} ({self.pretrained})...")
        try:
            self.model, _, self.preprocess = open_clip.create_model_and_transforms(
                self.model_name, 
                pretrained=self.pretrained,
                device=self.device
            )
            self.tokenizer = open_clip.get_tokenizer(self.model_name)
            
            # Define specific prompts for Hate and Trademark detection
            # We must include diverse "Safe" prompts to ensure benign images (scenery, abstract, UI) 
            # don't get forced into "Hate/Trademark" buckets due to low probability on "anime avatar".
            self.labels = [
                "a safe photo of a virtual anime avatar",  # 0: Safe
                "a screenshot of a video game world",      # 1: Safe
                "a scenery or landscape photo",            # 2: Safe
                "abstract shapes or solid colors",         # 3: Safe
                "geometric crossing lines pattern",        # 4: Safe
                "window frames or grid structure",         # 5: Safe
                
                "SS bolts symbol",                         # 6: Hate
                "KKK symbol",                              # 7: Hate
                
                "a corporate brand logo",                  # 8: Trademark
                "a trademarked logo",                      # 9: Trademark
                "a copyrighted commercial logo",           # 10: Trademark (Generic)
                "iconic video game logo",                  # 11: Trademark (Generic)
            ]
            
            self.text_features = self._precompute_text_features()
            logging.info("Local Safety Model loaded successfully.")
            
        except Exception as e:
            logging.error(f"Failed to load Safety Model: {e}")
            self.model = None

    def _precompute_text_features(self):
        if not self.model:
            return None
        text = self.tokenizer(self.labels).to(self.device)
        with torch.no_grad():
            text_features = self.model.encode_text(text)
            text_features /= text_features.norm(dim=-1, keepdim=True)
        return text_features

    def check_image(self, image_input):
        if not self.model:
            return {"result": "ERROR", "reason": "Model not loaded"}

        try:
            if isinstance(image_input, str):
                image = Image.open(image_input).convert('RGB')
            elif isinstance(image_input, Image.Image):
                image = image_input.convert('RGB')
            else:
                return {"result": "ERROR", "reason": "Invalid input type"}
            
            # Preprocessing (Resizing/Normalizing is handled here)
            # Input image is 1920x1080, model takes 224x224 usually.
            image_input = self.preprocess(image).unsqueeze(0).to(self.device)

            with torch.no_grad():
                image_features = self.model.encode_image(image_input)
                image_features /= image_features.norm(dim=-1, keepdim=True)

                text_probs = (100.0 * image_features @ self.text_features.T).softmax(dim=-1)
                probs = text_probs.cpu().numpy()[0]

            # Parse results
            # Indices: 0-5=Safe, 6-7=Hate (SS, KKK), 8-11=Trademark
            
            # Safe score is max of safe categories
            safe_score = max(probs[0:6])
            
            # Hate / Trademark scores
            # Removed Swastika (indices 4,5 in previous list) to reduce False Positives
            hate_max = max(probs[6:8])
            trademark_score = max(probs[8:12])

            logging.info(f"Safety Check Scores - Safe: {safe_score:.2f}, Hate: {hate_max:.2f}, Trademark: {trademark_score:.2f}")

            # Thresholds (Tunable)
            # Increased thresholds to avoid False Positives on simple geometry being flagged as Logos
            HATE_THRESHOLD = 0.5      
            TRADEMARK_THRESHOLD = 0.6 

            if hate_max > HATE_THRESHOLD:
                return {
                    "result": "NG",
                    "reason": f"Hate symbol detected (Confidence: {hate_max:.2f})."
                }
            
            if trademark_score > TRADEMARK_THRESHOLD:
                return {
                    "result": "NG",
                    "reason": f"Trademark commercial logo detected (Confidence: {trademark_score:.2f})."
                }

            return {
                "result": "OK",
                "reason": "No hate symbols or trademarks detected."
            }

        except Exception as e:
            logging.error(f"Error during local safety check: {e}")
            return {"result": "ERROR", "reason": str(e)}
