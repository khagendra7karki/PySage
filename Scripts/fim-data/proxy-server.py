from http.server import BaseHTTPRequestHandler, HTTPServer
import requests
from datetime import datetime

PROXY_PORT = 8888
TARGET_SERVER = "http://localhost:8012"
LOG_FILE = "proxy.log"
import json




import jedi
from pathlib import Path

def extract_context(code, project_path, file_path, line, column):
    """
    Extract relevant definitions and context from a Python project.
    
    Args:
        project_path: Root path of the Python project
        file_path: Path to the file where you want context
        line: Line number in the file
        column: Column number in the file
    """
    # Create a Script object for the file
    script = jedi.Script(
        code,
        path=file_path,
        project=jedi.Project(project_path)
    )
    
    # Get completions at the given position
    completions = script.complete(line, column)
    print(f"\nCompletions at {file_path}:{line}:{column}:")
    for c in completions:
        print(f"- {c.name} (type: {c.type})")
    
    # Get all definitions in the file
    definitions = script.get_names()
    print("\nAll definitions in this file:")
    for d in definitions:
        if d.type in ('function', 'class'):
            print(f"- {d.name} (type: {d.type}, line: {d.line})")
    
    # Get goto definitions (what's defined at this position)
    definitions = script.goto(line, column)
    print("\nDefinitions at cursor position:")
    for d in definitions:
        print(f"- {d.name} (type: {d.type}, module: {d.module_name}, path: {d.module_path}, line: {d.line})")
    
    # Get references/usages
    usages = script.get_references(line, column)
    print("\nReferences/usages:")
    for u in usages:
        print(f"- {u.name} in {u.module_path} at line {u.line}")



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
            str_body = post_body.decode(errors="ignore")

            self.log_json("➡️  Request Body:", str_body)

            # for extracting context
            json_body = json.loads(str_body)

            if json_body.get("fileContent", None):

                file_content = json_body['fileContent']
                line = json_body['line']
                column = json_body["column"]

                project_root = Path("../../../BoxWar")
                target_file = project_root / "main.py"
                extract_context(file_content, project_root, target_file, line, column)


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
            # print(log_entry.strip())
            with open(log_file_path, 'a') as f:
                f.write(log_entry)

        def log_message(self, format, *args):
            return  # Silence default server logs
        

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
