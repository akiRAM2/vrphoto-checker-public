import http.server
import socketserver
import json
import os
from functools import partial

class DashboardHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, db, *args, **kwargs):
        self.db = db
        # Set directory to 'web' to serve static files from there
        super().__init__(*args, directory="web", **kwargs)

    def do_GET(self):
        if self.path == '/api/logs':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            logs = self.db.get_logs()
            self.wfile.write(json.dumps(logs).encode('utf-8'))
        else:
            super().do_GET()

class DashboardServer:
    def __init__(self, port, db):
        self.port = port
        self.db = db
        self.handler = partial(DashboardHandler, self.db)

    def start(self):
        with socketserver.TCPServer(("", self.port), self.handler) as httpd:
            print(f"Serving dashboard at port {self.port}")
            httpd.serve_forever()
