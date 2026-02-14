import os
import time
import threading
import json
import logging
import webbrowser
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
    default_config = {
        "watch_path": os.path.join(os.path.expanduser("~"), "Pictures", "VRChat"),
        "ai_api_url": "http://localhost:11434/api/generate",
        "ai_model": "gemma3:4b",
        "ai_timeout": 60,
        "poll_interval": 5,
        "port": 8080
    }

    if not os.path.exists(config_path):
        logging.info("Configuration file not found. Creating default config.json.")
        try:
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(default_config, f, indent=4)
        except IOError as e:
            logging.error(f"Failed to create config file: {e}")
        return default_config
    
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        logging.error(f"CRITICAL: Default config file '{config_path}' is corrupted.")
        logging.error(f"JSON Error: {e}")
        print("\n" + "="*50)
        print("❌  Configuration Error")
        print(f"The 'config.json' file is invalid. Line {e.lineno}, Column {e.colno}.")
        print("Action: Please fix the syntax error or delete the file to regenerate defaults.")
        print("="*50 + "\n")
        # Returning default config to allow execution to proceed or letting it crash depends on strategy.
        # But per user request for "easy debugging", returning defaults might mask the issue?
        # Let's return defaults but strictly warn, or maybe just exit.
        # Given the user wants detailed debug info, let's re-raise or return None and let main handle it?
        # Simpler: Return default but rename broken file.
        # Actually, let's just return defaults but WARN heavily.
        return default_config
    except Exception as e:
        logging.error(f"Unexpected error reading config: {e}")
        return default_config

def main():
    print("""
    ##########################################
    #   VRPhoto Checker (Standalone Edition) #
    ##########################################
    """)
    logging.info("Initializing system...")
    
    # Load configuration
    config = load_config()
    
    # Check Environment (Ollama & Model)
    # We create a temporary auditor instance just for the health check
    from core.auditor import Auditor
    temp_auditor = Auditor(config)
    if not temp_auditor.check_health():
        logging.error("System health check failed. Please fix the issues above and restart.")
        input("Press Enter to exit...")
        return

    # Initialize database
    db = Database("logs/history.db")
    db.init_db()
    
    # Start Web Dashboard in a separate thread
    server = DashboardServer(config["port"], db)
    server_thread = threading.Thread(target=server.start, daemon=True)
    server_thread.start()
    logging.info(f"Dashboard running at http://localhost:{config['port']}")
    
    # Open browser automatically after a delay to ensure server is ready
    time.sleep(5)
    webbrowser.open(f"http://localhost:{config['port']}")
    logging.info("Browser opened automatically.")
    
    # Start Directory Watcher
    watcher = Watcher(config, db)
    
    logging.info("Startup complete. Waiting for new photos...")
    try:
        watcher.start()
    except KeyboardInterrupt:
        logging.info("Stopping vrphoto-checker...")

if __name__ == "__main__":
    main()
