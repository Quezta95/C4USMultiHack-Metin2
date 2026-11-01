"""Local web interface for the screenshot analyzer."""
import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

import cv2
import numpy as np

from analyze import analyze

WEB = Path(__file__).resolve().parent / 'web'
MAX_IMAGE_SIZE = 20 * 1024 * 1024


class Handler(BaseHTTPRequestHandler):
    def respond(self, status, body, content_type):
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        files = {'/': ('index.html', 'text/html; charset=utf-8'),
                 '/app.js': ('app.js', 'text/javascript; charset=utf-8'),
                 '/style.css': ('style.css', 'text/css; charset=utf-8')}
        item = files.get(urlsplit(self.path).path)
        if item is None:
            self.respond(404, b'Not found', 'text/plain')
            return
        self.respond(200, (WEB / item[0]).read_bytes(), item[1])

    def do_POST(self):
        if self.path != '/api/analyze':
            self.respond(404, b'Not found', 'text/plain')
            return
        origin = self.headers.get('Origin')
        if origin and origin != f'http://{self.headers.get("Host", "")}':
            self.respond(403, b'Forbidden', 'text/plain')
            return
        try:
            if self.headers.get('Content-Type') != 'application/octet-stream':
                raise ValueError('Nieprawidłowy format żądania.')
            size = int(self.headers.get('Content-Length', '0'))
            if not 0 < size <= MAX_IMAGE_SIZE:
                raise ValueError('Wybierz obraz o rozmiarze do 20 MB.')
            data = self.rfile.read(size)
            if len(data) != size:
                raise ValueError('Nie udało się wczytać całego pliku.')
            image = cv2.imdecode(np.frombuffer(data, dtype=np.uint8), cv2.IMREAD_COLOR)
            if image is None:
                raise ValueError('Nie udało się odczytać obrazu.')
            result = analyze(image)
            self.respond(200, json.dumps(result).encode(), 'application/json')
        except (ValueError, cv2.error) as exc:
            message = str(exc)
            if message.startswith('Expected a full 16:9'):
                message = 'Wybierz pełny zrzut gry 16:9 o szerokości co najmniej 1280 pikseli.'
            self.respond(400, json.dumps({'error': message}).encode(), 'application/json')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=8765)
    args = parser.parse_args()
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f'PoE 2 Vision: http://{args.host}:{server.server_port}', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
