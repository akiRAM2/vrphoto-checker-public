import os
import time
import threading
import json
import logging
from core.watcher import Watcher
from core.database import Database
from web.server import DashboardServer

# Logger configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)

def load_config():
    config_path = "config.json"
    if not os.path.exists(config_path):
        # Default configuration
        default_config = {
            "watch_path": os.path.join(os.path.expanduser("~"), "Pictures", "VRChat"),
            "ai_api_url": "http://localhost:11434/api/generate",
            "ai_model": "gemma:2b",
            "poll_interval": 5,
            "port": 8080
        }
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(default_config, f, indent=4)
        return default_config
    
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)

def main():
    logging.info("Starting vrphoto-checker...")
    
    # Load configuration
    config = load_config()
    
    # Initialize database
    db = Database("logs/history.db")
    db.init_db()
    
    # Start Web Dashboard in a separate thread
    server = DashboardServer(config["port"], db)
    server_thread = threading.Thread(target=server.start, daemon=True)
    server_thread.start()
    logging.info(f"Dashboard running at http://localhost:{config['port']}")
    
    # Start Directory Watcher
    watcher = Watcher(config, db)
    try:
        watcher.start()
    except KeyboardInterrupt:
        logging.info("Stopping vrphoto-checker...")

if __name__ == "__main__":
    main()
