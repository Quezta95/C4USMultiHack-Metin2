"""Local web interface for the screenshot analyzer."""
import argparse
import json
import io
import ipaddress
import socket
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

import cv2
import numpy as np
from PIL import Image, UnidentifiedImageError

from analyze import analyze

WEB = Path(__file__).resolve().parent / 'web'
MAX_IMAGE_SIZE = 20 * 1024 * 1024
MAX_IMAGE_PIXELS = 20_000_000
MAX_CONNECTIONS = 8
READ_TIMEOUT = 10


class LocalServer(ThreadingHTTPServer):
    """Limit concurrent handlers and time spent waiting for client input."""
    def __init__(self, address, handler):
        super().__init__(address, handler)
        self.slots = threading.BoundedSemaphore(MAX_CONNECTIONS)
        self.read_timeout = READ_TIMEOUT

    def get_request(self):
        connection, address = super().get_request()
        connection.settimeout(self.read_timeout)
        return connection, address

    def process_request(self, request, client_address):
        if not self.slots.acquire(blocking=False):
            self.shutdown_request(request)
            return
        try:
            super().process_request(request, client_address)
        except BaseException:
            self.slots.release()
            raise

    def process_request_thread(self, request, client_address):
        try:
            super().process_request_thread(request, client_address)
        finally:
            self.slots.release()


def checked_image(data):
    """Check supported image dimensions before OpenCV allocates pixels."""
    try:
        with Image.open(io.BytesIO(data)) as header:
            width, height = header.size
            if width <= 0 or height <= 0 or width * height > MAX_IMAGE_PIXELS:
                raise ValueError('Obraz przekracza limit 20 milionów pikseli.')
    except (UnidentifiedImageError, Image.DecompressionBombError, OSError, SyntaxError) as exc:
        raise ValueError('Nie udało się odczytać obrazu lub obraz jest zbyt duży.') from exc
    image = cv2.imdecode(np.frombuffer(data, dtype=np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError('Nie udało się odczytać obrazu.')
    return image


def loopback_host(host):
    if host.lower() == 'localhost':
        return host
    try:
        address = ipaddress.ip_address(host)
        if address.version == 4 and address.is_loopback:
            return host
    except ValueError:
        pass
    raise argparse.ArgumentTypeError('Użyj adresu IPv4 loopback lub localhost.')


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
            deadline = time.monotonic() + self.server.read_timeout
            chunks = []
            remaining = size
            while remaining:
                timeout = deadline - time.monotonic()
                if timeout <= 0:
                    raise socket.timeout()
                self.connection.settimeout(timeout)
                chunk = self.rfile.read1(min(remaining, 65536))
                if not chunk:
                    raise ValueError('Nie udało się wczytać całego pliku.')
                chunks.append(chunk)
                remaining -= len(chunk)
            self.connection.settimeout(self.server.read_timeout)
            image = checked_image(b''.join(chunks))
            result = analyze(image)
            self.respond(200, json.dumps(result).encode(), 'application/json')
        except socket.timeout:
            self.connection.settimeout(self.server.read_timeout)
            self.close_connection = True
            self.respond(408, b'Request timeout', 'text/plain')
        except (ValueError, cv2.error) as exc:
            message = str(exc)
            if message.startswith('Expected a full 16:9'):
                message = 'Wybierz pełny zrzut gry 16:9 o szerokości co najmniej 1280 pikseli.'
            self.respond(400, json.dumps({'error': message}).encode(), 'application/json')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--host', type=loopback_host, default='127.0.0.1')
    parser.add_argument('--port', type=int, default=8765)
    args = parser.parse_args()
    bind_host = '127.0.0.1' if args.host.lower() == 'localhost' else args.host
    server = LocalServer((bind_host, args.port), Handler)
    print(f'PoE 2 Vision: http://{args.host}:{server.server_port}', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
