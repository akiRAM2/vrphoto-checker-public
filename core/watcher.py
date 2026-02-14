import os
import time
import logging
import hashlib
from core.auditor import Auditor
from core.notifier import show_notification

class Watcher:
    def __init__(self, config, db):
        self.watch_path = config["watch_path"]
        self.poll_interval = config["poll_interval"]
        self.db = db
        self.auditor = Auditor(config)
        self.processed_files = set()

    def start(self):
        logging.info(f"Monitoring folder: {self.watch_path}")
        
        if not os.path.exists(self.watch_path):
            logging.warning(f"Watch path does not exist: {self.watch_path}")
            # Try to create it for testing purposes
            os.makedirs(self.watch_path, exist_ok=True)

        # 1. Initial Scan: Skip existing files that haven't been processed
        self._initial_skip_scan()

        # 2. Main Loop: Monitor for new files
        while True:
            self._scan()
            time.sleep(self.poll_interval)

    def _initial_skip_scan(self):
        """Marks all currently existing files as SKIPPED in the DB if not already present."""
        logging.info("Performing initial scan to skip existing files...")
        count = 0
        try:
            for root, dirs, files in os.walk(self.watch_path):
                for file in files:
                    if file.lower().endswith(('.png', '.jpg', '.jpeg')):
                        full_path = os.path.join(root, file)
                        if not self.db.is_processed(full_path):
                            self.db.add_record(full_path, "SKIPPED", "Pre-existing file skipped on startup")
                            count += 1
        except Exception as e:
            logging.error(f"Error during initial scan: {e}")
        
        if count > 0:
            logging.info(f"Skipped {count} pre-existing files.")
        else:
            logging.info("No new pre-existing files found to skip.")

    def _scan(self):
        try:
            # Use os.walk for recursive scanning to support subdirectories (e.g., VRChat/2026-02)
            for root, dirs, files in os.walk(self.watch_path):
                for file in files:
                    if file.lower().endswith(('.png', '.jpg', '.jpeg')):
                        full_path = os.path.join(root, file)
                        self._process_file(full_path)
        except Exception as e:
            logging.error(f"Error scanning directory: {e}")

    def _process_file(self, file_path):
        # Check if already processed in DB
        if self.db.is_processed(file_path):
            return

        file_name = os.path.basename(file_path)
        logging.info(f"New file detected: {file_name}")
        
        # Wait for file write to complete (simple delay as per architecture)
        time.sleep(2) 
        
        # Analyze file
        try:
            result, reason = self.auditor.audit(file_path)
            logging.info(f"Audit result for {file_name}: {result} - {reason}")
            
            # Save to DB
            self.db.add_record(file_path, result, reason)
            
            # Notify (Windows Toast Notification)
            if result in ["FAIL", "NG", "ERROR"]:
                logging.warning(f"ALERT: {file_name} failed audit! Reason: {reason}")
                
                # Format a short notification text
                short_reason = (reason[:50] + '..') if len(reason) > 50 else reason
                show_notification(
                    title=f"🛑 違反の可能性: {result}",
                    message=f"{file_name}\n{short_reason}"
                )
                
        except Exception as e:
            logging.error(f"Failed to process {file_name}: {e}")
