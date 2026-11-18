"""Local-only connection to the official launcher diagnostic endpoint."""
import base64
import hashlib
import json
import os
import socket
import struct
from urllib.parse import urlsplit

class LocalWebSocket:
    def __init__(self, url):
        target = urlsplit(url)
        if (target.scheme != 'ws' or target.hostname not in ('127.0.0.1', 'localhost') or
                target.port != 8088 or target.username or target.password or target.query or
                target.fragment or any(ord(c) < 32 for c in target.path)):
            raise ValueError('Only the local launcher diagnostic endpoint is allowed')
        self.socket = socket.create_connection(('127.0.0.1', 8088), timeout=3)
        self.socket.settimeout(3)
        try:
            self.handshake(target)
        except Exception:
            self.socket.close()
            raise

    def handshake(self, target):
        self.buffer = bytearray()
        self.next_id = 0
        key = base64.b64encode(os.urandom(16)).decode()
        request = (f'GET {target.path} HTTP/1.1\r\nHost: 127.0.0.1:8088\r\n'
                   f'Upgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Key: {key}\r\n'
                   'Sec-WebSocket-Version: 13\r\n\r\n')
        self.socket.sendall(request.encode('ascii'))
        while b'\r\n\r\n' not in self.buffer:
            chunk = self.socket.recv(4096)
            if not chunk:
                raise ConnectionError('Diagnostic WebSocket closed during handshake')
            self.buffer.extend(chunk)
            if len(self.buffer) > 32768:
                raise ValueError('Oversized WebSocket handshake')
        headers, pending = self.buffer.split(b'\r\n\r\n', 1)
        self.buffer = bytearray(pending)
        lines = headers.decode('ascii').split('\r\n')
        expected = base64.b64encode(hashlib.sha1((key + '258EAFA5-E914-47DA-95CA-C5AB0DC85B11').encode()).digest()).decode()
        fields = dict(line.split(':', 1) for line in lines[1:] if ':' in line)
        fields = {k.lower(): v.strip() for k, v in fields.items()}
        if ' 101 ' not in lines[0] or fields.get('sec-websocket-accept') != expected:
            raise ConnectionError('Invalid diagnostic WebSocket handshake')

    def read(self, count):
        while len(self.buffer) < count:
            chunk = self.socket.recv(min(65536, count - len(self.buffer)))
            if not chunk:
                raise ConnectionError('Diagnostic WebSocket closed')
            self.buffer.extend(chunk)
        result = bytes(self.buffer[:count])
        del self.buffer[:count]
        return result

    def send(self, data, opcode=1):
        mask = os.urandom(4)
        length = len(data)
        header = bytes([0x80 | opcode])
        if length < 126:
            header += bytes([0x80 | length])
        elif length < 65536:
            header += bytes([0x80 | 126]) + struct.pack('!H', length)
        else:
            header += bytes([0x80 | 127]) + struct.pack('!Q', length)
        self.socket.sendall(header + mask + bytes(value ^ mask[i % 4] for i, value in enumerate(data)))

    def receive(self):
        message = bytearray()
        while True:
            first, second = self.read(2)
            if first & 0x70 or second & 0x80:
                raise ValueError('Unexpected WebSocket extension or server mask')
            length = second & 0x7f
            if length == 126:
                length = struct.unpack('!H', self.read(2))[0]
            elif length == 127:
                length = struct.unpack('!Q', self.read(8))[0]
            if length > 16 * 1024 * 1024 or len(message) + length > 16 * 1024 * 1024:
                raise ValueError('Oversized diagnostic message')
            payload = self.read(length)
            opcode = first & 0x0f
            if opcode == 8:
                raise ConnectionError('Diagnostic WebSocket closed by launcher')
            if opcode == 9:
                self.send(payload, opcode=10)
                continue
            if opcode == 10:
                continue
            if opcode not in (0, 1):
                raise ValueError('Unexpected diagnostic frame type')
            message.extend(payload)
            if first & 0x80:
                return json.loads(message)

    def call(self, method, params=None):
        self.next_id += 1
        ident = self.next_id
        self.send(json.dumps({'id': ident, 'method': method, 'params': params or {}}).encode())
        for _ in range(1000):
            response = self.receive()
            if response.get('id') == ident:
                if 'error' in response:
                    raise RuntimeError('Diagnostic method failed: ' + str(response['error'].get('message', 'unknown error')))
                return response.get('result', {})
        raise RuntimeError('Too many unrelated diagnostic events')

    def close(self):
        self.socket.close()

