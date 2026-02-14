import sqlite3
import os
import logging
from datetime import datetime

class Database:
    def __init__(self, db_path):
        self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

    def init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_path TEXT UNIQUE,
                result TEXT,
                reason TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
        conn.close()

    def is_processed(self, file_path):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT id FROM audit_log WHERE file_path = ?', (file_path,))
        exists = cursor.fetchone() is not None
        conn.close()
        return exists

    def add_record(self, file_path, result, reason):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            cursor.execute('INSERT INTO audit_log (file_path, result, reason) VALUES (?, ?, ?)', 
                           (file_path, result, reason))
            conn.commit()
        except sqlite3.IntegrityError:
            logging.warning(f"Record for {file_path} already exists.")
        conn.close()

    def get_logs(self, limit=50):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM audit_log ORDER BY timestamp DESC LIMIT ?', (limit,))
        rows = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return rows
    
    def clear_logs(self):
        """全ての監査ログを削除"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM audit_log')
        conn.commit()
        deleted_count = cursor.rowcount
        conn.close()
        logging.info(f"全{deleted_count}件のログを削除しました")
        return deleted_count
