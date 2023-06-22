import sys

from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import poe
import logging

class RequestHandler(BaseHTTPRequestHandler):
    def _send_response(self, token, message):
        poe.logger.setLevel(logging.INFO)
        client = poe.Client(token)
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.send_header('Access-Control-Allow-Origin', '*')  # 添加这一行
        self.end_headers()
        for chunk in client.send_message("capybara", message, with_chat_break=True):
            self.wfile.write(chunk["text_new"].encode())
        
    def do_GET(self):
        url = urlparse(self.path)
        query_params = parse_qs(url.query)
        if 'token' in query_params and 'message' in query_params:
            token = query_params['token'][0]
            message = query_params['message'][0]
            self._send_response(token, message)
        else:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b'Invalid request')

if __name__ == '__main__':
    from http.server import HTTPServer
    server = HTTPServer(('localhost', 5000), RequestHandler)
    print('Starting server at http://localhost:8000')
    server.serve_forever()
