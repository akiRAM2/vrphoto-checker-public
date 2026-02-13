import os
import time
import logging
import hashlib
from core.auditor import Auditor

class Watcher:
    def __init__(self, config, db):
        self.watch_path = config["watch_path"]
        self.poll_interval = config["poll_interval"]
        self.db = db
        self.auditor = Auditor(config)
        self.processed_files = set()

    def start(self):
        logging.info(f"Monitoring folder: {self.watch_path}")
        
        # Initial scan to populate processed_files (optional: or process existing files)
        # For now, we might just want to process new files appearing after start.
        # But to be safe, let's just loop.
        
        if not os.path.exists(self.watch_path):
            logging.warning(f"Watch path does not exist: {self.watch_path}")
            # Try to create it for testing purposes
            os.makedirs(self.watch_path, exist_ok=True)

        while True:
            self._scan()
            time.sleep(self.poll_interval)

    def _scan(self):
        try:
            # os.scandir is efficient for directory traversal
            with os.scandir(self.watch_path) as entries:
                for entry in entries:
                    if entry.is_file() and entry.name.lower().endswith(('.png', '.jpg', '.jpeg')):
                        self._process_file(entry)
        except Exception as e:
            logging.error(f"Error scanning directory: {e}")

    def _process_file(self, entry):
        file_path = entry.path
        
        # Check if already processed in DB
        if self.db.is_processed(file_path):
            return

        logging.info(f"New file detected: {entry.name}")
        
        # Wait for file write to complete (simple delay as per architecture)
        time.sleep(2) 
        
        # Analyze file
        try:
            result, reason = self.auditor.audit(file_path)
            logging.info(f"Audit result for {entry.name}: {result} - {reason}")
            
            # Save to DB
            self.db.add_record(file_path, result, reason)
            
            # Notify (Placeholder for Windows Toast)
            if result == "FAIL":
                logging.warning(f"ALERT: {entry.name} failed audit!")
                # TODO: Implement Windows Toast notification using ctypes
                
        except Exception as e:
            logging.error(f"Failed to process {entry.name}: {e}")
