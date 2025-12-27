import os
from http.server import BaseHTTPRequestHandler, HTTPServer


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        env = os.getenv("ENVIRONMENT", "unknown")
        body = f"Hello from {env}\n".encode("utf-8")

        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    # keep logs quiet
    def log_message(self, fmt, *args):
        return


if __name__ == "__main__":
    host, port = "0.0.0.0", 8080
    print(f"Listening on http://{host}:{port}")
    HTTPServer((host, port), Handler).serve_forever()
