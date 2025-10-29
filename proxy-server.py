from http.server import BaseHTTPRequestHandler, HTTPServer
import requests
from datetime import datetime

PROXY_PORT = 8888
TARGET_SERVER = "http://localhost:8012"
LOG_FILE = "proxy.log"
import json



def make_proxy_handler(log_file_path):
    class SimpleProxy(BaseHTTPRequestHandler):
        def do_GET(self):
            target_url = f"{TARGET_SERVER}{self.path}"
            self.log(f"\n➡️  Forwarding GET to: {target_url}")

            try:
                resp = requests.get(target_url, headers=self.headers, stream=True)

                self.log(f"⬅️  Response Status: {resp.status_code}")
                self.log(f"⬅️  Response Headers: {resp.headers}\n")

                self.send_response(resp.status_code)
                for k, v in resp.headers.items():
                    self.send_header(k, v)
                self.end_headers()
                self.wfile.write(resp.content)

            except Exception as e:
                self.send_error(502, f"Error forwarding request: {e}")

        def do_POST(self):
            content_len = int(self.headers.get('Content-Length', 0))
            post_body = self.rfile.read(content_len)
            target_url = f"{TARGET_SERVER}{self.path}"

            self.log(f"\n➡️  Forwarding POST to: {target_url}")
            self.log_json("➡️  Request Body:", post_body.decode(errors='ignore'))

            try:
                resp = requests.post(target_url, headers=self.headers, data=post_body, stream=True)

                self.log(f"⬅️  Response Status: {resp.status_code}")
                self.log_json("⬅️  Response Body", resp.text)

                self.send_response(resp.status_code)
                for k, v in resp.headers.items():
                    self.send_header(k, v)
                self.end_headers()
                self.wfile.write(resp.content)

            except Exception as e:
                self.send_error(502, f"Error forwarding request: {e}")

        def log(self, message):
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            log_entry = f"[{timestamp}] {message}\n"
            print(log_entry.strip())
            with open(log_file_path, 'a') as f:
                f.write(log_entry)

        def log_message(self, format, *args):
            return  # Silence default server logs
        
        def log(self, message):
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            log_entry = f"[{timestamp}] {message}\n"
            print(log_entry.strip())
            with open(self.server.log_file, 'a') as f:
                f.write(log_entry)

        def log_json(self, label, raw_data):
            try:
                parsed = json.loads(raw_data)
                pretty = json.dumps(parsed, indent=2)
                self.log(f"{label} (JSON):\n{pretty}")
            except Exception:
                self.log(f"{label} (Raw):\n{raw_data}")
    # Initialize log file once
    with open(log_file_path, 'w') as f:
        f.write(f"Proxy Server Log - Started at {datetime.now()}\n\n")

    return SimpleProxy

if __name__ == "__main__":
    print(f"🔁 Starting proxy on port {PROXY_PORT}, forwarding to {TARGET_SERVER}")
    handler_class = make_proxy_handler(LOG_FILE)
    server = HTTPServer(("localhost", PROXY_PORT), handler_class)
    server.log_file = LOG_FILE
    server.serve_forever()
