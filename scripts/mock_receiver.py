#!/usr/bin/env python3
"""Mock webhook receiver that randomly fails — useful for testing retries.

Run:  python scripts/mock_receiver.py
Listens on http://localhost:9999
"""

import random
from http.server import BaseHTTPRequestHandler, HTTPServer

FAIL_RATE = 0.6  # 60 % of requests will fail


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)
        sig = self.headers.get("X-Webhook-Signature", "(none)")

        if random.random() < FAIL_RATE:
            code = random.choice([500, 502, 503, 429])
            print(f"\u274c  Returning {code}  sig={sig[:16]}...")
            self.send_response(code)
        else:
            print(f"\u2705  Returning 200  sig={sig[:16]}...  body={body[:80]}")
            self.send_response(200)

        self.end_headers()


if __name__ == "__main__":
    server = HTTPServer(("0.0.0.0", 9999), Handler)
    print("Mock receiver listening on http://localhost:9999")
    server.serve_forever()
