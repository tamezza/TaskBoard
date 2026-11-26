import json
from http.server import BaseHTTPRequestHandler, HTTPServer


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers["Content-Length"])
        message = json.loads(self.rfile.read(length))
        for alert in message["alerts"]:
            print(
                alert["status"].upper(),
                alert["labels"]["alertname"],
                "-",
                alert["annotations"].get("summary", ""),
                flush=True,
            )
        self.send_response(200)
        self.end_headers()

    def log_message(self, *args):
        pass


HTTPServer(("0.0.0.0", 9000), Handler).serve_forever()