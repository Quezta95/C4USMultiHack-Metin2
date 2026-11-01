import argparse
import io
import http.client
import json
from pathlib import Path
import shutil
import socket
import struct
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest import mock
import zlib

import cv2
import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import analyze
import server


def encoded_image(fmt, size=(1280, 720)):
    output = io.BytesIO()
    Image.new('RGB', size).save(output, format=fmt)
    return output.getvalue()


class ImageTests(unittest.TestCase):
    def test_unicode_paths_for_screenshot_and_templates(self):
        with tempfile.TemporaryDirectory(prefix='Łukasz_') as directory:
            root = Path(directory)
            shutil.copytree(analyze.ROOT / 'templates', root / 'templates')
            path = root / 'zrzut_żółć.png'
            path.write_bytes(encoded_image('PNG'))
            image = analyze.read_image(path, cv2.IMREAD_COLOR)
            self.assertIsNotNone(image)
            with mock.patch.object(analyze, 'ROOT', root):
                self.assertEqual(set(analyze.analyze(image)), {'raven_visible', 'map_completed'})
                template = analyze.read_image(root / 'templates' / 'raven.png', cv2.IMREAD_GRAYSCALE)
                self.assertEqual(len(template.shape), 2)
            result = subprocess.run([sys.executable, str(Path(analyze.__file__)), str(path)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('raven_visible', json.loads(result.stdout))
            self.assertIsNone(analyze.read_image(root / 'missing.png', cv2.IMREAD_COLOR))
            path.write_bytes(b'')
            self.assertIsNone(analyze.read_image(path, cv2.IMREAD_COLOR))

    def test_all_supported_formats(self):
        for fmt in ('PNG', 'JPEG', 'WEBP', 'BMP', 'TIFF'):
            with self.subTest(format=fmt):
                self.assertEqual(server.checked_image(encoded_image(fmt)).shape[:2], (720, 1280))

    def test_oversized_png_rejected_before_decode(self):
        data = bytearray(encoded_image('PNG', (1, 1)))
        struct.pack_into('>II', data, 16, 5000, 5000)
        struct.pack_into('>I', data, 29, zlib.crc32(data[12:29]))
        with mock.patch.object(server.cv2, 'imdecode', side_effect=AssertionError('decoded')):
            with self.assertRaisesRegex(ValueError, 'limit'):
                server.checked_image(bytes(data))

    def test_bad_image_rejected_before_decode(self):
        with mock.patch.object(server.cv2, 'imdecode', side_effect=AssertionError('decoded')):
            with self.assertRaises(ValueError):
                server.checked_image(b'not an image')


class ServerTests(unittest.TestCase):
    def setUp(self):
        self.httpd = server.LocalServer(('127.0.0.1', 0), server.Handler)
        self.httpd.read_timeout = 0.3
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.httpd.shutdown()
        self.thread.join()
        self.httpd.server_close()

    def connect(self):
        return socket.create_connection(self.httpd.server_address, timeout=2)

    def test_incomplete_body_times_out(self):
        with self.connect() as sock:
            sock.sendall(b'POST /api/analyze HTTP/1.1\r\nHost: 127.0.0.1\r\nContent-Type: application/octet-stream\r\nContent-Length: 100\r\n\r\nx')
            self.assertIn(b' 408 ', sock.recv(1024))

    def test_body_deadline_is_not_extended_by_trickling(self):
        with self.connect() as sock:
            sock.sendall(b'POST /api/analyze HTTP/1.1\r\nHost: localhost\r\nContent-Type: application/octet-stream\r\nContent-Length: 100\r\n\r\nx')
            start = time.monotonic()
            for _ in range(5):
                time.sleep(0.08)
                try:
                    sock.sendall(b'x')
                except BrokenPipeError:
                    break
            self.assertIn(b' 408 ', sock.recv(1024))
            self.assertLess(time.monotonic() - start, 1.5)

    def test_api_accepts_screenshot_and_rejects_invalid_image(self):
        conn = http.client.HTTPConnection(*self.httpd.server_address, timeout=3)
        try:
            conn.request('POST', '/api/analyze', encoded_image('PNG'), {'Content-Type': 'application/octet-stream'})
            response = conn.getresponse()
            self.assertEqual(response.status, 200)
            self.assertIn('raven_visible', json.loads(response.read()))
            conn.request('POST', '/api/analyze', b'bad', {'Content-Type': 'application/octet-stream'})
            response = conn.getresponse()
            self.assertEqual(response.status, 400)
            self.assertIn('error', json.loads(response.read()))
        finally:
            conn.close()

    def test_connection_limit(self):
        self.httpd.read_timeout = 2
        clients = []
        try:
            for _ in range(server.MAX_CONNECTIONS):
                sock = self.connect()
                clients.append(sock)
                sock.sendall(b'POST /api/analyze HTTP/1.1\r\nHost: localhost\r\nContent-Type: application/octet-stream\r\nContent-Length: 100\r\n\r\nx')
            deadline = time.monotonic() + 1
            while time.monotonic() < deadline:
                if not self.httpd.slots.acquire(blocking=False):
                    break
                self.httpd.slots.release()
                time.sleep(0.01)
            else:
                self.fail('server did not reach the connection limit')
            with self.connect() as sock:
                sock.sendall(b'GET / HTTP/1.1\r\nHost: localhost\r\n\r\n')
                try:
                    response = sock.recv(1024)
                except ConnectionResetError:
                    response = b''
                self.assertEqual(response, b'')
        finally:
            for sock in clients:
                sock.shutdown(socket.SHUT_WR)
            for sock in clients:
                try:
                    sock.recv(1024)
                finally:
                    sock.close()

    def test_bind_validation(self):
        self.assertEqual(server.loopback_host('127.0.0.1'), '127.0.0.1')
        self.assertEqual(server.loopback_host('localhost'), 'localhost')
        for host in ('0.0.0.0', '192.168.1.2', 'example.com'):
            with self.subTest(host=host), self.assertRaises(argparse.ArgumentTypeError):
                server.loopback_host(host)
        result = subprocess.run([sys.executable, str(Path(server.__file__)), '--host', '0.0.0.0'], capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        process = subprocess.Popen([sys.executable, str(Path(server.__file__)), '--host', 'localhost', '--port', '0'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            self.assertTrue(process.stdout.readline().startswith('PoE 2 Vision: http://localhost:'))
            self.assertIsNone(process.poll())
        finally:
            process.terminate()
            process.communicate(timeout=3)


if __name__ == '__main__':
    unittest.main()
