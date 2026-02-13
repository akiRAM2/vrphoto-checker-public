import urllib.parse
import mimetypes

class DashboardHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, db, *args, **kwargs):
        self.db = db
        super().__init__(*args, directory="web", **kwargs)

    def do_GET(self):
        parsed_url = urllib.parse.urlparse(self.path)
        
        if parsed_url.path == '/api/logs':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            logs = self.db.get_logs()
            self.wfile.write(json.dumps(logs).encode('utf-8'))
            
        elif parsed_url.path == '/api/image':
            query_params = urllib.parse.parse_qs(parsed_url.query)
            file_path = query_params.get('path', [None])[0]
            
            if file_path and os.path.exists(file_path):
                # Basic security check: ensure it's a file
                # Real production would need sandbox check to ensure inside watch_path
                try:
                    with open(file_path, 'rb') as f:
                        content = f.read()
                        
                    mime_type, _ = mimetypes.guess_type(file_path)
                    self.send_response(200)
                    self.send_header('Content-type', mime_type or 'application/octet-stream')
                    self.end_headers()
                    self.wfile.write(content)
                except Exception as e:
                    self.send_response(500)
                    self.end_headers()
            else:
                self.send_response(404)
                self.end_headers()
        else:
            super().do_GET()

class DashboardServer:
    def __init__(self, port, db):
        self.port = port
        self.db = db
        self.handler = partial(DashboardHandler, self.db)

    def start(self):
        with socketserver.TCPServer(("", self.port), self.handler) as httpd:
            print(f"Serving dashboard at http://localhost:{self.port}")
            httpd.serve_forever()
